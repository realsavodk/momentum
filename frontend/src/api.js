// Thin wrapper around the backend API. All network calls live here so components stay
// focused on rendering.

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

async function post(path) {
  const res = await fetch(`${BASE}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  searchArtists: (q) => get(`/search?q=${encodeURIComponent(q)}`),
  getArtist: (id) => get(`/artist/${id}`),
  getHistory: (id) => get(`/artist/${id}/history`),
  getMomentum: (id, decay) => get(`/artist/${id}/momentum?decay=${decay}`),
  getPredictions: (id, decay) => get(`/artist/${id}/prediction?decay=${decay}`),
  snapshot: (id) => post(`/snapshot/${id}`),
};
