from fastapi import APIRouter

from investigation_engine.ring_detector import detect_fraud_rings
from investigation_engine.community_risk import score_communities

router = APIRouter()


@router.get("/fraud-rings")
def fraud_rings():

    return detect_fraud_rings()


@router.get("/communities")
def communities():

    return score_communities()
