# CONTEXT — read this before continuing the build

This file is the handoff document. It captures the design decisions so a fresh Claude
(or you, in two weeks) can pick up the thread without re-deriving everything.

## What this project is

A dashboard for a single Spotify artist that shows:
1. **Artist header** — name, genre, follower count, popularity.
2. **Metrics row** — monthly listeners, top song this month, predicted next hit.
3. **Monthly volume chart** — popularity-weighted activity per month, each bar colored
   by the top song that month.
4. **Song distribution donut** — share of activity across the artist's top tracks.
5. **Momentum scores** — the ML layer. Ranks songs by a time-decayed score and shows a
   slider to tune how aggressively recent data is weighted.

## The core data problem (important)

Spotify's Web API does **not** return raw monthly stream counts per track for normal
(non-partner) apps. What it *does* return per track is a `popularity` field, 0–100,
roughly reflecting recent listening relative to the catalog.

So this project does **not** read a stream time-series from Spotify. It **builds** one:
- A scheduled job calls Spotify, reads each top track's `popularity`, and writes a row to
  the `snapshots` table with a timestamp.
- Over days/weeks this accumulates into a real time-series.
- The charts and ML model run on that stored history, not on live Spotify data.

This is why `database.py` exists and why the trend chart is empty on first run. It's also
a genuinely nice talking point for the resume / interview: *you* designed the data
collection, not just consumed an endpoint.

## The ML model (`ml.py`)

The momentum score uses **exponential time-decay weighting**. For each song, every
historical snapshot contributes to the score, but older snapshots are discounted:

```
weight(age) = exp(-λ · age)
score       = Σ (popularity_t · weight_t) / Σ weight_t
```

where `age` is how many periods ago the snapshot was (0 = most recent) and `λ` (lambda)
is the decay rate. Higher λ → only very recent data matters. Lower λ → history stays
relevant. The frontend slider sends λ to the backend so the user can explore this live.

The score is then normalized to 0–100 against the top-scoring song. A song that has been
climbing recently outranks one that was huge months ago but is fading — which is the
"recently popping songs score higher" behavior you asked for.

**Where to take it next** (currently stubbed / noted in `ml.py`):
- Pull Spotify **audio features** (tempo, energy, danceability, valence) per track.
- Train a small scikit-learn model on the decayed history to predict next-period
  popularity, and/or cluster tracks to find which existing song a future release is
  "most similar" to. The decay-weighted score is a clean feature to feed that model.
- This is where your banking-ML toolkit (XGBoost/LightGBM, SHAP for explainability)
  transfers directly — momentum scoring is structurally the same as the recency-weighted
  features you'd build for fraud/credit models.

## Architecture / data flow

```
Spotify Web API
      │  (OAuth client-credentials for public data)
      ▼
backend/spotify.py  ──reads popularity, audio features──┐
      │                                                  │
      ▼                                                  ▼
backend/database.py  ◄── scheduled snapshot ──►  backend/ml.py (decay scoring)
      │                                                  │
      └──────────────► backend/main.py (FastAPI) ◄───────┘
                              │  JSON
                              ▼
                  frontend/src/api.js → React components
```

## Auth note

For reading **public** artist/track data you only need the **client-credentials** flow
(app token, no user login) — that's what `spotify.py` implements and is enough for the
whole dashboard. The redirect-URI / user-login (authorization-code) flow is only needed
if you later want per-user data like someone's own playlists. Stick with
client-credentials unless you add user features.

## Status: done vs. to-do

**Done (scaffolded, working skeleton):**
- [x] FastAPI app with routes: `/search`, `/artist/{id}`, `/artist/{id}/momentum`, `/snapshot/{id}`
- [x] Spotify client-credentials auth + top-tracks fetch (`spotify.py`)
- [x] SQLite snapshot storage with schema (`database.py`)
- [x] Time-decay momentum model (`ml.py`)
- [x] React dashboard with all five UI sections wired to the API
- [x] Decay-rate slider that re-queries momentum live

**To-do (your build work):**
- [ ] Run a real Spotify app and confirm credentials load (`.env`)
- [ ] Add a scheduler (APScheduler) so snapshots run automatically, not just on demand
- [ ] Add audio-features fetch + the scikit-learn prediction model (see `ml.py` TODOs)
- [ ] Group snapshots into proper monthly buckets (currently grouped by snapshot order)
- [ ] Error/loading states polish in the frontend
- [ ] Deploy: frontend → Vercel, backend → Render (both free tiers)
- [ ] Write tests for `ml.py` (the scoring math is the most testable, resume-worthy part)

## Seeding demo data

So you can demo without waiting days for snapshots to accumulate, `database.py` has a
`seed_demo_snapshots(artist_id)` helper that backfills several months of synthetic
popularity history. Call it once from a Python shell or add a temporary `/seed/{id}`
route. Remove before deploying.
