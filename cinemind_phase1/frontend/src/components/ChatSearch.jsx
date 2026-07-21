import { useMemo, useState } from "react";
import { chat, parseGenres } from "../api";
import RecommendationCard from "./RecommendationCard";
import GenreFilter from "./GenreFilter";
import { SkeletonGrid } from "./SkeletonCard";

const SUGGESTIONS = [
  "smart funny science fiction with some heart",
  "slow-burn mystery I can watch with my parents",
  "underrated 90s action movies",
  "something uplifting after a hard week",
];

export default function ChatSearch() {
  const [query, setQuery] = useState(SUGGESTIONS[0]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [genre, setGenre] = useState(null);

  async function runSearch(q) {
    setLoading(true);
    setError(null);
    setGenre(null);
    try {
      const res = await chat(q);
      setResults(res.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e) {
    e.preventDefault();
    runSearch(query);
  }

  function handleSuggestion(s) {
    setQuery(s);
    runSearch(s);
  }

  const filtered = useMemo(() => {
    if (!results || !genre) return results;
    return results.filter((m) => parseGenres(m.genres).includes(genre));
  }, [results, genre]);

  return (
    <section>
      <form className="search-form" onSubmit={handleSearch}>
        <div className="field field-grow">
          <label htmlFor="chat-query">Search request</label>
          <input
            id="chat-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      <div className="suggestion-row">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="filter-chip" onClick={() => handleSuggestion(s)}>
            {s}
          </button>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}

      {loading && <SkeletonGrid />}

      {results && results.length > 0 && (
        <>
          <GenreFilter movies={results} active={genre} onChange={setGenre} />
          <div className="rec-grid">
            {filtered.map((movie) => (
              <RecommendationCard key={movie.movie_id} movie={movie} query={query} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
