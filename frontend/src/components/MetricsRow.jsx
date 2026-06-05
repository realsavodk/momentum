// Four summary metric cards. Top song and predicted hit come from the momentum scores.

export default function MetricsRow({ artist, topTracks, momentum }) {
  const topSong = topTracks?.[0]?.name || "—";
  const predicted = momentum?.[0];

  return (
    <div className="metrics">
      <div className="metric">
        <div className="label">Popularity</div>
        <div className="value">{artist?.popularity ?? "—"}</div>
        <div className="delta muted">0–100 scale</div>
      </div>
      <div className="metric">
        <div className="label">Tracked songs</div>
        <div className="value">{topTracks?.length ?? 0}</div>
        <div className="delta muted">top tracks</div>
      </div>
      <div className="metric">
        <div className="label">Top song</div>
        <div className="value small">{topSong}</div>
        <div className="delta muted">current</div>
      </div>
      <div className="metric">
        <div className="label">Sound of the moment</div>
        <div className="value small">{predicted?.name || "—"}</div>
        <div className="delta up">
          {predicted ? `Score: ${predicted.score}` : "needs history"}
        </div>
      </div>
    </div>
  );
}
