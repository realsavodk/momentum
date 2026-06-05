"""Momentum scoring and next-period prediction — the ML layer.

Descriptive layer (compute_momentum):
    Scores each song by its popularity history using exponential time-decay.
    Recent snapshots are weighted more heavily. A climbing song outranks one
    that was big months ago but is now fading.

        weight(age) = exp(-lambda * age)        age = periods ago, 0 = most recent
        score       = sum(pop_t * weight_t) / sum(weight_t)

Predictive layer (predict_next_period):
    Builds a feature matrix per track (decay score, trend, acceleration,
    volatility, peak, mean popularity, recency) and trains a RandomForest
    regressor to predict next-period popularity. SHAP values explain which
    features drove each prediction — mirroring recency-weighted feature
    engineering used in financial ML (fraud/credit models).
"""
from collections import defaultdict
import numpy as np


def _group_by_period(
    history: list,
) -> tuple:
    """Group snapshot rows into calendar-month periods (YYYY-MM).

    Multiple snapshots in the same month are averaged so the model
    sees one value per period per track.
    """
    monthly = defaultdict(lambda: defaultdict(list))
    names = {}
    for row in history:
        month = row["captured_at"][:7]
        monthly[month][row["track_id"]].append(row["popularity"])
        names[row["track_id"]] = row["track_name"]

    periods = sorted(monthly.keys())
    by_track = defaultdict(dict)
    for month, tracks in monthly.items():
        for track_id, pops in tracks.items():
            by_track[track_id][month] = round(sum(pops) / len(pops))

    return periods, by_track, names


def _feature_vector(series: dict, periods: list, decay: float = 0.7) -> dict:
    """Compute a feature vector for one track given its series up to `periods`.

    Uses a high default decay (0.7) so recent periods dominate. Features are
    designed to capture *trajectory* rather than absolute popularity, so that
    a rising newer track outranks a stable all-time hit.
    """
    pops = [series.get(p, 0) for p in periods]
    nonzero = [p for p in pops if p > 0]
    if not nonzero:
        return {}

    n = len(periods)
    weighted_sum = sum(pops[i] * np.exp(-decay * (n - 1 - i)) for i in range(n))
    weight_total = sum(np.exp(-decay * (n - 1 - i)) for i in range(n) if pops[i] > 0)
    decay_score = weighted_sum / weight_total if weight_total else 0.0

    trend = pops[-1] - pops[-2] if len(pops) >= 2 else 0
    trend_prev = pops[-2] - pops[-3] if len(pops) >= 3 else 0
    acceleration = trend - trend_prev

    # how much above its own baseline is this track performing recently?
    historical_mean = float(np.mean(nonzero))
    recent = [pops[i] for i in range(max(0, n - 2), n) if pops[i] > 0]
    recent_mean = float(np.mean(recent)) if recent else historical_mean
    recent_growth = (recent_mean / historical_mean) - 1.0

    # trend normalized by the track's own mean — avoids big songs dominating
    relative_trend = trend / (historical_mean + 1.0)

    return {
        "decay_score": float(decay_score),
        "trend": float(trend),
        "acceleration": float(acceleration),
        "recent_growth": recent_growth,
        "relative_trend": relative_trend,
        "volatility": float(np.std(nonzero)),
        "recency": len(nonzero) / max(n, 1),
    }


FEATURES = ["decay_score", "trend", "acceleration", "recent_growth", "relative_trend", "volatility", "recency"]


def compute_momentum(history: list, decay: float = 0.4) -> list:
    """Return songs ranked by decayed momentum score."""
    if not history:
        return []

    periods, by_track, names = _group_by_period(history)
    n = len(periods)
    period_index = {p: i for i, p in enumerate(periods)}

    results = []
    for track_id, series in by_track.items():
        weighted_sum = 0.0
        weight_total = 0.0
        for period, pop in series.items():
            age = (n - 1) - period_index[period]
            w = np.exp(-decay * age)
            weighted_sum += pop * w
            weight_total += w
        raw = weighted_sum / weight_total if weight_total else 0.0

        sorted_periods = sorted(series.keys())
        trend = (
            series[sorted_periods[-1]] - series[sorted_periods[-2]]
            if len(sorted_periods) >= 2 else 0
        )
        results.append({"track_id": track_id, "name": names[track_id], "raw": raw, "trend": trend})

    max_raw = max((r["raw"] for r in results), default=1.0) or 1.0
    for r in results:
        r["score"] = round(r["raw"] / max_raw * 100)
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def predict_next_period(history: list, decay: float = 0.7) -> list:
    """Train a RandomForest on historical track data and predict next-period momentum.

    For each track × period, features are built from all prior periods and the
    target is that period's popularity. The trained model then predicts the next
    unseen period. SHAP TreeExplainer produces per-feature attributions.

    Requires at least 3 months of history and 5 training samples to run.
    Returns [] if there is insufficient data.
    """
    if not history:
        return []

    periods, by_track, names = _group_by_period(history)
    if len(periods) < 3:
        return []

    # Build training data: features from periods 0..i-1, target = popularity at period i
    X_rows, y_rows = [], []
    for period_idx in range(2, len(periods)):
        prior_periods = periods[:period_idx]
        target_period = periods[period_idx]
        for track_id, series in by_track.items():
            target_raw = series.get(target_period, 0)
            if not target_raw:
                continue
            prior_series = {p: series[p] for p in prior_periods if p in series}
            if not prior_series:
                continue
            prior_mean = float(np.mean(list(prior_series.values()))) + 1.0
            # relative target: how much above its own baseline did this track perform?
            target = target_raw / prior_mean
            fv = _feature_vector(prior_series, prior_periods, decay=decay)
            if fv:
                X_rows.append([fv[f] for f in FEATURES])
                y_rows.append(target)

    if len(X_rows) < 5:
        return []

    from sklearn.ensemble import RandomForestRegressor
    import shap

    X = np.array(X_rows)
    y = np.array(y_rows)

    # standardize
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-8
    X_norm = (X - X_mean) / X_std

    model = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
    model.fit(X_norm, y)

    # predict next period for each track using full history
    pred_rows, pred_ids = [], []
    for track_id, series in by_track.items():
        fv = _feature_vector(series, periods, decay=decay)
        if fv:
            pred_rows.append([fv[f] for f in FEATURES])
            pred_ids.append(track_id)

    if not pred_rows:
        return []

    X_pred = (np.array(pred_rows) - X_mean) / X_std
    predictions = model.predict(X_pred)

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_pred)

    max_pred = max(predictions) or 1.0
    results = []
    for i, track_id in enumerate(pred_ids):
        shap_dict = {f: round(float(shap_vals[i][j]), 2) for j, f in enumerate(FEATURES)}
        results.append({
            "track_id": track_id,
            "name": names[track_id],
            "predicted_score": round(float(predictions[i]) / max_pred * 100),
            "shap_values": shap_dict,
        })

    results.sort(key=lambda r: r["predicted_score"], reverse=True)
    return results
