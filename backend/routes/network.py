from fastapi import APIRouter

from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get(
    "/graph/network/{account_id}"
)
def account_network(
    account_id: str
):

    query = """
    MATCH p=
    (a:Account {account_id:$account_id})
    -[r:TRANSFER*1..2]->
    (b)

    UNWIND relationships(p) AS rel

    WITH
        startNode(rel) AS s,
        endNode(rel) AS t,
        rel

    RETURN DISTINCT
        s.account_id AS source,
        t.account_id AS target,
        rel.amount AS amount
    """

    result = neo4j_client.execute(
        query,
        {
            "account_id": account_id
        }
    )

    links = []
    node_ids = set()

    for row in result:

        source = row["source"]
        target = row["target"]

        node_ids.add(source)
        node_ids.add(target)

        links.append(
            {
                "source": source,
                "target": target,
                "amount": row["amount"]
            }
        )

    nodes = []

    for node in node_ids:

        node_query = """
        MATCH (a:Account {
            account_id:$id
        })

        RETURN
            a.account_id AS id,
            coalesce(a.risk_score,0) AS risk,
            coalesce(a.community,-1) AS community,
            coalesce(a.pagerank,0) AS pagerank
        """

        account = neo4j_client.execute(
            node_query,
            {
                "id": node
            }
        ).single()

        nodes.append(
            dict(account)
        )

    return {
        "nodes": nodes,
        "links": links
    }
