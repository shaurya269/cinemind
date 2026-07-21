import { useState } from "react";
import { Link } from "react-router-dom";
import { parseGenres } from "../api";
import { useWatchlist } from "../hooks/useWatchlist";
import MovieModal from "../components/MovieModal";

export default function Watchlist() {
  const { movies, remove } = useWatchlist();
  const [active, setActive] = useState(null);

  return (
    <section>
      <h2>Your watchlist</h2>
      <p className="muted">
        Saved locally in this browser &mdash; click the star on any recommendation card to add or
        remove a title.
      </p>

      {movies.length === 0 ? (
        <div className="empty-state">
          <p>Nothing saved yet.</p>
          <Link className="btn btn-primary" to="/app">
            Find something to watch
          </Link>
        </div>
      ) : (
        <div className="watchlist-grid">
          {movies.map((movie) => {
            const genres = parseGenres(movie.genres);
            return (
              <article key={movie.movie_id} className="watchlist-row">
                <div className="rec-poster">
                  {movie.poster_url ? (
                    <img src={movie.poster_url} alt={`${movie.title} poster`} loading="lazy" />
                  ) : (
                    <div className="rec-poster-placeholder">No poster</div>
                  )}
                </div>
                <div className="watchlist-row-content" onClick={() => setActive(movie)} role="button" tabIndex={0}>
                  <h3>{movie.title}</h3>
                  {genres.length > 0 && (
                    <ul className="genre-chips">
                      {genres.slice(0, 4).map((g) => (
                        <li key={g}>{g}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <button
                  className="btn btn-ghost"
                  onClick={() => remove(movie.movie_id)}
                  aria-label={`Remove ${movie.title} from watchlist`}
                >
                  Remove
                </button>
              </article>
            );
          })}
        </div>
      )}

      {active && <MovieModal movie={active} onClose={() => setActive(null)} />}
    </section>
  );
}
