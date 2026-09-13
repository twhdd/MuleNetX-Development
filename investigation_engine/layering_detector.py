from backend.neo4j_client import neo4j_client


def detect_layering():

    query = """
    MATCH p=
    (a:Account)-[:TRANSFER*4..8]->(b)

    WHERE
    a <> b

    RETURN
    a.account_id AS source,
    b.account_id AS destination,
    length(p) AS hops

    LIMIT 1000
    """

    result = neo4j_client.execute(query)

    return [dict(x) for x in result]
