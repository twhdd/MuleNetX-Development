from fastapi import APIRouter

from intelligence_core.fraud_detection.fanout_detector import (
    detect_fanout
)

from intelligence_core.fraud_detection.mule_detector import (
    detect_mules
)

from intelligence_core.fraud_detection.pattern_matcher import (
    find_smurfing
)

router = APIRouter()


@router.get(
    "/patterns/smurfing"
)
def smurfing():

    return find_smurfing()


@router.get(
    "/patterns/mules"
)
def mules():

    return detect_mules()


@router.get(
    "/patterns/fanout"
)
def fanout():

    return detect_fanout()
