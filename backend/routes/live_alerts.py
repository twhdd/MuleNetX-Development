from fastapi import APIRouter

from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get(
    "/alerts/high-risk"
)
def high_risk_alerts():

    query = """
    MATCH (a:Account)

    WHERE
    a.risk_score >= 0.80

    RETURN
        a.account_id AS account,
        a.risk_score AS risk,
        a.community AS community

    ORDER BY
        risk DESC

    LIMIT 100
    """

    result = neo4j_client.execute(
        query
    )

    return [
        dict(row)
        for row in result
    ]
