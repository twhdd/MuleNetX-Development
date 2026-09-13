from backend.neo4j_client import neo4j_client


def trace_transactions(
    account_id,
    hops=5,
    limit=500
):

    query = """
    MATCH p =
    (start:Account {account_id:$account_id})
    -[:TRANSFER*1..5]->
    (target)

    RETURN p
    LIMIT $limit
    """

    return neo4j_client.execute(
        query,
        {
            "account_id": account_id,
            "limit": limit
        }
    )
