from dataclasses import dataclass
from typing import List
import random


@dataclass
class Recommendation:

    title: str
    priority: str
    confidence: float
    impact: str
    description: str


class RecommendationEngine:

    def __init__(self):

        self.templates = [

            Recommendation(
                title="Freeze High-Risk Accounts",
                priority="CRITICAL",
                confidence=94.2,
                impact="Estimated Fraud Reduction: 31%",
                description="Accounts exceeded fraud threshold and are strongly connected to an active fraud ring."
            ),

            Recommendation(
                title="Escalate Investigation",
                priority="HIGH",
                confidence=92.8,
                impact="Reduce Investigation Time",
                description="Community Cluster-17 expanded significantly over the last 24 hours."
            ),

            Recommendation(
                title="Increase Regional Monitoring",
                priority="HIGH",
                confidence=90.5,
                impact="Reduce Regional Exposure",
                description="Transaction velocity anomaly detected across western region."
            ),

            Recommendation(
                title="Retrain Fraud Model",
                priority="MEDIUM",
                confidence=88.4,
                impact="Improve Detection Accuracy",
                description="Feature drift detected within recent transaction batches."
            )

        ]

    def generate(self):

        recommendation = random.choice(self.templates)

        return {

            "title": recommendation.title,

            "priority": recommendation.priority,

            "confidence": recommendation.confidence,

            "impact": recommendation.impact,

            "description": recommendation.description

        }


engine = RecommendationEngine()
