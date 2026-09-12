from fastapi import APIRouter

from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/community/top")
def top_communities():

    query = """
    MATCH (a:Account)

    RETURN
        a.community AS community,
        count(*) AS members,
        avg(a.risk_score) AS avg_risk

    ORDER BY avg_risk DESC

    LIMIT 50
    """

    result = neo4j_client.execute(query)

    return [dict(x) for x in result]
