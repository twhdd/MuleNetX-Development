import os
from typing import Any, Dict, Optional

import pandas as pd


DEFAULT_RAW_PATH = os.path.join(
    os.path.dirname(__file__),
    "raw",
    "paysim.csv",
)

PROCESSED_PATH = os.path.join(
    os.path.dirname(__file__),
    "processed_paysim.csv",
)

REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]


def validate_raw_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate the PaySim schema and return basic dataset statistics."""
    missing_cols = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in dataset: {missing_cols}")

    return {
        "total_rows": len(df),
        "columns": list(df.columns),
        "column_types": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "fraud_count": int(df["isFraud"].sum()),
        "non_fraud_count": int((df["isFraud"] == 0).sum()),
        "flagged_fraud_count": int(df["isFlaggedFraud"].sum()),
        "unique_senders": int(df["nameOrig"].nunique()),
        "unique_receivers": int(df["nameDest"].nunique()),
    }


def preprocess_paysim(
    raw_path: Optional[str] = None,
    output_path: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Validate, normalize, and persist a deterministic PaySim transaction subset."""
    raw_path = raw_path or DEFAULT_RAW_PATH
    if not os.path.exists(raw_path):
        alternate_path = os.path.join(
            os.path.dirname(__file__),
            "PS_20174392719_1491204439457_log.csv",
        )
        if os.path.exists(alternate_path):
            raw_path = alternate_path
        else:
            raise FileNotFoundError(f"PaySim raw dataset not found at {raw_path}")

    if limit is not None and limit > 0:
        df = pd.read_csv(raw_path, nrows=limit)
    else:
        df = pd.read_csv(raw_path)

    validate_raw_dataset(df)
    df = df.dropna(
        subset=["step", "type", "amount", "nameOrig", "nameDest", "isFraud"]
    ).copy()

    df["step"] = df["step"].astype(int)
    df["type"] = df["type"].astype(str).str.strip().str.upper()
    df["amount"] = df["amount"].astype(float)
    df["nameOrig"] = df["nameOrig"].astype(str).str.strip()
    df["oldbalanceOrg"] = df["oldbalanceOrg"].fillna(0.0).astype(float)
    df["newbalanceOrig"] = df["newbalanceOrig"].fillna(0.0).astype(float)
    df["nameDest"] = df["nameDest"].astype(str).str.strip()
    df["oldbalanceDest"] = df["oldbalanceDest"].fillna(0.0).astype(float)
    df["newbalanceDest"] = df["newbalanceDest"].fillna(0.0).astype(float)
    df["isFraud"] = df["isFraud"].astype(int)
    df["isFlaggedFraud"] = df["isFlaggedFraud"].fillna(0).astype(int)
    df = df[(df["amount"] >= 0) & (df["step"] >= 0)].copy()

    if "transaction_id" not in df.columns:
        df.insert(0, "transaction_id", [f"TX_{index + 1:08d}" for index in range(len(df))])

    standard_columns = [
        "transaction_id",
        "step",
        "type",
        "amount",
        "nameOrig",
        "oldbalanceOrg",
        "newbalanceOrig",
        "nameDest",
        "oldbalanceDest",
        "newbalanceDest",
        "isFraud",
        "isFlaggedFraud",
    ]
    df = df[standard_columns]

    if output_path is not None:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Preprocessed dataset written to {output_path} ({len(df)} rows)")

    return df
