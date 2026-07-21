import { useState } from "react";
import { explainMovie } from "../api";

export default function ExplainPanel({ movieId, query }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);

  async function handleToggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (explanation || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await explainMovie(movieId, query);
      setExplanation(res.explanation);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button className="btn btn-ghost" onClick={handleToggle}>
        {open ? "Hide explanation" : "Why this?"}
      </button>
      {open && (
        <div className="explain-body">
          {loading && <span className="muted">Thinking...</span>}
          {error && <span className="error-text">{error}</span>}
          {explanation && <p>{explanation}</p>}
        </div>
      )}
    </>
  );
}
