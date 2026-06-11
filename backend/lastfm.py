"""Last.fm API client.

Uses the public REST API with an API key (no OAuth needed for read-only data).
Docs: https://www.last.fm/api

Artist images come from Spotify (via spotify.get_artist_image) since Last.fm
deprecated their hosted images in 2019.
"""
import asyncio
import hashlib
import httpx

from config import settings
from spotify import get_artist_image, get_track_image

API_BASE = "https://ws.audioscrobbler.com/2.0/"


async def _get(method: str, params: dict) -> dict:
    all_params = {
        "method": method,
        "api_key": settings.LASTFM_API_KEY,
        "format": "json",
        **params,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(API_BASE, params=all_params)
        resp.raise_for_status()
        data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Last.fm error {data['error']}: {data.get('message')}")
    return data



def _track_id(artist: str, track: str) -> str:
    """Stable ID from artist+track since Last.fm doesn't always provide mbid."""
    return hashlib.md5(f"{artist.lower()}::{track.lower()}".encode()).hexdigest()


async def search_artists(query: str, limit: int = 8) -> list[dict]:
    data = await _get("artist.search", {"artist": query, "limit": limit})
    items = data.get("results", {}).get("artistmatches", {}).get("artist", [])

    valid = [a for a in items if isinstance(a, dict)]
    images = await asyncio.gather(*[get_artist_image(a["name"]) for a in valid])
    return [
        {
            "id": a["name"],
            "name": a["name"],
            "genres": [],
            "followers": int(a.get("listeners", 0)),
            "popularity": min(100, int(int(a.get("listeners", 0)) / 10000)),
            "image": image,
        }
        for a, image in zip(valid, images)
    ]


async def get_artist(artist_name: str) -> dict:
    data = await _get("artist.getinfo", {"artist": artist_name})
    a = data["artist"]
    tags = [t["name"] for t in a.get("tags", {}).get("tag", [])]
    listeners = int(a.get("stats", {}).get("listeners", 0))
    image = await get_artist_image(artist_name)
    return {
        "id": artist_name,
        "name": a["name"],
        "genres": tags,
        "followers": listeners,
        "popularity": min(100, listeners // 10000),
        "image": image,
    }



async def get_top_tracks(artist_name: str, limit: int = 10) -> list[dict]:
    data = await _get("artist.gettoptracks", {"artist": artist_name, "limit": limit})
    tracks = data.get("toptracks", {}).get("track", [])
    counts = [int(t.get("playcount", 0)) for t in tracks]
    max_count = max(counts, default=1) or 1
    return [
        {
            "id": t.get("mbid") or _track_id(artist_name, t["name"]),
            "name": t["name"],
            "popularity": round(int(t.get("playcount", 0)) / max_count * 100),
            "playcount": int(t.get("playcount", 0)),
            "album": None,
            "image": None,
        }
        for t in tracks
        if isinstance(t, dict)
    ]
