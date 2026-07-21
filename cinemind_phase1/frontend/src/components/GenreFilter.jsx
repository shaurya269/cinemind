import { useMemo } from "react";
import { parseGenres } from "../api";

export default function GenreFilter({ movies, active, onChange }) {
  const genres = useMemo(() => {
    const set = new Set();
    movies?.forEach((m) => parseGenres(m.genres).forEach((g) => set.add(g)));
    return [...set].sort();
  }, [movies]);

  if (genres.length === 0) return null;

  return (
    <div className="genre-filter" role="group" aria-label="Filter by genre">
      <button
        className={`filter-chip ${active === null ? "filter-chip-active" : ""}`}
        onClick={() => onChange(null)}
      >
        All
      </button>
      {genres.map((g) => (
        <button
          key={g}
          className={`filter-chip ${active === g ? "filter-chip-active" : ""}`}
          onClick={() => onChange(g === active ? null : g)}
        >
          {g}
        </button>
      ))}
    </div>
  );
}
