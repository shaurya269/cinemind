import { useState } from "react";
import { getGraphInsights } from "../api";

export default function GraphInsights({ movieId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);

  async function handleToggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (data || loading) return;
    setLoading(true);
    setError(null);
    try {
      setData(await getGraphInsights(movieId, 3));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button className="btn btn-ghost" onClick={handleToggle}>
        {open ? "Hide graph insights" : "Graph insights"}
      </button>
      {open && (
        <div className="explain-body">
          {loading && <span className="muted">Querying the graph...</span>}
          {error && <span className="error-text">{error}</span>}
          {data && (
            <div className="graph-insights">
              <p>
                <strong>{data.total_raters}</strong> users rated this movie in
                the graph.
              </p>
              {data.also_liked_by_raters.length > 0 && (
                <p>
                  Also liked by the same raters:{" "}
                  {data.also_liked_by_raters.map((m) => m.title).join(", ")}
                </p>
              )}
              {data.shared_genre_movies.length > 0 && (
                <p>
                  Shares the most genres with:{" "}
                  {data.shared_genre_movies.map((m) => m.title).join(", ")}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}
