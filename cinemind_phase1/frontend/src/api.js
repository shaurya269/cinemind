// Thin fetch wrapper around the Phase 2 FastAPI routes. This is the ONLY
// place the frontend talks to the backend -- no direct Qdrant/Postgres/Redis
// access, matching the Phase 3 design (CLAUDE.md / System Architecture).
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const checkHealth = () => request("/health");

export const getRecommendations = (userId, k = 10) =>
  request(`/recommendations/${userId}?k=${k}`);

export const chat = (query) =>
  request("/chat", { method: "POST", body: JSON.stringify({ query }) });

export const onboard = (answers) =>
  request("/onboarding", { method: "POST", body: JSON.stringify({ answers }) });

export const explainMovie = (movieId, query = "this recommendation") =>
  request(`/explain/${movieId}?query=${encodeURIComponent(query)}`);

export const sendFeedback = (userId, movieId, { rating, clicked } = {}) =>
  request("/feedback", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, movie_id: movieId, rating, clicked }),
  });

// items.csv stores genres as a Python list repr, e.g. "['Drama', 'Romance']".
// Parse it into a real JS array for rendering as chips.
export function parseGenres(genresStr) {
  if (!genresStr) return [];
  const matches = genresStr.match(/'([^']*)'|"([^"]*)"/g);
  if (!matches) return [];
  return matches.map((m) => m.slice(1, -1));
}
