from backend.neo4j_client import neo4j_client


def detect_fraud_rings():

    query = """
    MATCH (a:Account)

    WITH
    a,
    (
        coalesce(a.pagerank,0) * 0.40 +
        coalesce(a.betweenness,0) * 0.30 +
        coalesce(a.degree,0) * 0.30
    ) AS risk_score

    WHERE risk_score > 1

    RETURN
        a.account_id AS account,
        risk_score,
        a.community AS community

    ORDER BY risk_score DESC
    LIMIT 500
    """

    result = neo4j_client.execute(query)

    return [dict(x) for x in result]
