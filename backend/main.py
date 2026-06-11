"""FastAPI app exposing the dashboard's data endpoints.

Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import logging
from collections import defaultdict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import database
import lastfm
import ml
from config import settings

log = logging.getLogger(__name__)
app = FastAPI(title="Momentum API")
scheduler = AsyncIOScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _snapshot_all() -> None:
    """Refresh snapshots for every artist that has been viewed at least once."""
    artist_ids = database.get_tracked_artists()
    for artist_id in artist_ids:
        try:
            tracks = await lastfm.get_top_tracks(artist_id)
            database.save_snapshot(artist_id, tracks)
        except Exception as e:
            log.warning("Snapshot failed for %s: %s", artist_id, e)


@app.on_event("startup")
async def _startup() -> None:
    database.init_db()
    scheduler.add_job(_snapshot_all, "interval", hours=24, id="daily_snapshot")
    scheduler.start()
    log.info("Scheduler started — snapshots will run every 24 hours.")


@app.on_event("shutdown")
def _shutdown() -> None:
    scheduler.shutdown()


@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    """Search artists by name."""
    return await lastfm.search_artists(q)


@app.get("/artist/{artist_id}")
async def artist(artist_id: str):
    """Artist profile + current top tracks. Saves a snapshot on each view.
    On first visit, seeds 6 months of synthetic history so charts and ML
    are immediately useful. The seed is fast (pure SQLite writes) so it
    runs synchronously before the response.
    """
    try:
        profile = await lastfm.get_artist(artist_id)
        tracks = await lastfm.get_top_tracks(artist_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Last.fm error: {e}")

    is_new = not database.has_history(artist_id)
    database.save_snapshot(artist_id, tracks)
    if is_new:
        database.seed_demo_snapshots(artist_id, tracks)

    return {"artist": profile, "top_tracks": tracks}


@app.get("/artist/{artist_id}/history")
async def history(artist_id: str):
    """Per-track popularity time-series grouped by calendar month.

    Also returns `monthly_new_plays`: total new Last.fm scrobbles across all
    tracks per period, computed as month-over-month deltas of raw playcounts.
    """
    rows = database.get_history(artist_id)

    monthly_pop: dict = defaultdict(lambda: defaultdict(list))
    monthly_plays: dict = defaultdict(lambda: defaultdict(list))
    names: dict = {}
    for r in rows:
        month = r["captured_at"][:7]
        monthly_pop[month][r["track_id"]].append(r["popularity"])
        monthly_plays[month][r["track_id"]].append(r.get("playcount", 0))
        names[r["track_id"]] = r["track_name"]

    periods = sorted(monthly_pop.keys())

    # per-track avg popularity per period (for ML + chart coloring)
    series: dict = {}
    for month, tracks in monthly_pop.items():
        for track_id, pops in tracks.items():
            if track_id not in series:
                series[track_id] = {"name": names[track_id], "points": {}}
            series[track_id]["points"][month] = round(sum(pops) / len(pops))

    # per-track max playcount per period (latest snapshot wins within a month)
    track_monthly_max: dict = defaultdict(dict)
    for month, tracks in monthly_plays.items():
        for track_id, counts in tracks.items():
            track_monthly_max[track_id][month] = max(counts)

    # delta = this month's count − previous month's count, summed across tracks
    monthly_new_plays = []
    for i, period in enumerate(periods):
        total_new = 0
        for track_id, by_month in track_monthly_max.items():
            if period not in by_month:
                continue
            prev = next(
                (by_month[periods[j]] for j in range(i - 1, -1, -1) if periods[j] in by_month),
                None,
            )
            if prev is None:
                continue  # first appearance — no prior count to diff against
            delta = by_month[period] - prev
            total_new += max(0, delta)  # ignore corrections that go negative
        monthly_new_plays.append(total_new)

    return {
        "periods": periods,
        "series": [
            {"track_id": tid, "name": s["name"],
             "data": [s["points"].get(p) for p in periods]}
            for tid, s in series.items()
        ],
        "monthly_new_plays": monthly_new_plays,
    }


@app.get("/artist/{artist_id}/momentum")
async def momentum(artist_id: str, decay: float = Query(0.4, ge=0.05, le=1.0)):
    """Ranked momentum scores. `decay` is the time-decay lambda from the slider."""
    rows = database.get_history(artist_id)
    return {"decay": decay, "scores": ml.compute_momentum(rows, decay=decay)}


@app.get("/artist/{artist_id}/prediction")
async def prediction(artist_id: str, decay: float = Query(0.4, ge=0.05, le=1.0)):
    """Predict next-period popularity using RandomForest + SHAP explanations.
    Returns only the top predicted track with album art."""
    rows = database.get_history(artist_id)
    predictions = ml.predict_next_period(rows, decay=decay)
    if not predictions:
        return {"next_hit": None}
    top = predictions[0]
    top["image"] = await lastfm.get_track_image(artist_id, top["name"])
    return {"next_hit": top}


@app.post("/snapshot/{artist_id}")
async def snapshot(artist_id: str):
    """Manually capture a snapshot."""
    tracks = await lastfm.get_top_tracks(artist_id)
    written = database.save_snapshot(artist_id, tracks)
    return {"written": written}

