import json
from datetime import datetime

from backend.neo4j_client import (
    neo4j_client
)


def create_snapshot():

    query = """
    MATCH (a)-[t:TRANSFER]->(b)

    RETURN
        a.account_id AS source,
        b.account_id AS target,
        t.amount AS amount
    """

    result = neo4j_client.execute(
        query
    )

    rows = [
        dict(r)
        for r in result
    ]

    filename = (
        f"snapshots/"
        f"{datetime.utcnow().timestamp()}.json"
    )

    with open(
        filename,
        "w"
    ) as f:

        json.dump(
            rows,
            f
        )

    return filename
