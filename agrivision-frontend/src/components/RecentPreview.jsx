import React from "react";

const RecentPreview = () => {
  // Static mock data
  const recentAnalyses = [
    {
      id: 1,
      result: "Healthy",
      confidence: "98%",
      date: "25 Sep 2025",
      status: "healthy",
    },
    {
      id: 2,
      result: "Leaf Blight",
      confidence: "96%",
      date: "24 Sep 2025",
      status: "diseased",
    },
    {
      id: 3,
      result: "Healthy",
      confidence: "99%",
      date: "23 Sep 2025",
      status: "healthy",
    },
  ];

  return (
    <div style={{ marginTop: "32px" }}>
      <h3 style={{ marginBottom: "16px" }}>
        Recent Analyses
      </h3>

      {recentAnalyses.length === 0 ? (
        <p style={{ color: "#777" }}>
          No recent analysis. Upload an image to get started.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {recentAnalyses.slice(0, 3).map((item) => (
            <div
              key={item.id}
              style={{
                backgroundColor: "#fff",
                padding: "14px 18px",
                borderRadius: "10px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
              }}
            >
              <div>
                <strong>{item.result}</strong>
                <p style={{ margin: 0, fontSize: "13px", color: "#666" }}>
                  Confidence: {item.confidence}
                </p>
              </div>

              <div style={{ textAlign: "right" }}>
                <span
                  style={{
                    padding: "4px 10px",
                    borderRadius: "12px",
                    fontSize: "12px",
                    color: "#fff",
                    backgroundColor:
                      item.status === "healthy" ? "#2E7D32" : "#D32F2F",
                  }}
                >
                  {item.status === "healthy" ? "Healthy" : "Diseased"}
                </span>
                <p style={{ margin: 0, fontSize: "12px", color: "#777" }}>
                  {item.date}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecentPreview;
