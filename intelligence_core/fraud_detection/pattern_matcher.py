from backend.neo4j_client import (
    neo4j_client
)


def find_smurfing():

    query = """
    MATCH (a)-[t:TRANSFER]->(b)

    WITH
        b,
        count(*) AS tx_count,
        sum(t.amount) AS total

    WHERE
        tx_count > 20
        AND total > 10000

    RETURN
        b.account_id AS account,
        tx_count,
        total

    ORDER BY total DESC
    """

    result = neo4j_client.execute(
        query
    )

    return [
        dict(x)
        for x in result
    ]
