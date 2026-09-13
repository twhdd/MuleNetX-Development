from investigation_engine.ring_detector import detect_fraud_rings
from investigation_engine.community_risk import score_communities


def generate_summary():

    communities = score_communities()
    rings = detect_fraud_rings()

    report = {
        "high_risk_communities": communities[:10],
        "top_accounts": rings[:50]
    }

    return report
