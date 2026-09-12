import os
import pandas as pd
from typing import Optional, Dict, Any
from tqdm import tqdm

from backend.neo4j_client import neo4j_client
from backend.database.session import engine
from graph_engine.create_schema import create_schema

BATCH_SIZE = 5000


def create_batch(records):
    query = """
    UNWIND $rows AS row

    MERGE (sender:Account {
        account_id: row.nameOrig
    })

    MERGE (receiver:Account {
        account_id: row.nameDest
    })

    CREATE (sender)-[:TRANSFER {
        transaction_id: row.transaction_id,
        amount: toFloat(row.amount),
        type: row.type,
        transaction_type: row.type,
        step: toInteger(row.step),
        oldbalanceOrg: toFloat(coalesce(row.oldbalanceOrg, 0.0)),
        newbalanceOrig: toFloat(coalesce(row.newbalanceOrig, 0.0)),
        oldbalanceDest: toFloat(coalesce(row.oldbalanceDest, 0.0)),
        newbalanceDest: toFloat(coalesce(row.newbalanceDest, 0.0)),
        isFraud: toInteger(row.isFraud),
        isFlaggedFraud: toInteger(coalesce(row.isFlaggedFraud, 0))
    }]->(receiver)
    """
    neo4j_client.execute(query, {"rows": records})


def ingest_from_postgres(
    limit: Optional[int] = None,
    clear_existing: bool = True
) -> Dict[str, Any]:
    """Ingests transactions from PostgreSQL table into Neo4j graph."""
    create_schema()

    if clear_existing:
        print("Clearing existing Neo4j graph data...")
        neo4j_client.execute_admin("MATCH (n:Account) DETACH DELETE n")

    query = "SELECT * FROM transactions ORDER BY id"
    if limit is not None and limit > 0:
        query += f" LIMIT {limit}"

    print("Loading transactions from PostgreSQL...")
    df = pd.read_sql(query, con=engine)
    print(f"Loaded {len(df)} transactions from PostgreSQL.")

    # Normalize column names to camelCase for Cypher template compatibility
    records = []
    for row in df.to_dict("records"):
        records.append({
            "transaction_id": row.get("transaction_id") or f"TX_{row.get('id', 0):08d}",
            "nameOrig": row.get("name_orig") or row.get("nameOrig"),
            "nameDest": row.get("name_dest") or row.get("nameDest"),
            "amount": float(row.get("amount", 0.0)),
            "type": str(row.get("type", "")),
            "step": int(row.get("step", 0)),
            "oldbalanceOrg": float(row.get("old_balance_org") or 0.0),
            "newbalanceOrig": float(row.get("new_balance_orig") or 0.0),
            "oldbalanceDest": float(row.get("old_balance_dest") or 0.0),
            "newbalanceDest": float(row.get("new_balance_dest") or 0.0),
            "isFraud": int(row.get("is_fraud") or 0),
            "isFlaggedFraud": int(row.get("is_flagged_fraud") or 0),
        })

    total_rows = len(records)
    print(f"Ingesting {total_rows} transactions into Neo4j...")
    for start in tqdm(range(0, total_rows, BATCH_SIZE)):
        end = start + BATCH_SIZE
        batch = records[start:end]
        create_batch(batch)

    # Verification counts
    acct_res = neo4j_client.execute("MATCH (a:Account) RETURN count(a) AS cnt").single()
    accounts_count = acct_res["cnt"] if acct_res else 0

    tx_res = neo4j_client.execute("MATCH ()-[t:TRANSFER]->() RETURN count(t) AS cnt").single()
    transactions_count = tx_res["cnt"] if tx_res else 0

    fraud_res = neo4j_client.execute("MATCH ()-[t:TRANSFER {isFraud: 1}]->() RETURN count(t) AS cnt").single()
    fraud_transactions_count = fraud_res["cnt"] if fraud_res else 0

    stats = {
        "neo4j_accounts": accounts_count,
        "neo4j_transactions": transactions_count,
        "neo4j_fraud_transactions": fraud_transactions_count
    }

    print("Neo4j Graph Construction Verified:")
    print(f"  Accounts:           {accounts_count}")
    print(f"  Transactions:       {transactions_count}")
    print(f"  Fraud Transactions: {fraud_transactions_count}")

    return stats


def ingest(df, clear_existing: bool = False):
    create_schema()
    if clear_existing:
        neo4j_client.execute_admin("MATCH (n:Account) DETACH DELETE n")

    records = df.to_dict("records")
    total_rows = len(records)
    for start in tqdm(range(0, total_rows, BATCH_SIZE)):
        end = start + BATCH_SIZE
        batch = records[start:end]
        create_batch(batch)


if __name__ == "__main__":
    ingest_from_postgres()
    print("Ingestion Complete")
