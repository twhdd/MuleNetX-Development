from datetime import datetime

from backend.services.intelligence.forecast_engine import (
    engine as forecast_engine
)

from backend.services.intelligence.recommendation_engine import (
    engine as recommendation_engine
)

from backend.services.intelligence.temporal_engine import (
    engine as temporal_engine
)


class ExecutiveEngine:

    def build(self):

        forecast = forecast_engine.forecast()

        recommendation = recommendation_engine.generate()

        temporal = temporal_engine.timeline()

        highest_alert = max(

            temporal["timeline"],

            key=lambda x: x["alerts"]

        )

        average_anomaly = round(

            sum(

                t["anomalyScore"]

                for t in temporal["timeline"]

            ) / len(temporal["timeline"]),

            2

        )

        return {

            "generatedAt": datetime.now().strftime("%I:%M:%S %p"),

            "forecastConfidence":

                forecast["forecastConfidence"],

            "averageAnomaly":

                average_anomaly,

            "peakHour":

                highest_alert["time"],

            "peakAlerts":

                highest_alert["alerts"],

            "recommendation":

                recommendation,

            "forecast":

                forecast,

            "timeline":

                temporal

        }


engine = ExecutiveEngine()
