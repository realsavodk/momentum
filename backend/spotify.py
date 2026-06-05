"""Spotify client — used only for artist images.

All music data (tracks, popularity, search) comes from Last.fm.
Spotify's artist search reliably returns high-quality artist photos.
"""
import base64
import time
from typing import Optional
import httpx

from config import settings

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

_token_cache: Optional[tuple] = None


async def _get_token() -> Optional[str]:
    global _token_cache
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        return None
    if _token_cache and _token_cache[1] > time.time() + 30:
        return _token_cache[0]
    creds = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    auth = base64.b64encode(creds.encode()).decode()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                headers={"Authorization": f"Basic {auth}"},
                data={"grant_type": "client_credentials"},
            )
            resp.raise_for_status()
            data = resp.json()
        _token_cache = (data["access_token"], time.time() + data["expires_in"])
        return _token_cache[0]
    except Exception:
        return None


async def get_artist_image(artist_name: str) -> Optional[str]:
    """Search Spotify for an artist and return their image URL."""
    token = await _get_token()
    if not token:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": artist_name, "type": "artist", "limit": 1},
            )
            resp.raise_for_status()
            items = resp.json().get("artists", {}).get("items", [])
        if items and items[0].get("images"):
            return items[0]["images"][0]["url"]
    except Exception:
        pass
    return None


async def get_track_image(artist_name: str, track_name: str) -> Optional[str]:
    """Search Spotify for a track and return its album cover URL.

    Spotify requires cover art for every release, so this works for obscure
    artists where iTunes search fails. Falls back to a plain-text query if
    the structured field search returns nothing.
    """
    token = await _get_token()
    if not token:
        return None
    try:
        async with httpx.AsyncClient() as client:
            # structured query is more precise
            resp = await client.get(
                f"{API_BASE}/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": f"track:{track_name} artist:{artist_name}", "type": "track", "limit": 1},
            )
            resp.raise_for_status()
            items = resp.json().get("tracks", {}).get("items", [])
            if not items:
                # plain-text fallback for unusual spellings / features
                resp = await client.get(
                    f"{API_BASE}/search",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"q": f"{track_name} {artist_name}", "type": "track", "limit": 1},
                )
                resp.raise_for_status()
                items = resp.json().get("tracks", {}).get("items", [])
        if items:
            images = items[0].get("album", {}).get("images", [])
            if images:
                return images[0]["url"]
    except Exception:
        pass
    return None
