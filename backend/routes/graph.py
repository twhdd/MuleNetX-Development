from fastapi import APIRouter

from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/graph/{account_id}")
def graph_data(account_id: str):

    query = """
    MATCH p=
    (a:Account {account_id:$account_id})
    -[t:TRANSFER*1..2]->
    (b)

    WITH nodes(p) AS ns

    UNWIND ns AS n

    RETURN DISTINCT
        n.account_id AS account,
        coalesce(n.risk_score,0) AS risk,
        coalesce(n.community,-1) AS community
    """

    result = neo4j_client.execute(
        query,
        {"account_id": account_id}
    )

    return [dict(x) for x in result]
