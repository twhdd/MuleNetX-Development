from fastapi import APIRouter

from backend.core.cache import (
    cache_get,
    cache_set
)
from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/risk/top")
def top_risk():
    try:
        cached = cache_get(
            "risk_top"
        )
        if cached:
            return cached
    except Exception:
        cached = None

    query = """
    MATCH (a:Account)
    RETURN
        a.account_id AS account,
        coalesce(a.risk_score, 0) AS risk
    ORDER BY risk DESC
    LIMIT 50
    """

    result = neo4j_client.execute(query)

    data = [
        dict(x)
        for x in result
    ]

    try:
        cache_set(
            "risk_top",
            data,
            300
        )
    except Exception:
        pass

    return data
