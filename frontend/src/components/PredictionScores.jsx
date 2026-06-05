// Momentum scores with decay slider + a single "sound of the moment" card.

const PALETTE = ["#1db954", "#378add", "#d4537e", "#ba7517", "#7f77dd", "#1d9e75",
  "#e24b4a", "#888780"];

const FEATURE_PHRASES = {
  decay_score:    { pos: "it's been building real momentum lately",       neg: "its momentum has been fading" },
  trend:          { pos: "popularity has been climbing month over month", neg: "popularity has been sliding" },
  acceleration:   { pos: "that growth is picking up speed",              neg: "growth has been losing steam" },
  recent_growth:  { pos: "it's well above its own historical average",   neg: "it's slipped below its historical average" },
  relative_trend: { pos: "the upward trend is strong for its level",     neg: "the trend is weak relative to its level" },
  volatility:     { pos: "its popularity has stayed consistent",         neg: "its popularity has been unpredictable" },
  recency:        { pos: "it has a solid recent track record",           neg: "recent data is limited" },
};

// Features that measure the same underlying thing — only the highest-|SHAP|
// one from each group is used so the explanation never contradicts itself.
const SEMANTIC_GROUP = {
  decay_score:    "momentum",
  trend:          "direction",
  relative_trend: "direction",   // trend normalised by mean — same family
  recent_growth:  "level",
  acceleration:   "trajectory",
  volatility:     "consistency",
  recency:        "consistency",
};

function shapExplanation(shap_values) {
  const sorted = Object.entries(shap_values)
    .filter(([, v]) => Math.abs(v) > 0.01)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  if (!sorted.length) return "Not enough signal to explain this track's momentum.";

  const positives = sorted.filter(([, v]) => v > 0);
  const negatives = sorted.filter(([, v]) => v < 0);

  // Pick up to 2 positive drivers from different semantic groups
  const seenGroups = new Set();
  const picks = [];
  for (const [key, val] of positives) {
    const group = SEMANTIC_GROUP[key] ?? key;
    if (seenGroups.has(group)) continue;
    seenGroups.add(group);
    picks.push([key, val]);
    if (picks.length === 2) break;
  }

  if (!picks.length) {
    return "This track scored highest overall despite mixed momentum signals.";
  }

  const posPhrases = picks.map(([k]) => FEATURE_PHRASES[k]?.pos ?? k);
  const body = posPhrases.length === 1
    ? posPhrases[0]
    : `${posPhrases[0]} and ${posPhrases[1]}`;

  // Add a "even though" clause only when the top negative outweighs the smaller positive
  const topNeg = negatives[0];
  const smallerPickVal = Math.abs(picks[picks.length - 1]?.[1] ?? 0);
  const negPhrase = topNeg && Math.abs(topNeg[1]) > smallerPickVal * 0.7
    ? FEATURE_PHRASES[topNeg[0]]?.neg
    : null;

  return `This track is resonating right now because ${body}${negPhrase ? `, even though ${negPhrase}` : ""}.`;
}

export default function PredictionScores({ scores, decay, onDecayChange, predictions }) {
  const nextHit = predictions;

  return (
    <div className="card">
      <h2>ML momentum scores</h2>
      <p className="desc">
        Exponential time-decay weighting — recent periods score higher.
      </p>

      <div className="decay-control">
        <span>Decay λ</span>
        <input
          type="range"
          min="0.1"
          max="0.9"
          step="0.1"
          value={decay}
          onChange={(e) => onDecayChange(parseFloat(e.target.value))}
        />
        <span style={{ color: "var(--text)", fontWeight: 600, minWidth: 28 }}>
          {decay.toFixed(1)}
        </span>
      </div>

      {!scores?.length ? (
        <p className="muted">No history yet — momentum needs at least one snapshot.</p>
      ) : (
        <ul className="pred-list">
          {scores.map((s, i) => {
            const color = PALETTE[i % PALETTE.length];
            const trendStr =
              s.trend > 0 ? `↑ +${s.trend}` : s.trend < 0 ? `↓ ${s.trend}` : "→";
            const trendClass = s.trend > 0 ? "up" : s.trend < 0 ? "down" : "muted";
            return (
              <li className="pred-item" key={s.track_id}>
                <span className="pred-rank">{i + 1}</span>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
                <span className="pred-name">{s.name}</span>
                <span className={trendClass} style={{ fontSize: 12, minWidth: 44, textAlign: "right" }}>
                  {trendStr}
                </span>
                <span className="pred-score">{s.score}</span>
              </li>
            );
          })}
        </ul>
      )}

      {nextHit && (
        <div style={{ marginTop: 24 }}>
          <h2>Sound of the moment</h2>
          <p className="desc">The track in this artist's catalog that's resonating the most with listeners right now.</p>
          <div style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 12 }}>
            {nextHit.image && (
              <img
                src={nextHit.image}
                alt={nextHit.name}
                style={{ width: 80, height: 80, borderRadius: 8, objectFit: "cover", flexShrink: 0 }}
              />
            )}
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>{nextHit.name}</div>
              <div style={{ fontSize: 13, marginTop: 6, lineHeight: 1.5, color: "var(--text-muted)" }}>
                {shapExplanation(nextHit.shap_values)}
              </div>
              <div style={{ fontSize: 12, marginTop: 4, color: "var(--text-muted)" }}>
                Momentum score: {nextHit.predicted_score}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
