"""SQLite storage for popularity snapshots.

Each row records one track's popularity at one point in time. Over many snapshots this
builds the time-series the charts and ML model consume.

Schema (table `snapshots`):
    artist_id   TEXT    Spotify artist id
    track_id    TEXT    Spotify track id
    track_name  TEXT    denormalized for convenience
    popularity  INTEGER 0-100 normalised score
    playcount   INTEGER raw cumulative scrobble count from Last.fm
    captured_at TEXT    ISO timestamp
"""
import sqlite3
from datetime import datetime, timedelta, timezone

from config import settings


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id   TEXT    NOT NULL,
                track_id    TEXT    NOT NULL,
                track_name  TEXT    NOT NULL,
                popularity  INTEGER NOT NULL,
                playcount   INTEGER NOT NULL DEFAULT 0,
                captured_at TEXT    NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artist ON snapshots(artist_id, captured_at)"
        )
        # migrate existing DBs that predate the playcount column
        try:
            conn.execute("ALTER TABLE snapshots ADD COLUMN playcount INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass


def save_snapshot(artist_id: str, tracks: list[dict]) -> int:
    """Persist one snapshot of an artist's top tracks. Returns rows written."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.executemany(
            "INSERT INTO snapshots (artist_id, track_id, track_name, popularity, playcount, captured_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(artist_id, t["id"], t["name"], t["popularity"], t.get("playcount", 0), now) for t in tracks],
        )
    return len(tracks)


def has_history(artist_id: str) -> bool:
    """Return True if the artist already has any snapshots."""
    with _conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM snapshots WHERE artist_id = ?", (artist_id,)
        ).fetchone()[0]
    return count > 0


def get_tracked_artists() -> list[str]:
    """All distinct artist IDs that have at least one snapshot."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT artist_id FROM snapshots"
        ).fetchall()
    return [r["artist_id"] for r in rows]


def get_history(artist_id: str) -> list[dict]:
    """All snapshot rows for an artist, oldest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT track_id, track_name, popularity, playcount, captured_at"
            " FROM snapshots WHERE artist_id = ? ORDER BY captured_at ASC",
            (artist_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def seed_demo_snapshots(artist_id: str, tracks: list[dict], months: int = 6) -> None:
    """Backfill synthetic monthly history so you can demo without waiting.

    Creates a rising/falling popularity trajectory per track. REMOVE before deploying.
    """
    import random

    base = datetime.now(timezone.utc)
    with _conn() as conn:
        for i, t in enumerate(tracks):
            # base cumulative count proportional to popularity; grows each month
            base_count = int(t["popularity"] * 60000) + random.randint(10000, 200000)
            monthly_growth = int(base_count * 0.04) + random.randint(5000, 30000)
            for m in range(months):
                captured = (base - timedelta(days=30 * (months - m))).isoformat()
                trend = (i - len(tracks) / 2) * (m - months / 2) * 2
                pop = max(5, min(100, int(t["popularity"] + trend + random.randint(-4, 4))))
                play = base_count + monthly_growth * m + random.randint(-8000, 8000)
                conn.execute(
                    "INSERT INTO snapshots (artist_id, track_id, track_name, popularity, playcount, captured_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (artist_id, t["id"], t["name"], pop, play, captured),
                )
