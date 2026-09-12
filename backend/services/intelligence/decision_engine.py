from datetime import datetime

from backend.services.intelligence.recommendation_engine import (
    engine as recommendation_engine
)

from backend.services.intelligence.forecast_engine import (
    engine as forecast_engine
)

from backend.services.intelligence.temporal_engine import (
    engine as temporal_engine
)


class DecisionEngine:

    def evaluate(self):

        recommendation = recommendation_engine.generate()

        forecast = forecast_engine.forecast()

        temporal = temporal_engine.timeline()

        tomorrow = forecast["predictions"][1]

        score = 0

        if recommendation["priority"] == "CRITICAL":
            score += 40

        elif recommendation["priority"] == "HIGH":
            score += 25

        score += int(recommendation["confidence"] / 2)

        score += int(
            temporal["timeline"][-1]["anomalyScore"] * 20
        )

        score = min(score, 100)

        return {

            "generatedAt":

                datetime.now().strftime("%I:%M:%S %p"),

            "decisionScore":

                score,

            "decision":

                recommendation,

            "forecast":

                tomorrow,

            "currentRisk":

                temporal["timeline"][-1]["risk"],

            "nextAction":

                recommendation["title"],

            "confidence":

                recommendation["confidence"]

        }


engine = DecisionEngine()
