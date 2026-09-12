from backend.neo4j_client import (
    neo4j_client
)


def detect_fanout():

    query = """
    MATCH (a)-[t:TRANSFER]->(b)

    WITH
        a,
        count(b) AS receivers,
        sum(t.amount) AS total

    WHERE
        receivers > 25

    RETURN
        a.account_id AS account,
        receivers,
        total

    ORDER BY receivers DESC
    """

    result = neo4j_client.execute(
        query
    )

    return [
        dict(x)
        for x in result
    ]
