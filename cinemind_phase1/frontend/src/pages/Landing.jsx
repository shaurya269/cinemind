import { Link } from "react-router-dom";

const STEPS = [
  {
    n: "01",
    title: "Retrieve",
    body: "Content embeddings (E5) narrow the full catalogue down to ~30 relevant candidates by cosine similarity — instant, no LLM needed yet.",
  },
  {
    n: "02",
    title: "Rank",
    body: "A two-tower neural network trained on implicit feedback scores each candidate, blended with a log-popularity prior. Cached in Redis for 5 minutes.",
  },
  {
    n: "03",
    title: "Reason",
    body: "Claude (or Groq/Llama) re-ranks the shortlist, writes a grounded “Why this?” explanation, and drives onboarding chat for brand-new users.",
  },
  {
    n: "04",
    title: "Connect",
    body: "A Neo4j graph of real rating behaviour surfaces what similar raters also liked — a genuinely different signal from either vector store.",
  },
];

const STATS = [
  { value: "+55%", label: "precision@10 vs. popularity baseline" },
  { value: "+83%", label: "recall@10 vs. popularity baseline" },
  { value: "943", label: "users in MovieLens 100K" },
  { value: "1,682", label: "movies, ~1,548 enriched via OMDb" },
];

export default function Landing() {
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Personalised &middot; Explainable &middot; Conversational</span>
          <h1 className="hero-title">
            Movie recommendations
            <br />
            that show their work.
          </h1>
          <p className="hero-sub">
            CineMind pairs a two-tower deep learning model with an LLM reasoning layer to
            recommend films, explain why, and hold a real conversation about what you want to
            watch next &mdash; grounded in real metadata, never a hallucinated title.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary btn-lg" to="/app">
              Get recommendations
            </Link>
            <Link className="btn btn-ghost btn-lg" to="/search">
              Try conversational search
            </Link>
          </div>
        </div>
        <div className="hero-reel" aria-hidden="true">
          <div className="reel-strip">
            {["🎬", "🍿", "🎞", "🎭", "📽", "🎬", "🍿", "🎞"].map((e, i) => (
              <span key={i}>{e}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="stat-row">
        {STATS.map((s) => (
          <div className="stat-tile" key={s.label}>
            <div className="stat-value mono">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </section>

      <section className="how-it-works">
        <h2>How a recommendation gets made</h2>
        <div className="step-grid">
          {STEPS.map((s) => (
            <div className="step-card" key={s.n}>
              <span className="step-num mono">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Three ways in</h2>
          <p className="muted">Pick whichever matches where you are.</p>
        </div>
        <div className="cta-cards">
          <Link className="cta-card" to="/app">
            <h3>Returning user</h3>
            <p>Have a MovieLens user ID? Get hybrid two-tower recommendations instantly.</p>
          </Link>
          <Link className="cta-card" to="/search">
            <h3>Conversational search</h3>
            <p>Describe a mood or genre in plain language and let the LLM find real matches.</p>
          </Link>
          <Link className="cta-card" to="/profile">
            <h3>New here?</h3>
            <p>No rating history yet — describe your taste and get seed recommendations.</p>
          </Link>
        </div>
      </section>
    </div>
  );
}
