import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "cinemind:watchlist";

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

// Simple event bus so every component using this hook stays in sync without
// prop-drilling a shared store through App -- watchlist is opened from
// Home/Search/Profile cards as well as its own nav page.
const listeners = new Set();

function broadcast(movies) {
  listeners.forEach((fn) => fn(movies));
}

export function useWatchlist() {
  const [movies, setMovies] = useState(load);

  useEffect(() => {
    listeners.add(setMovies);
    return () => listeners.delete(setMovies);
  }, []);

  const persist = useCallback((next) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    broadcast(next);
  }, []);

  const isSaved = useCallback((movieId) => movies.some((m) => m.movie_id === movieId), [movies]);

  const toggle = useCallback(
    (movie) => {
      const exists = movies.some((m) => m.movie_id === movie.movie_id);
      const next = exists
        ? movies.filter((m) => m.movie_id !== movie.movie_id)
        : [{ ...movie, savedAt: Date.now() }, ...movies];
      setMovies(next);
      persist(next);
    },
    [movies, persist]
  );

  const remove = useCallback(
    (movieId) => {
      const next = movies.filter((m) => m.movie_id !== movieId);
      setMovies(next);
      persist(next);
    },
    [movies, persist]
  );

  return { movies, isSaved, toggle, remove };
}
