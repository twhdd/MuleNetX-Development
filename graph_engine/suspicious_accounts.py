from backend.neo4j_client import neo4j_client


def suspicious_accounts(limit=100):

    query = """
    MATCH (a:Account)

    RETURN
        a.account_id AS account,
        a.pagerank AS pagerank,
        a.degree AS degree,
        a.betweenness AS betweenness,
        a.community AS community,
        a.total_sent AS total_sent

    ORDER BY
        a.pagerank DESC,
        a.betweenness DESC

    LIMIT $limit
    """

    result = neo4j_client.execute(
        query,
        {"limit": limit}
    )

    rows = []

    for r in result:
        rows.append(dict(r))

    return rows


if __name__ == "__main__":

    suspects = suspicious_accounts()

    for row in suspects[:20]:
        print(row)
