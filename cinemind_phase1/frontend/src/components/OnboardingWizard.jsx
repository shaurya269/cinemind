import { useState } from "react";
import { onboard } from "../api";
import RecommendationCard from "./RecommendationCard";
import { SkeletonGrid } from "./SkeletonCard";

export default function OnboardingWizard() {
  const [answers, setAnswers] = useState(
    "I like clever thrillers, heartfelt sci-fi, and movies with strong characters."
  );
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await onboard(answers);
      setResults(res.seed_recommendations);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <p className="muted">
        No rating history yet? Describe what you like and we'll seed your
        first recommendations from content alone -- no collaborative history
        required.
      </p>
      <form className="search-form search-form-stacked" onSubmit={handleSubmit}>
        <div className="field field-grow">
          <label htmlFor="onboarding-answers">Taste notes</label>
          <textarea
            id="onboarding-answers"
            rows={4}
            value={answers}
            onChange={(e) => setAnswers(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Finding movies…" : "Find seed movies"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {loading && <SkeletonGrid />}

      <div className="rec-grid">
        {results?.map((movie) => (
          <RecommendationCard key={movie.movie_id} movie={movie} query={answers} />
        ))}
      </div>
    </section>
  );
}
