import { useEffect } from "react";
import { createPortal } from "react-dom";
import { parseGenres } from "../api";
import { useWatchlist } from "../hooks/useWatchlist";

export default function MovieModal({ movie, onClose }) {
  const { isSaved, toggle } = useWatchlist();

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  if (!movie) return null;
  const genres = parseGenres(movie.genres);
  const saved = isSaved(movie.movie_id);

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-shell"
        role="dialog"
        aria-modal="true"
        aria-label={movie.title}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" onClick={onClose} aria-label="Close">
          &times;
        </button>

        <div className="modal-body">
          <div className="modal-poster">
            {movie.poster_url ? (
              <img src={movie.poster_url} alt={`${movie.title} poster`} />
            ) : (
              <div className="rec-poster-placeholder modal-poster-placeholder">No poster</div>
            )}
          </div>

          <div className="modal-content">
            <h2>{movie.title}</h2>

            <div className="modal-meta-row">
              {movie.score != null && (
                <span className="mono rec-score" title="Model similarity score">
                  score {movie.score.toFixed(3)}
                </span>
              )}
              {genres.length > 0 && (
                <ul className="genre-chips">
                  {genres.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              )}
            </div>

            {movie.overview && <p className="modal-overview">{movie.overview}</p>}
            {movie.cast && (
              <p className="rec-cast">
                <span className="rec-cast-label">Cast</span> {movie.cast}
              </p>
            )}
            {movie.why && (
              <div className="modal-why">
                <span className="rec-cast-label">Why this?</span>
                <p>{movie.why}</p>
              </div>
            )}

            <button
              className={`btn ${saved ? "btn-primary" : "btn-ghost"} modal-watchlist-btn`}
              onClick={() => toggle(movie)}
            >
              {saved ? "In your watchlist" : "Add to watchlist"}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
