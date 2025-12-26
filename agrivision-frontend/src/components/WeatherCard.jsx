import React from "react";

const WeatherCard = () => {
  // Static data for now
  const weather = {
    condition: "Sunny",
    temperature: "32°C",
    humidity: "65%",
  };

  return (
    <div
      style={{
        backgroundColor: "#ffffff",
        borderRadius: "12px",
        padding: "20px",
        minWidth: "260px",
        boxShadow: "0 2px 6px rgba(0,0,0,0.08)",
      }}
    >
      <h4 style={{ margin: 0, marginBottom: "12px" }}>
        Weather Today
      </h4>

      <div style={{ fontSize: "32px", marginBottom: "8px" }}>
        ☀️ {weather.temperature}
      </div>

      <p style={{ margin: "4px 0", color: "#555" }}>
        Condition: <strong>{weather.condition}</strong>
      </p>

      <p style={{ margin: "4px 0", color: "#555" }}>
        Humidity: <strong>{weather.humidity}</strong>
      </p>
    </div>
  );
};

export default WeatherCard;
