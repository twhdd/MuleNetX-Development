from datetime import datetime
import random


class ExecutiveService:

    def __init__(self):

        self.states = [
            "Karnataka",
            "Maharashtra",
            "Delhi",
            "Tamil Nadu",
            "Telangana"
        ]

        self.patterns = [
            "Layering",
            "Money Mule Network",
            "Synthetic Identity",
            "Transaction Burst",
            "Account Takeover"
        ]

    def generate_summary(self):

        fraud_change = round(random.uniform(6.0, 15.0), 1)

        recovery = round(random.uniform(3.0, 10.0), 1)

        confidence = round(random.uniform(91.0, 98.5), 1)

        exposure = round(random.uniform(1.5, 4.8), 2)

        state = random.choice(self.states)

        pattern = random.choice(self.patterns)

        findings = [

            f"Fraud activity increased {fraud_change}% in {state}.",

            f"{pattern} remains the dominant attack pattern.",

            "14 accounts require analyst review.",

            "Two new fraud rings detected."

        ]

        recommendations = [

            "Freeze high-risk accounts.",

            "Increase monitoring in high-risk regions.",

            "Escalate Cluster-17 investigation.",

            "Retrain fraud detection model."

        ]

        return {

            "confidence": confidence,

            "fraudIncrease": f"+{fraud_change}%",

            "financialExposure": f"₹{exposure} Cr",

            "recoveryEfficiency": f"+{recovery}%",

            "lastUpdated": datetime.now().strftime("%I:%M %p"),

            "findings": findings,

            "recommendations": recommendations

        }


service = ExecutiveService()
