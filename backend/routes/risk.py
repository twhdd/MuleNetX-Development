from fastapi import APIRouter

from backend.core.cache import (
    cache_get,
    cache_set
)
from backend.neo4j_client import neo4j_client

router = APIRouter()


@router.get("/risk/account/{account_id}")
def account_risk(account_id: str):
    query = """
    MATCH (a:Account {account_id: $account_id})
    RETURN
        a.account_id AS account_id,
        coalesce(a.fraud_probability, 0.0) AS fraud_probability,
        coalesce(a.risk_score, 0.0) AS risk_score,
        coalesce(a.risk_category, "LOW") AS risk_category,
        coalesce(a.predicted_label, 0) AS predicted_label,
        coalesce(a.top_risk_drivers, "") AS top_risk_drivers,
        coalesce(a.explanation, "") AS explanation
    """
    result = neo4j_client.execute(query, {"account_id": account_id}).single()
    if result is None:
        return {"account_id": account_id, "found": False}
    return {"found": True, **dict(result)}


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
        coalesce(a.risk_score, 0) AS risk,
        coalesce(a.explanation, "") AS explanation,
        coalesce(a.risk_category, "LOW") AS risk_category
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
