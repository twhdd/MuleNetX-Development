from backend.neo4j_client import neo4j_client


def get_account_context(account_id: str):

    query = """
    MATCH (a:Account {account_id:$account_id})

    OPTIONAL MATCH (a)-[t:TRANSFER]->(b)

    WITH
        a,
        count(t) AS transaction_count,
        sum(t.amount) AS total_sent,
        collect(DISTINCT b.account_id)[0..20] AS connected_accounts

    RETURN
        a.account_id AS account_id,
        coalesce(a.risk_score,0) AS risk_score,
        coalesce(a.pagerank,0) AS pagerank,
        coalesce(a.degree,0) AS degree,
        coalesce(a.betweenness,0) AS betweenness,
        coalesce(a.community,-1) AS community,
        transaction_count,
        coalesce(total_sent,0) AS total_sent,
        connected_accounts
    """

    result = neo4j_client.execute(
        query,
        {"account_id": account_id}
    )

    record = result.single()

    if not record:
        return None

    return dict(record)
