from fastapi import APIRouter

from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary():

    query = """
    MATCH (a:Account)

    RETURN
        count(a) AS total_accounts,
        avg(a.risk_score) AS avg_risk,
        max(a.risk_score) AS max_risk
    """

    result = neo4j_client.execute(query)

    row = result.single()

    return dict(row)
