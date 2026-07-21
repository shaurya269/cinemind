import { useState } from "react";
import { chat } from "../api";
import RecommendationCard from "./RecommendationCard";

export default function ChatSearch() {
  const [query, setQuery] = useState("smart funny science fiction with some heart");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSearch(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await chat(query);
      setResults(res.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <form className="search-form" onSubmit={handleSearch}>
        <label htmlFor="chat-query">Search request</label>
        <input
          id="chat-query"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      <div className="rec-grid">
        {results?.map((movie) => (
          <RecommendationCard key={movie.movie_id} movie={movie} query={query} />
        ))}
      </div>
    </section>
  );
}
