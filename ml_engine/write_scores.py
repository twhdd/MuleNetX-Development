from backend.neo4j_client import neo4j_client

from ml_engine.feature_builder import build_feature_dataset
from ml_engine.predict_risk import predict


def write_scores():

    df = build_feature_dataset()

    scored = predict(df)

    rows = scored[
        ["account_id", "risk_score"]
    ].to_dict("records")

    query = """
    UNWIND $rows AS row

    MATCH (a:Account {
        account_id: row.account_id
    })

    SET a.risk_score = row.risk_score
    """

    neo4j_client.execute(
        query,
        {"rows": rows}
    )

    print("Scores Written")


if __name__ == "__main__":
    write_scores()
