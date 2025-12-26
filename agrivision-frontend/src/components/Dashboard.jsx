import React from "react";
import StatCard from "./StatCard";
import WeatherCard from "./WeatherCard";
import RecentPreview from "./RecentPreview";


const Dashboard = () => {
  const stats = {
    total: 0,
    healthy: 0,
    diseased: 0,
  };

  return (
    <div
  style={{
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "20px",
    marginTop: "24px",
    alignItems: "stretch",
  }}
>
      <h2 style={{ marginBottom: "4px" }}>Welcome back, Udayraj!</h2>
      <p style={{ marginTop: 0, color: "#666" }}>
        Monitor your crop health and get disease insights
      </p>

      <div
        style={{
          display: "flex",
          gap: "20px",
          marginTop: "24px",
          flexWrap: "wrap",
        }}
      >
        <StatCard
          title="Total Analyses"
          value={stats.total}
          icon="📊"
          color="#4CAF50"
        />

        <StatCard
          title="Healthy"
          value={stats.healthy}
          icon="✅"
          color="#2E7D32"
        />

        <StatCard
          title="Diseased"
          value={stats.diseased}
          icon="⚠️"
          color="#D32F2F"
        />

        {/* Weather Card */}
        <WeatherCard />
      </div>
      <RecentPreview />
    </div>
  );
};

export default Dashboard;
