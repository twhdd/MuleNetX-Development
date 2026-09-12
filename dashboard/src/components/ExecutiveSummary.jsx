import "./ExecutiveSummary.css";

export default function ExecutiveSummary() {

    const summary = {
        confidence: 94.2,
        exposure: "₹2.31 Cr",
        recovery: "+7.8%",
        fraudIncrease: "+11.4%",
        lastUpdated: "10:42 AM",

        findings: [
            "Two new fraud rings identified in Karnataka.",
            "Transaction velocity increased across western regions.",
            "14 accounts require immediate analyst review."
        ],

        recommendations: [
            "Freeze 12 high-risk accounts.",
            "Increase monitoring for Maharashtra and Karnataka.",
            "Escalate Cluster-17 investigation.",
            "Retrain fraud model with latest transaction batch."
        ]
    };

    return (

        <section className="executive-summary">

            <div className="summary-top">

                <div>

                    <p className="summary-tag">
                        AI EXECUTIVE SUMMARY
                    </p>

                    <h1>
                        Executive Intelligence
                    </h1>

                    <p className="summary-date">
                        Last Updated • {summary.lastUpdated}
                    </p>

                </div>

                <div className="confidence-box">

                    <span>Confidence</span>

                    <h2>{summary.confidence}%</h2>

                </div>

            </div>

            <div className="summary-grid">

                <div className="summary-card">

                    <h3>Business Overview</h3>

                    <div className="metric">

                        <span>Fraud Activity</span>

                        <strong className="danger">
                            {summary.fraudIncrease}
                        </strong>

                    </div>

                    <div className="metric">

                        <span>Financial Exposure</span>

                        <strong className="warning">
                            {summary.exposure}
                        </strong>

                    </div>

                    <div className="metric">

                        <span>Recovery Efficiency</span>

                        <strong className="success">
                            {summary.recovery}
                        </strong>

                    </div>

                </div>

                <div className="summary-card">

                    <h3>AI Findings</h3>

                    <ul>

                        {summary.findings.map((item, index) => (

                            <li key={index}>
                                {item}
                            </li>

                        ))}

                    </ul>

                </div>

                <div className="summary-card">

                    <h3>Recommended Actions</h3>

                    <ul>

                        {summary.recommendations.map((item, index) => (

                            <li key={index}>
                                {item}
                            </li>

                        ))}

                    </ul>

                </div>

            </div>

        </section>

    );

}
