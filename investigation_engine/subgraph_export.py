from backend.neo4j_client import neo4j_client


def export_community(community):

    query = """
    MATCH (a:Account)
    WHERE a.community = $community

    OPTIONAL MATCH
    (a)-[t:TRANSFER]->(b)

    RETURN
    a.account_id,
    b.account_id,
    t.amount
    """

    result = neo4j_client.execute(
        query,
        {"community": community}
    )

    return [dict(x) for x in result]
