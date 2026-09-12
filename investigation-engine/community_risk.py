from backend.neo4j_client import neo4j_client


def score_communities():

    query = """
    MATCH (a:Account)

    WITH
        a.community AS community,
        avg(a.pagerank) AS avg_rank,
        avg(a.betweenness) AS avg_between,
        count(*) AS members

    RETURN
        community,
        avg_rank,
        avg_between,
        members

    ORDER BY avg_rank DESC
    """

    result = neo4j_client.execute(query)

    return [dict(x) for x in result]
