# Spotify Momentum — Artist Analytics & Song Prediction

A full-stack dashboard that tracks a Spotify artist's track popularity over time and
uses an exponential time-decay model to score which songs have the most "momentum" —
i.e. which are trending now and likely to predict the artist's next direction.

**Stack:** React (Vite) frontend · FastAPI (Python) backend · SQLite for snapshots ·
Spotify Web API for data.

> New here? Read `CONTEXT.md` next. It explains the architecture, the ML model, and
> exactly what is done vs. what is left to build. If you're continuing this project with
> Claude Code in VS Code, your first message should be:
> *"Read README.md and CONTEXT.md to understand this project, then let's continue."*

---

## Why popularity score, not raw streams

Spotify's public Web API does **not** expose raw monthly stream counts per song. It does
expose a `popularity` score (0–100) per track, which is a strong proxy for relative
listening activity. This project **takes a snapshot of those scores on a schedule** and
builds the time-series itself. That stored history is what powers the trend chart and the
momentum model. See `CONTEXT.md` for the full reasoning.

---

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- A free Spotify developer app (instructions below)

## 1. Get Spotify API credentials (free)

1. Go to https://developer.spotify.com/dashboard and log in.
2. Click **Create app**. Name it anything (e.g. "Momentum").
3. Set the **Redirect URI** to: `http://localhost:8000/callback`
4. Save. Copy the **Client ID** and **Client Secret**.

## 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then paste your Client ID + Secret into .env
uvicorn main:app --reload --port 8000
```

Backend runs at http://localhost:8000 — interactive API docs at http://localhost:8000/docs

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env              # default points at localhost:8000, usually fine
npm run dev
```

Frontend runs at http://localhost:5173

## 4. Try it

Open http://localhost:5173, search an artist, and the dashboard loads. The first time you
view an artist there's only one snapshot, so the trend chart is a single point — run the
snapshot a few times (or wait for the scheduled job) to build history. See `CONTEXT.md`
→ "Seeding demo data" for a shortcut that backfills fake history so you can demo it
immediately.

---

## Project layout

```
spotify-momentum/
├── README.md            ← you are here (setup)
├── CONTEXT.md           ← architecture, ML model, to-do list (READ THIS)
├── backend/
│   ├── main.py          ← FastAPI app + routes
│   ├── spotify.py       ← Spotify OAuth + API client
│   ├── ml.py            ← momentum scoring (time-decay model)
│   ├── database.py      ← SQLite snapshot storage
│   ├── config.py        ← settings loaded from .env
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── api.js               ← calls the backend
        └── components/
            ├── ArtistHeader.jsx
            ├── MetricsRow.jsx
            ├── MonthlyChart.jsx       ← bar chart, top song highlighted
            ├── SongDistribution.jsx   ← donut
            └── PredictionScores.jsx   ← momentum list + decay slider
```
