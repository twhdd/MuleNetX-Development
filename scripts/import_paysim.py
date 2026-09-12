import os
import pandas as pd
from backend.neo4j_client import neo4j_client
from graph_engine.create_schema import create_schema

BATCH_SIZE = 5000


def run_import(csv_path=None, limit=10000):
    create_schema()

    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "datasets",
            "processed_paysim.csv"
        )
        if not os.path.exists(csv_path):
            csv_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "datasets",
                "raw",
                "paysim.csv"
            )

    df = pd.read_csv(csv_path)
    if limit is not None and limit > 0:
        df = df.head(limit)

    query = """
    UNWIND $rows AS row
    MERGE (s:Account {account_id: row.nameOrig})
    MERGE (r:Account {account_id: row.nameDest})
    CREATE (s)-[t:TRANSFER {
        transaction_id: coalesce(row.transaction_id, 'TX_' + toString(row.step)),
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
    }]->(r)
    """

    records = df.to_dict("records")
    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]
        neo4j_client.execute(query, {"rows": batch})

    print(f"Import Complete: {len(df)} transactions loaded via canonical :TRANSFER relationship")


if __name__ == "__main__":
    run_import()
