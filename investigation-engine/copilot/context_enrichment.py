from intelligence_core.fraud_detection.mule_detector import (
    detect_mules
)

from intelligence_core.fraud_detection.pattern_matcher import (
    find_smurfing
)

from intelligence_core.fraud_detection.fanout_detector import (
    detect_fanout
)


def enrich_context():

    return {
        "mules":
        detect_mules()[:10],

        "smurfing":
        find_smurfing()[:10],

        "fanout":
        detect_fanout()[:10]
    }
