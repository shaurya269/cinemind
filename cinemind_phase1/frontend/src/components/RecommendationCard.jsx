import { parseGenres, sendFeedback } from "../api";
import ExplainPanel from "./ExplainPanel";

export default function RecommendationCard({ movie, query, userId, onFeedback }) {
  const genres = parseGenres(movie.genres);

  async function handleFeedback(clicked) {
    if (!userId) return;
    try {
      await sendFeedback(userId, movie.movie_id, { clicked, rating: clicked ? 5 : undefined });
      onFeedback?.(movie.movie_id, clicked);
    } catch {
      // Feedback is best-effort -- never block the browsing experience on it.
    }
  }

  return (
    <article className="rec-card">
      <div className="rec-card-body">
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
              <span className="rec-score" title="Model similarity score">
                {movie.score.toFixed(3)}
              </span>
            )}
          </header>

          {genres.length > 0 && (
            <ul className="genre-chips">
              {genres.map((g) => (
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
        {userId && (
          <span className="feedback-buttons">
            <button className="btn btn-ghost" onClick={() => handleFeedback(true)}>
              Liked
            </button>
            <button className="btn btn-ghost" onClick={() => handleFeedback(false)}>
              Skip
            </button>
          </span>
        )}
      </footer>
    </article>
  );
}
