from datetime import datetime, timedelta
import random


class ForecastEngine:

    def __init__(self):

        self.confidence = 93.4

    def forecast(self):

        predictions = []

        current = datetime.now()

        base_transactions = random.randint(18000, 24000)
        base_fraud = random.randint(120, 180)

        for i in range(7):

            transactions = base_transactions + random.randint(-800, 1200)

            fraud = base_fraud + random.randint(-15, 25)

            exposure = round(random.uniform(1.4, 3.8), 2)

            predictions.append({

                "date": (current + timedelta(days=i)).strftime("%d %b"),

                "transactions": transactions,

                "predictedFraud": fraud,

                "financialExposure": f"₹{exposure} Cr"

            })

        return {

            "forecastConfidence": self.confidence,

            "generatedAt": datetime.now().strftime("%I:%M:%S %p"),

            "predictions": predictions

        }


engine = ForecastEngine()
