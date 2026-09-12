from datetime import datetime, timedelta
import random


class TemporalEngine:

    def __init__(self):

        self.risk_levels = [
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL"
        ]

        self.events = [
            "Transaction Burst",
            "Money Mule Activity",
            "Suspicious Login",
            "Large Fund Transfer",
            "Fraud Ring Expansion",
            "High Velocity Payments",
            "Device Change",
            "AI Recommendation Triggered",
            "Investigation Started",
            "Accounts Frozen"
        ]

    def timeline(self):

        timeline = []

        now = datetime.now().replace(minute=0, second=0, microsecond=0)

        for hour in range(24):

            timestamp = now - timedelta(hours=23-hour)

            transactions = random.randint(500, 2500)

            alerts = random.randint(0, 18)

            anomaly = round(random.uniform(0.15, 0.99), 2)

            risk = random.choices(

                self.risk_levels,

                weights=[35, 30, 25, 10]

            )[0]

            timeline.append({

                "time": timestamp.strftime("%H:%M"),

                "transactions": transactions,

                "alerts": alerts,

                "anomalyScore": anomaly,

                "risk": risk,

                "event": random.choice(self.events)

            })

        return {

            "generatedAt": datetime.now().strftime("%I:%M:%S %p"),

            "window": "24 Hours",

            "timeline": timeline

        }


engine = TemporalEngine()
