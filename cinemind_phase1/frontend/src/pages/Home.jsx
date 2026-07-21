import { useState } from "react";
import { Link } from "react-router-dom";
import { getRecommendations } from "../api";
import RecommendationCard from "../components/RecommendationCard";

export default function Home() {
  const [userId, setUserId] = useState(196);
  const [count, setCount] = useState(10);
  const [recs, setRecs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleRecommend(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setRecs(null);
    try {
      const res = await getRecommendations(userId, count);
      setRecs(res.recommendations);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h2>Returning user</h2>
      <p className="muted">
        Hybrid two-tower + popularity-prior recommendations for a user with
        existing rating history. New here? Try{" "}
        <Link to="/profile">the onboarding flow</Link> instead.
      </p>

      <form className="search-form" onSubmit={handleRecommend}>
        <label htmlFor="user-id">User ID</label>
        <input
          id="user-id"
          type="number"
          min={1}
          max={943}
          value={userId}
          onChange={(e) => setUserId(Number(e.target.value))}
        />
        <label htmlFor="count">Recommendations</label>
        <input
          id="count"
          type="number"
          min={5}
          max={20}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
        />
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Loading..." : "Recommend"}
        </button>
      </form>

      {error && (
        <p className="error-text">
          {error} -- try a different user ID, or use the onboarding flow for a
          new user.
        </p>
      )}

      <div className="rec-grid">
        {recs?.map((movie) => (
          <RecommendationCard key={movie.movie_id} movie={movie} userId={userId} />
        ))}
      </div>
    </section>
  );
}
