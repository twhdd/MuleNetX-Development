import React from "react";
import ExecutiveSummary from "../components/executive/ExecutiveSummary";
import BusinessKPIs from "../components/executive/BusinessKPIs";
import RecommendationPanel from "../components/executive/RecommendationPanel";
import ThreatOverview from "../components/executive/ThreatOverview";
import QuickActions from "../components/executive/QuickActions";

export default function ExecutiveDashboard() {
  return (
    <div
      style={{
        background: "#050505",
        minHeight: "100vh",
        color: "white",
        padding: "25px",
      }}
    >
      <h1
        style={{
          fontSize: "34px",
          marginBottom: "5px",
          fontWeight: 700,
        }}
      >
        Executive Intelligence Center
      </h1>

      <p
        style={{
          color: "#888",
          marginBottom: "30px",
        }}
      >
        AI Powered Business • Financial • Cyber Intelligence
      </p>

      <ExecutiveSummary />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: "20px",
          marginTop: "25px",
        }}
      >
        <BusinessKPIs />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "25px",
          marginTop: "25px",
        }}
      >
        <RecommendationPanel />
        <ThreatOverview />
      </div>

      <div
        style={{
          marginTop: "25px",
        }}
      >
        <QuickActions />
      </div>
    </div>
  );
}
