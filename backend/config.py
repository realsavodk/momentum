"""Configuration loaded from environment / .env file."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    LASTFM_API_KEY: str = os.getenv("LASTFM_API_KEY", "")
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "snapshots.db")
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",")


settings = Settings()
