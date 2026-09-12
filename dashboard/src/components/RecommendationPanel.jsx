import { useEffect, useState } from "react";
import "./RecommendationPanel.css";

export default function RecommendationPanel() {

    const [recommendation, setRecommendation] = useState(null);

    useEffect(() => {

        fetch("http://localhost:8000/api/recommendation")

            .then(res => res.json())

            .then(data => setRecommendation(data));

    }, []);

    if (!recommendation) {

        return null;

    }

    return (

        <div className="recommendation-panel">

            <h2>AI Recommendation</h2>

            <h3>{recommendation.title}</h3>

            <p>{recommendation.description}</p>

            <div className="recommendation-grid">

                <div>

                    <span>Priority</span>

                    <strong>{recommendation.priority}</strong>

                </div>

                <div>

                    <span>Confidence</span>

                    <strong>{recommendation.confidence}%</strong>

                </div>

                <div>

                    <span>Impact</span>

                    <strong>{recommendation.impact}</strong>

                </div>

            </div>

        </div>

    );

}
