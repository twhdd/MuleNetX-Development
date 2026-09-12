from fastapi import APIRouter

from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get(
    "/transactions/live"
)
def transactions():

    query = """
    MATCH ()-[t:TRANSFER]->()

    RETURN
        t.transaction_id AS tx,
        t.amount AS amount,
        t.timestamp AS timestamp

    ORDER BY timestamp DESC

    LIMIT 100
    """

    result = neo4j_client.execute(
        query
    )

    return [
        dict(x)
        for x in result
    ]
