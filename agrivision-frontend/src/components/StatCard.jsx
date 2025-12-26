import React from "react";

const StatCard = ({ title, value, icon, color }) => {
  return (
    <div
      style={{
        backgroundColor: "#ffffff",
        borderRadius: "12px",
        padding: "20px",
        display: "flex",
        alignItems: "center",
        gap: "16px",
        boxShadow: "0 2px 6px rgba(0,0,0,0.08)",
        borderLeft: `6px solid ${color}`,
        minWidth: "220px",
      }}
    >
      <div
        style={{
          fontSize: "28px",
          color: color,
        }}
      >
        {icon}
      </div>

      <div>
        <h4 style={{ margin: 0, fontSize: "14px", color: "#666" }}>
          {title}
        </h4>
        <p style={{ margin: 0, fontSize: "26px", fontWeight: "bold" }}>
          {value}
        </p>
      </div>
    </div>
  );
};

export default StatCard;
