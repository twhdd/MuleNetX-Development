import os
import sys
import pandas as pd
from sqlalchemy import text

# Ensure project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datasets.preprocess import preprocess_paysim, validate_raw_dataset, DEFAULT_RAW_PATH
from backend.database.session import engine
from backend.database.init_db import init_db
from backend.database.load_transactions import load_transactions_to_postgres
from graph_engine.create_schema import create_schema
from graph_engine.ingest_paysim import ingest_from_postgres
from graph_engine.run_analytics import run as run_graph_analytics
from ml_engine.feature_builder import build_feature_dataset
from backend.neo4j_client import neo4j_client


def run_pipeline(limit=10000):
    print("=" * 60)
    print("PHASE 2: DATA PIPELINE + GRAPH CONSTRUCTION")
    print("=" * 60)

    # 1. Inspect Raw Dataset
    print("\n--- 1. Raw PaySim Dataset Inspection ---")
    raw_csv = DEFAULT_RAW_PATH
    if not os.path.exists(raw_csv):
        raw_csv = os.path.join(PROJECT_ROOT, "datasets", "PS_20174392719_1491204439457_log.csv")

    raw_stats = validate_raw_dataset(pd.read_csv(raw_csv, nrows=100))
    # Count full raw rows
    raw_df_full = pd.read_csv(raw_csv, usecols=["isFraud"])
    raw_total_rows = len(raw_df_full)
    raw_total_fraud = int(raw_df_full["isFraud"].sum())
    print(f"Raw PaySim Dataset Path: {raw_csv}")
    print(f"Total Raw Rows: {raw_total_rows}")
    print(f"Total Raw Fraud Transactions: {raw_total_fraud}")
    print(f"Columns: {raw_stats['columns']}")

    # 2. Preprocessing
    print(f"\n--- 2. Preprocessing (Pipeline subset: {limit} rows) ---")
    processed_df = preprocess_paysim(
        raw_path=raw_csv,
        limit=limit,
        output_path=os.path.join(PROJECT_ROOT, "datasets", "processed_paysim.csv")
    )
    processed_count = len(processed_df)
    processed_fraud = int(processed_df["isFraud"].sum())
    print(f"Processed Transactions: {processed_count}")
    print(f"Processed Fraud Transactions: {processed_fraud}")

    # 3. PostgreSQL Ingestion
    print("\n--- 3. PostgreSQL Ingestion ---")
    init_db()
    pg_stats = load_transactions_to_postgres(df=processed_df, truncate=True)
    pg_total = pg_stats["postgres_total_transactions"]
    pg_fraud = pg_stats["postgres_fraud_transactions"]

    # 4. Neo4j Graph Construction
    print("\n--- 4. Neo4j Graph Construction ---")
    neo4j_stats = ingest_from_postgres(limit=limit, clear_existing=True)
    neo4j_accounts = neo4j_stats["neo4j_accounts"]
    neo4j_txs = neo4j_stats["neo4j_transactions"]
    neo4j_fraud = neo4j_stats["neo4j_fraud_transactions"]

    # 5. Graph Analytics
    print("\n--- 5. Graph Analytics (GDS & Topological Features) ---")
    run_graph_analytics()

    # 6. ML-Ready Feature Dataset
    print("\n--- 6. ML-Ready Feature Dataset ---")
    feature_df = build_feature_dataset()
    feature_rows = len(feature_df)
    feature_cols = len(feature_df.columns)

    # 7. Verification of Final Dataset
    feature_csv_path = os.path.join(PROJECT_ROOT, "datasets", "account_features.csv")
    read_check = pd.read_csv(feature_csv_path)
    assert len(read_check) == feature_rows, "Row count mismatch in saved feature dataset"
    assert len(read_check.columns) == feature_cols, "Column count mismatch in saved feature dataset"
    print(f"Successfully verified readable feature dataset at {feature_csv_path}")

    print("\n" + "=" * 60)
    print("PIPELINE VERIFICATION NUMBERS:")
    print("=" * 60)
    print(f"raw transactions:        {raw_total_rows}")
    print(f"processed transactions:  {processed_count}")
    print(f"PostgreSQL transactions: {pg_total}")
    print(f"Neo4j accounts:          {neo4j_accounts}")
    print(f"Neo4j transactions:      {neo4j_txs}")
    print(f"fraud transactions:      {neo4j_fraud}")
    print(f"feature rows:            {feature_rows}")
    print(f"feature columns:         {feature_cols}")
    print("=" * 60)

    return {
        "raw_transactions": raw_total_rows,
        "processed_transactions": processed_count,
        "postgresql_transactions": pg_total,
        "neo4j_accounts": neo4j_accounts,
        "neo4j_transactions": neo4j_txs,
        "fraud_transactions": neo4j_fraud,
        "feature_rows": feature_rows,
        "feature_columns": feature_cols
    }


if __name__ == "__main__":
    run_pipeline()
