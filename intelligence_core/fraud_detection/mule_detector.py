from backend.neo4j_client import (
    neo4j_client
)


def detect_mules():

    query = """
    MATCH (a:Account)

    OPTIONAL MATCH
    ()-[i:TRANSFER]->(a)

    OPTIONAL MATCH
    (a)-[o:TRANSFER]->()

    WITH
        a,
        count(i) AS incoming,
        count(o) AS outgoing

    WHERE
        incoming > 20
        AND outgoing < 3

    RETURN
        a.account_id AS account,
        incoming,
        outgoing
    """

    result = neo4j_client.execute(
        query
    )

    return [
        dict(x)
        for x in result
    ]
