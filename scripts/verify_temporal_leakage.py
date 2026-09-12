import os
import sys
import pandas as pd
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.session import engine

df_feat = pd.read_csv("datasets/account_features.csv")

# Query actual count of transactions for each account per cutoff from PostgreSQL
q = """
WITH acct_txs AS (
    SELECT name_orig AS acct, step, amount FROM transactions
    UNION ALL
    SELECT name_dest AS acct, step, amount FROM transactions
)
SELECT 
    acct AS account_id,
    count(case when step <= 4 then 1 end) AS count_step4,
    count(case when step <= 5 then 1 end) AS count_step5,
    count(case when step <= 7 then 1 end) AS count_step7,
    coalesce(sum(case when step <= 4 then amount else 0 end), 0) AS total_amt_step4,
    count(*) AS total_count_all_steps
FROM acct_txs
GROUP BY acct;
"""
tx_counts = pd.read_sql(q, con=engine)
check_df = pd.merge(df_feat, tx_counts, on="account_id")

# Train check: cutoff 4
train_check = check_df[check_df["split"] == "train"]
train_diff = int((train_check["transaction_count"] != train_check["count_step4"]).sum())
train_leak = int((train_check["transaction_count"] > train_check["count_step4"]).sum())

# Val check: cutoff 5
val_check = check_df[check_df["split"] == "val"]
val_diff = int((val_check["transaction_count"] != val_check["count_step5"]).sum())
val_leak = int((val_check["transaction_count"] > val_check["count_step5"]).sum())

# Test check: cutoff 7
test_check = check_df[check_df["split"] == "test"]
test_diff = int((test_check["transaction_count"] != test_check["count_step7"]).sum())
test_leak = int((test_check["transaction_count"] > test_check["count_step7"]).sum())

print("=== POINT-IN-TIME VERIFICATION RESULTS ===")
print(f"Train accounts ({len(train_check)}): differences from step<=4: {train_diff}, leaks: {train_leak}")
print(f"Val accounts   ({len(val_check)}): differences from step<=5: {val_diff}, leaks: {val_leak}")
print(f"Test accounts  ({len(test_check)}): differences from step<=7: {test_diff}, leaks: {test_leak}")

# Check accounts with later transactions
later_txs = train_check[train_check["total_count_all_steps"] > train_check["count_step4"]]
print(f"Train accounts having subsequent transactions in steps 5-7: {len(later_txs)}")
if len(later_txs) > 0:
    s = later_txs.iloc[0]
    print(f"Sample account {s['account_id']}: step<=4 count = {s['count_step4']}, feature count = {s['transaction_count']}, all-steps count = {s['total_count_all_steps']}")

assert train_leak == 0, "Temporal leakage detected in train set!"
assert val_leak == 0, "Temporal leakage detected in val set!"
assert test_leak == 0, "Temporal leakage detected in test set!"
print("\nTEMPORAL LEAKAGE AUDIT: ALL CHECKS PASSED (ZERO LEAKAGE).")
