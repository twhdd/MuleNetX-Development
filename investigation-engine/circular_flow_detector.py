from backend.neo4j_client import neo4j_client


def detect_cycles():

    query = """
    MATCH p =
    (a:Account)-[:TRANSFER*3..8]->(a)

    RETURN
    a.account_id AS account,
    length(p) AS cycle_length

    LIMIT 500
    """

    result = neo4j_client.execute(query)

    return [dict(x) for x in result]
