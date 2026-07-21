import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getRecommendations, parseGenres } from "../api";
import RecommendationCard from "../components/RecommendationCard";
import GenreFilter from "../components/GenreFilter";
import { SkeletonGrid } from "../components/SkeletonCard";

export default function Home() {
  const [userId, setUserId] = useState(196);
  const [count, setCount] = useState(10);
  const [recs, setRecs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [genre, setGenre] = useState(null);

  async function handleRecommend(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setRecs(null);
    setGenre(null);
    try {
      const res = await getRecommendations(userId, count);
      setRecs(res.recommendations);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    if (!recs || !genre) return recs;
    return recs.filter((m) => parseGenres(m.genres).includes(genre));
  }, [recs, genre]);

  return (
    <section>
      <h2>Returning user</h2>
      <p className="muted">
        Hybrid two-tower + popularity-prior recommendations for a user with
        existing rating history. New here? Try{" "}
        <Link to="/profile">the onboarding flow</Link> instead.
      </p>

      <form className="search-form" onSubmit={handleRecommend}>
        <div className="field">
          <label htmlFor="user-id">User ID</label>
          <input
            id="user-id"
            type="number"
            min={1}
            max={943}
            value={userId}
            onChange={(e) => setUserId(Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="count">Recommendations</label>
          <input
            id="count"
            type="number"
            min={5}
            max={20}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Loading…" : "Recommend"}
        </button>
      </form>

      {error && (
        <p className="error-text">
          {error} &mdash; try a different user ID, or use the onboarding flow for a
          new user.
        </p>
      )}

      {loading && <SkeletonGrid />}

      {recs && recs.length > 0 && (
        <>
          <GenreFilter movies={recs} active={genre} onChange={setGenre} />
          <div className="rec-grid">
            {filtered.map((movie) => (
              <RecommendationCard key={movie.movie_id} movie={movie} userId={userId} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
