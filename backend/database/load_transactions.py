import os
import pandas as pd
from typing import Optional, Dict, Any
from sqlalchemy import text

from backend.database.session import engine, SessionLocal
from backend.database.init_db import init_db
from backend.models.transaction import Transaction


def load_transactions_to_postgres(
    df: Optional[pd.DataFrame] = None,
    csv_path: Optional[str] = None,
    truncate: bool = True
) -> Dict[str, Any]:
    """
    Loads preprocessed transactions into PostgreSQL table 'transactions'.
    Verifies inserted row count and fraud/non-fraud counts.
    """
    # Ensure tables exist
    init_db()

    if df is None:
        if csv_path is None:
            csv_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "datasets",
                "processed_paysim.csv"
            )
        df = pd.read_csv(csv_path)

    # Rename columns to match database schema
    column_mapping = {
        "transaction_id": "transaction_id",
        "step": "step",
        "type": "type",
        "amount": "amount",
        "nameOrig": "name_orig",
        "oldbalanceOrg": "old_balance_org",
        "newbalanceOrig": "new_balance_orig",
        "nameDest": "name_dest",
        "oldbalanceDest": "old_balance_dest",
        "newbalanceDest": "new_balance_dest",
        "isFraud": "is_fraud",
        "isFlaggedFraud": "is_flagged_fraud"
    }

    db_df = df.rename(columns=column_mapping)
    # Select only columns present in the model
    db_cols = list(column_mapping.values())
    db_df = db_df[[c for c in db_cols if c in db_df.columns]]

    with engine.begin() as conn:
        if truncate:
            conn.execute(text("TRUNCATE TABLE transactions RESTART IDENTITY;"))

    # Bulk insert
    db_df.to_sql(
        "transactions",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi"
    )

    # Query verification stats directly from PostgreSQL
    with engine.connect() as conn:
        total_count = conn.execute(text("SELECT count(*) FROM transactions;")).scalar()
        fraud_count = conn.execute(text("SELECT count(*) FROM transactions WHERE is_fraud = 1;")).scalar()
        non_fraud_count = conn.execute(text("SELECT count(*) FROM transactions WHERE is_fraud = 0;")).scalar()

    stats = {
        "postgres_total_transactions": total_count,
        "postgres_fraud_transactions": fraud_count,
        "postgres_non_fraud_transactions": non_fraud_count
    }

    print("PostgreSQL Transaction Ingestion Verified:")
    print(f"  Total Inserted: {total_count}")
    print(f"  Fraud:          {fraud_count}")
    print(f"  Non-Fraud:      {non_fraud_count}")

    return stats


if __name__ == "__main__":
    load_transactions_to_postgres()
