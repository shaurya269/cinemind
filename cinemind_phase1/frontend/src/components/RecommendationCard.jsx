import { useState } from "react";
import { parseGenres, sendFeedback } from "../api";
import { useWatchlist } from "../hooks/useWatchlist";
import ExplainPanel from "./ExplainPanel";
import GraphInsights from "./GraphInsights";
import MovieModal from "./MovieModal";

export default function RecommendationCard({ movie, query, userId, onFeedback }) {
  const genres = parseGenres(movie.genres);
  const [modalOpen, setModalOpen] = useState(false);
  const [feedbackState, setFeedbackState] = useState(null);
  const { isSaved, toggle } = useWatchlist();
  const saved = isSaved(movie.movie_id);

  async function handleFeedback(clicked) {
    if (!userId) return;
    try {
      await sendFeedback(userId, movie.movie_id, { clicked, rating: clicked ? 5 : undefined });
      setFeedbackState(clicked ? "liked" : "skipped");
      onFeedback?.(movie.movie_id, clicked);
    } catch {
      // Feedback is best-effort -- never block the browsing experience on it.
    }
  }

  return (
    <>
      <article className="rec-card">
        <button
          className="watchlist-toggle"
          onClick={() => toggle(movie)}
          aria-label={saved ? "Remove from watchlist" : "Add to watchlist"}
          title={saved ? "Remove from watchlist" : "Add to watchlist"}
        >
          {saved ? "★" : "☆"}
        </button>

        <div className="rec-card-body" onClick={() => setModalOpen(true)} role="button" tabIndex={0}>
          <div className="rec-poster">
            {movie.poster_url ? (
              <img src={movie.poster_url} alt={`${movie.title} poster`} loading="lazy" />
            ) : (
              <div className="rec-poster-placeholder">No poster</div>
            )}
          </div>

          <div className="rec-card-content">
            <header className="rec-card-head">
              <h3>{movie.title}</h3>
              {movie.score != null && (
                <span className="rec-score mono" title="Model similarity score">
                  {movie.score.toFixed(3)}
                </span>
              )}
            </header>

            {genres.length > 0 && (
              <ul className="genre-chips">
                {genres.slice(0, 4).map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            )}

            {movie.overview && <p className="rec-overview">{movie.overview}</p>}
            {movie.cast && (
              <p className="rec-cast">
                <span className="rec-cast-label">Cast</span> {movie.cast}
              </p>
            )}
            {movie.why && <p className="rec-why">{movie.why}</p>}
          </div>
        </div>

        <footer className="rec-card-actions">
          <ExplainPanel movieId={movie.movie_id} query={query} />
          <GraphInsights movieId={movie.movie_id} />
          {userId && (
            <span className="feedback-buttons">
              <button
                className={`btn btn-ghost ${feedbackState === "liked" ? "btn-feedback-active" : ""}`}
                onClick={() => handleFeedback(true)}
              >
                Liked
              </button>
              <button
                className={`btn btn-ghost ${feedbackState === "skipped" ? "btn-feedback-active" : ""}`}
                onClick={() => handleFeedback(false)}
              >
                Skip
              </button>
            </span>
          )}
        </footer>
      </article>

      {modalOpen && <MovieModal movie={movie} onClose={() => setModalOpen(false)} />}
    </>
  );
}
