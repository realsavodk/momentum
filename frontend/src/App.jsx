import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "./api";
import ArtistHeader from "./components/ArtistHeader";
import MetricsRow from "./components/MetricsRow";
import MonthlyChart from "./components/MonthlyChart";
import SongDistribution from "./components/SongDistribution";
import PredictionScores from "./components/PredictionScores";
import LoadingSkeleton from "./components/LoadingSkeleton";

export default function App() {
  const searchRef = useRef(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [artist, setArtist] = useState(null);
  const [topTracks, setTopTracks] = useState([]);
  const [history, setHistory] = useState(null);
  const [momentum, setMomentum] = useState([]);
  const [predictions, setPredictions] = useState(null);
  const [decay, setDecay] = useState(0.4);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Live search — fires 300 ms after the user stops typing
  useEffect(() => {
    if (query.trim().length < 2) { setResults([]); return; }
    const t = setTimeout(async () => {
      try { setResults(await api.searchArtists(query)); }
      catch (e) { setError(e.message); }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  async function selectArtist(id) {
    setSelected(id);
    setResults([]);
    setError("");
    setLoading(true);
    try {
      const { artist, top_tracks } = await api.getArtist(id);
      setArtist(artist);
      setTopTracks(top_tracks);
      setHistory(await api.getHistory(id));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const loadMomentum = useCallback(async () => {
    if (!selected) return;
    try {
      const { scores } = await api.getMomentum(selected, decay);
      setMomentum(scores);
    } catch (e) {
      setError(e.message);
    }
  }, [selected, decay]);

  const loadPredictions = useCallback(async () => {
    if (!selected) return;
    try {
      const { next_hit } = await api.getPredictions(selected, decay);
      setPredictions(next_hit);
    } catch { /* best-effort */ }
  }, [selected, decay]);

  useEffect(() => { loadMomentum(); }, [loadMomentum]);
  useEffect(() => { loadPredictions(); }, [loadPredictions]);


  return (
    <>
      {/* ── Hero ── */}
      <section className="hero">
        <p className="hero-eyebrow">Artist Analytics</p>
        <h1 className="hero-title">Momentum</h1>
        <p className="hero-sub">
          See which artists are rising — before everyone else.
        </p>
        <button
          className="hero-cta"
          onClick={() => searchRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
        >
          Search an artist
        </button>
        <div className="scroll-hint" />
      </section>

      {/* ── Search ── */}
      <section className="search-section" ref={searchRef}>
        <div className="search-section-inner">
          <p className="search-label">Find an artist</p>
          <div className="search-wrap">
            <input
              value={query}
              placeholder="Start typing a name…"
              onChange={(e) => { setQuery(e.target.value); setError(""); }}
              onBlur={() => setTimeout(() => setResults([]), 150)}
            />
            {results.length > 0 && (
              <div className="search-results">
                {results.map((r) => (
                  <div key={r.id} className="search-result" onClick={() => selectArtist(r.id)}>
                    {r.image
                      ? <img src={r.image} alt={r.name} />
                      : <div className="search-result-avatar">{r.name[0]}</div>
                    }
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 15 }}>{r.name}</div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {r.followers?.toLocaleString()} listeners
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {error && <p className="error" style={{ marginTop: 12, textAlign: "center" }}>{error}</p>}
        </div>
      </section>

      {loading && <LoadingSkeleton />}

      {/* ── Dashboard ── */}
      {artist && !loading && (
        <div className="app">
          <ArtistHeader artist={artist} />
          <MetricsRow artist={artist} topTracks={topTracks} momentum={momentum} />
          <MonthlyChart history={history} />
          <div className="grid-2">
            <SongDistribution topTracks={topTracks} />
            <PredictionScores
              scores={momentum}
              decay={decay}
              onDecayChange={setDecay}
              predictions={predictions}
            />
          </div>
        </div>
      )}
    </>
  );
}
