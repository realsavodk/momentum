export default function LoadingSkeleton() {
  return (
    <div className="app">
      {/* Artist header */}
      <div className="skeleton-header">
        <div className="skeleton skeleton-avatar" />
        <div className="skeleton-lines">
          <div className="skeleton skeleton-line" style={{ width: "40%", height: 22 }} />
          <div className="skeleton skeleton-line" style={{ width: "60%" }} />
        </div>
      </div>

      {/* Metric cards */}
      <div className="skeleton-metrics">
        {[1, 2, 3, 4].map((i) => (
          <div className="skeleton-card" key={i}>
            <div className="skeleton skeleton-line" style={{ width: "50%", height: 11 }} />
            <div className="skeleton skeleton-line" style={{ width: "35%", height: 26, marginTop: 12 }} />
            <div className="skeleton skeleton-line" style={{ width: "45%", height: 11, marginTop: 8 }} />
          </div>
        ))}
      </div>

      {/* Chart card */}
      <div className="skeleton-card" style={{ marginBottom: "1.5rem" }}>
        <div className="skeleton skeleton-line" style={{ width: "30%", height: 16 }} />
        <div className="skeleton skeleton-line" style={{ width: "55%", height: 12, marginTop: 8 }} />
        <div className="skeleton skeleton-chart-area" />
      </div>

      {/* 2-column bottom */}
      <div className="grid-2">
        <div className="skeleton-card skeleton-card-tall" />
        <div className="skeleton-card skeleton-card-tall" />
      </div>
    </div>
  );
}
