import os
import sys

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.session import engine


SPLIT_CUTOFFS = {"train": 4, "val": 5, "test": 7}


def expected_account_counts(cutoff: int) -> pd.DataFrame:
    query = text(
        """
        WITH acct_steps AS (
            SELECT name_orig AS account_id, step, is_fraud FROM transactions
            UNION ALL
            SELECT name_dest AS account_id, step, is_fraud FROM transactions
        )
        SELECT
            account_id,
            COUNT(CASE WHEN step <= :cutoff THEN 1 END) AS feature_count,
            MAX(CASE WHEN step > :cutoff AND is_fraud = 1 THEN 1 ELSE 0 END)
                AS expected_target
        FROM acct_steps
        GROUP BY account_id
        """
    )
    return pd.read_sql(query, con=engine, params={"cutoff": cutoff})


def main() -> None:
    feature_path = os.path.join(PROJECT_ROOT, "datasets", "account_features.csv")
    feature_df = pd.read_csv(feature_path)
    required = {
        "account_id",
        "first_step",
        "cutoff_step",
        "split",
        "transaction_count",
        "target",
        "max_observed_step",
        "target_eligible",
        "target_censored",
    }
    missing = required.difference(feature_df.columns)
    if missing:
        raise AssertionError(f"Missing target validation columns: {sorted(missing)}")

    failures = []
    for split, cutoff in SPLIT_CUTOFFS.items():
        rows = feature_df[feature_df["split"] == split].copy()
        if not (rows["cutoff_step"] == cutoff).all():
            failures.append(f"{split}: incorrect cutoff metadata")
        if split == "test" and not ((rows["first_step"] >= 6) & (rows["first_step"] <= 7)).all():
            failures.append("test: account outside first_step 6..7")
        censored = rows[~rows["target_eligible"]]
        evaluated = rows[rows["target_eligible"]].copy()
        if not (rows["target_censored"] == ~rows["target_eligible"]).all():
            failures.append(f"{split}: inconsistent censoring metadata")
        if not (evaluated["max_observed_step"] > evaluated["cutoff_step"]).all():
            failures.append(f"{split}: improperly censored evaluated row")

        expected = expected_account_counts(cutoff).set_index("account_id")
        checked = rows.set_index("account_id").join(expected, how="left")
        if checked["expected_target"].isna().any():
            failures.append(f"{split}: account missing from transaction metadata")
            continue
        if (checked["target"] != checked["expected_target"]).any():
            failures.append(f"{split}: target differs from cutoff-relative future fraud")
        if ((checked["target"] == 1) & (checked["expected_target"] != 1)).any():
            failures.append(f"{split}: target=1 without qualifying future fraud")
        if ((checked["target"] == 0) & (checked["expected_target"] == 1)).any():
            failures.append(f"{split}: target=0 despite qualifying future fraud")
        if (checked["transaction_count"] != checked["feature_count"]).any():
            failures.append(f"{split}: feature transaction count exceeds cutoff")

        positives = int(evaluated["target"].sum())
        negatives = int(len(evaluated) - positives)
        print(
            f"{split}: evaluated={len(evaluated)}, positive={positives}, "
            f"negative={negatives}, censored={len(censored)}"
        )

    if failures:
        raise AssertionError("; ".join(failures))

    print("TARGET VALIDATION: PASS")
    print("FEATURE LEAKAGE VALIDATION: PASS")


if __name__ == "__main__":
    main()
