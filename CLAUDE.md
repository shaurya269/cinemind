# CineMind — Project Context for Claude Code

## Version control (standing authorization)
This repo is pushed to **github.com/shaurya269/cinemind** (public). The user
has explicitly pre-authorized autonomous `git commit` + `git push` under
these rules, so no need to ask permission each time -- this note is that
advance authorization:
- Commit after completing a meaningful unit of work (a feature, a fix, a
  doc/diagram sync) -- not after every tiny edit.
- Push after a completed task, or after a small batch of a few commits --
  don't push after literally every single commit if several are landing in
  quick succession as part of one continuous task.
- If genuinely unsure whether to push yet, it's fine to ask -- but proactively
  push (don't wait to be asked) whenever context/session limits might be
  approaching, so finished work is never left stranded uncommitted/unpushed.
- Standard safety rules still apply on top of this: never force-push, never
  push over history you didn't create locally, always check `git status`/diff
  for secrets before committing (`.env` is gitignored -- verify new secret-like
  files get the same treatment), and never commit `.env`, `node_modules/`,
  `data/`, `artifacts/`, or other gitignored paths even if `-A`-added by habit.

## Project Title
**CineMind: An LLM-Augmented Hybrid Deep Learning Framework for Personalised, Explainable, and Conversational Movie & Show Recommendation**

---

## What this project is (one paragraph)
CineMind is a full-stack movie and TV recommendation system that combines a PyTorch two-tower deep learning model (collaborative filtering) with an LLM reasoning layer (via Claude API + LangChain) to deliver personalised, explainable, and conversational recommendations. It solves three real business problems: real-time personalisation for returning users, cold-start resolution for new users via an onboarding chat, and transparent "Why this?" explanations. It is built as a portfolio project with a production-grade architecture and benchmarked against an RBM baseline from the reference repo.

---

## Reference repo
https://github.com/nshakhapur/Movie_Recommendation_DeepLearning
- Uses Restricted Boltzmann Machine (RBM) on MovieLens 100K
- We reproduce this as our baseline, then beat it with the two-tower model

---

## Tech Stack

| Layer | Tool / Library |
|---|---|
| Deep learning model | PyTorch (two-tower neural network) |
| Content embeddings | intfloat/e5-small-v2 (local, free — small chosen deliberately for laptop speed; see nested `cinemind_phase1/CLAUDE.md`) |
| Vector database | Qdrant (local Docker, verified live) |
| Graph database | Neo4j — built and verified (`src/08_neo4j_graph.py` loads the graph, `backend/graph.py` queries it, `GET /graph/insights/{movie_id}` exposes it, both UIs render it) |
| Cache | Redis — built and verified (`recommender.recommend_for_user` cache-aside, 5 min TTL; confirmed ~24x speedup on cache hit) |
| Relational DB | PostgreSQL (used for feedback storage; SQLite fallback when unreachable) |
| LLM API | Claude API (Haiku/Sonnet) **or** Groq (Llama 3.x, free tier) — provider auto-selected by whichever `ANTHROPIC_API_KEY`/`GROQ_API_KEY` is set, Anthropic preferred |
| LLM orchestration | LangChain (LCEL chains, PromptTemplates); retrieval is direct cosine search over content vectors, not a Qdrant-backed retriever object |
| Observability | Langfuse — built and verified (`backend/llm_chains.py`'s `_invoke_or_none` attaches a `CallbackHandler` to every chain call; a real trace was confirmed to land at cloud.langfuse.com via their public API) |
| Backend | FastAPI (plain JSON responses — no SSE streaming implemented) |
| Frontend | React (Vite), built and verified — see Phase 3 below |
| Public demo | Streamlit, built and verified locally — **not yet deployed** to Streamlit Community Cloud |
| Prototyping | Jupyter notebooks |
| Datasets | MovieLens 100K (`ml-100k`) + OMDb API for poster/plot/cast |

---

## Architecture (6 layers)

```
Layer 1: Data
  MovieLens 100K (ratings + item metadata)
  OMDb API (poster, plot, cast) -- matched by title+year, NOT a links.csv
    join (ml-100k ships no links.csv/tmdbId, unlike the newer 25M release).
    See src/07_omdb_enrichment.py. Multi-key rotation supported for the
    1,000/day free-tier quota. 1,548/1,682 movies matched so far.
  Stored in PostgreSQL (feedback only -- movie metadata lives in CSV/artifacts)

Layer 2: Embedding pipeline (offline, batch)
  Content embeddings:  e5-small-v2  on (title + genres)
  Collaborative:       Two-tower PyTorch model trained on implicit feedback (rating >= 4)
  Content vectors searched directly (cosine sim); collab vectors also indexed in Qdrant

Layer 3: Storage
  Qdrant   - vector search (collab vectors); content vectors searched via
             plain numpy/cosine in recommender.py, not stored in Qdrant
  Neo4j    - graph: (User)-[:RATED {rating,timestamp}]->(Movie)-[:HAS_GENRE]->(Genre).
             Loaded by src/08_neo4j_graph.py from the same ratings/items data
             as everything else (55,375 RATED edges, 2,893 HAS_GENRE edges on
             ml-100k). Queried by backend/graph.py for co-rater and
             shared-genre traversals -- a genuinely different signal than the
             vector stores (real other-user behaviour, not a similarity score).
  Redis    - cache-aside for GET /recommendations/{user_id} (5 min TTL,
             keyed on user_id+k). Numpy/no-cache fallback if unreachable.
  Postgres - feedback logs (SQLite fallback when Postgres isn't reachable)

Layer 4: Online pipeline (per request)
  Step 1: Candidate generation - cosine search over content vectors -> ~30 candidates
  Step 2: Ranking - two-tower dot product + 0.30 * log-popularity prior (hybrid scorer),
          Redis-cached per (user_id, k) for 5 minutes
  Step 3: LLM reasoning (LangChain), when ANTHROPIC_API_KEY or GROQ_API_KEY is set:
    a) Conversational query parsing (RAG)
    b) Re-ranking top ~30 -> final 10 (de-duplicated -- free-tier models can repeat ids)
    c) "Why this?" explanation generation (grounded in real metadata + plot when available)
    d) Cold-start onboarding chat (new users)
    Without a key, falls back to retrieval-only results (no crash).
    Every chain invocation traced to Langfuse when configured (see Layer 5).
  Step 4: Graph insights (GET /graph/insights/{movie_id}) -- co-raters and
          shared-genre movies via Neo4j traversal, independent of steps 1-3.

Layer 5: Backend (FastAPI) -- built and verified
  GET  /recommendations/{user_id}   (Redis-cached)
  POST /chat          (conversational search, Langfuse-traced)
  POST /onboarding    (cold-start dialogue, Langfuse-traced)
  POST /feedback      (clicks, ratings -> retraining)
  GET  /explain/{movie_id}          (Langfuse-traced)
  GET  /graph/insights/{movie_id}   (Neo4j traversal)
  GET  /health         (status, active LLM provider, feedback backend, cache, graph)
  Docker-compose: API + Qdrant + Postgres + Redis + Neo4j (Langfuse Cloud, not self-hosted)
  CORS enabled for the Vite dev server origin.

Layer 6: React Frontend -- built and verified (frontend/, Vite + react-router)
  Recommendation cards (poster + score + genres + cast + "Why this?" panel
  + "Graph insights" panel)
  Chat interface (LLM dialogue for conversational search)
  Onboarding wizard (cold-start flow)
  Thumbs up/down feedback
  Live API health badge in the nav bar

Phase 3.5: Streamlit public demo -- built and verified locally, not yet
  deployed to Streamlit Community Cloud. streamlit_app/app.py, thin wrapper
  over backend/recommender.py + llm_chains.py + graph.py (no API hop). Uses
  st.session_state to persist results across reruns -- per-card buttons
  (Explain, Graph insights, Liked, ...) each trigger a Streamlit rerun, and
  without session_state the whole recommendation list would vanish on any
  of those clicks (a real bug found and fixed while adding Graph insights).
```

### Status note: Neo4j, Langfuse, Redis
All three are now built and verified end-to-end (not just "no errors thrown"
-- see below for how each was actually confirmed):
- **Neo4j**: `src/08_neo4j_graph.py` loads the graph (MERGE-based, idempotent,
  batched); `backend/graph.py` queries it (`graph_insights()`); wired into
  `GET /graph/insights/{movie_id}` and a "Graph insights" button/panel in
  both the React and Streamlit UIs. Verified against real data: e.g. Star
  Wars (movie_id 50) correctly shows 501 raters and Return of the
  Jedi/Raiders of the Lost Ark as top co-liked/shared-genre movies.
- **Langfuse**: `backend/llm_chains.py`'s `_invoke_or_none()` attaches a
  `CallbackHandler` to every chain `.invoke()` call when
  `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are set. Verified by calling
  `explain_recommendation()` and then confirming via Langfuse's own public
  API (`GET /api/public/traces`) that a real trace landed on their servers
  -- not just that the code ran without throwing.
- **Redis**: `recommender.recommend_for_user()` does cache-aside with a
  5-minute TTL, keyed `recs:{user_id}:{k}`. Verified with a direct timing
  test: first call (cache miss) ~24ms, second call (cache hit) ~1ms, results
  identical. Falls back to always-fresh computation if Redis is unreachable.

---

## Key design decisions (important for context)

1. **LLM choice:** Claude API (Haiku for most calls, Sonnet for complex re-ranking).
   Reason: small local models hallucinate movie titles badly. Embeddings are done locally with E5.

2. **Two-tower training:**
   - Implicit feedback: rating >= 4 = positive interaction
   - Temporal split: last 20% of each user's history = test (never random split)
   - In-batch negatives + logQ popularity correction (CRITICAL — without this the model loses to a popularity baseline)
   - 64-dim towers, item tower takes [ID embedding + 19 genre flags]

3. **Hybrid retrieval:** cosine search over content vectors (~30 candidates) for conversational search; two-tower + log-popularity prior for the returning-user path. (Not literally Qdrant-filtered content search + a separate trending fallback as the original design sketch said -- see `backend/recommender.py` for what's actually implemented.)

4. **RAG pattern for conversations:** embed user query → cosine search over content vectors → LLM generates from retrieved real movies only (no hallucinations)

5. **Langfuse traces every LLM call:** implemented via `_invoke_or_none()` in `backend/llm_chains.py` wrapping every chain invocation with a callback handler when configured -- see the status note above for how this was verified.

---

## Verified benchmark results (ml-100k, 60 epochs)

| Ranker | Precision@10 | Recall@10 |
|---|---|---|
| Popularity baseline | 0.061 | 0.066 |
| Two-tower (collab only) | 0.059 | 0.090 |
| Two-tower + popularity prior (hybrid) | **0.094** | **0.121** |

The hybrid beats popularity by +55% precision / +83% recall.

---

## Project phases and notebooks

### Phase 1 — Jupyter prototype
```
notebooks/
  01_data_exploration.ipynb     # Load MovieLens, EDA, save train/test split
  02_rbm_baseline.ipynb         # Reproduce reference repo RBM, measure Precision@10
  03_content_embeddings.ipynb   # E5 embeddings, test "movies like X" search
  04_two_tower.ipynb            # Train two-tower, beat RBM
  05_qdrant_indexing.ipynb      # Load collab vectors into Qdrant, test ANN
  06_llm_layer.ipynb            # LangChain chains: parse -> retrieve -> rerank -> explain
  07_evaluation.ipynb           # Compare all approaches side by side

src/07_omdb_enrichment.py       # Poster/plot/cast via OMDb (no notebook mirror --
                                 # it's a batch data script, not exploratory/teaching
                                 # content). Title+year matched, since ml-100k ships
                                 # no links.csv. Multi-key rotation for daily quota.
src/08_neo4j_graph.py            # Loads User-RATED->Movie, Movie-HAS_GENRE->Genre
                                 # into Neo4j (also no notebook mirror -- batch script).
```

### Phase 2 — FastAPI backend
```
backend/
  main.py                  # FastAPI app, all routes
  recommender.py           # Core pipeline: ANN -> rank -> LLM, Redis cache-aside
  embedder.py              # E5 content embedding utility
  llm_chains.py            # LangChain chains (rerank, explain, onboarding, RAG), Langfuse-traced
  feedback.py              # Feedback capture -> Postgres
  graph.py                 # Neo4j queries -- graph_insights() for GET /graph/insights
  docker-compose.yml       # API + Qdrant + Postgres + Redis + Neo4j (Langfuse Cloud, not self-hosted)
  Dockerfile.render        # Render deploy: single-service image, bakes in data/+artifacts/
                            # (no volumes on Render's free tier), no Qdrant/Postgres/Redis/
                            # Neo4j sidecars -- recommender.py/graph.py/feedback.py already
                            # degrade gracefully without them. See render.yaml (project root).
```

### Phase 3 — React frontend
Cinematic dark/light theme (Bebas Neue display + Inter body + mono for
scores/ids), a marquee-red accent -- built and verified, see below.
```
frontend/
  src/
    api.js                     # Fetch client for all FastAPI routes
    hooks/
      useTheme.js               # Light/dark toggle, persisted in localStorage
      useWatchlist.js           # Favorites/watchlist, localStorage-backed, cross-component via a tiny listener set
    components/
      RecommendationCard.jsx    # Poster + score + watchlist star + "Why this?" + Graph insights
      ChatSearch.jsx            # Conversational search input + suggestion chips
      OnboardingWizard.jsx      # Cold-start dialogue flow
      ExplainPanel.jsx          # Detailed explanation panel
      GraphInsights.jsx          # Co-raters + shared-genre movies via Neo4j
      MovieModal.jsx             # Full-detail poster/plot/cast modal, opened from a card
      GenreFilter.jsx            # Genre chip filter over a result grid
      SkeletonCard.jsx           # Shimmer loading placeholders
    pages/
      Landing.jsx                # Hero + "how it works" + stat row, the "/" route
      Home.jsx                   # Returning-user recs, the "/app" route
      Search.jsx
      Profile.jsx
      Watchlist.jsx               # Saved movies, the "/watchlist" route
```
Deployment: `frontend/vercel.json` (SPA rewrite for react-router),
`frontend/.env.example` (`VITE_API_BASE`) -- see Phase 2's Render note below
and `SETUP_GUIDE.md` Section 9.5 for the full Vercel + Render walkthrough.

### Phase 3.5 — Streamlit public demo (parallel deployment track)
The React/FastAPI stack above remains the primary product architecture. Streamlit
is a **separate, lightweight deployment** for public/online access (recruiters,
portfolio reviewers) without needing to host React + FastAPI + Docker infra.
```
streamlit_app/
  app.py                   # Single-page Streamlit app: calls backend/recommender.py,
                            # llm_chains.py, and graph.py directly (no separate API hop)
  requirements.txt          # Streamlit-only subset of deps, including redis/neo4j/langfuse
```
Notes:
- Deploy via Streamlit Community Cloud (free, connects directly to the GitHub repo)
  -- **not done yet**; the app is built and verified locally only.
- Because Streamlit Cloud has no Docker-compose, the demo already degrades
  gracefully: Qdrant -> local/in-memory vector search fallback; Postgres ->
  SQLite (`backend/feedback.db`); Redis/Neo4j -> features that use them
  (caching, Graph insights) just silently skip if unreachable, same pattern
  as everything else.
- Secrets (`ANTHROPIC_API_KEY` or `GROQ_API_KEY`, `OMDB_API_KEY`,
  `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`) go in Streamlit Cloud's
  secrets manager once deployed, not `.env`.
- `streamlit_app/app.py` is a thin UI wrapper reusing `recommender.py` /
  `llm_chains.py` / `graph.py` from the backend, as designed. It uses
  `st.session_state` to persist recommendation results across reruns --
  without this, clicking ANY per-card button (Explain, Graph insights,
  Liked, ...) would make the whole result list disappear, since each button
  click triggers a Streamlit rerun where the primary "Recommend"/"Search"
  button's own `st.button()` call returns `False` again.

---

## What's already built / verified
- [x] Two-tower model: trained and evaluated on ml-100k, saved as `two_tower.pt` and `item_vecs.npy`
- [x] Benchmark numbers confirmed (see table above)
- [x] logQ popularity correction implemented
- [x] Temporal train/test split implemented
- [x] All notebooks 01-07 (`07_llm_layer` and `07_evaluation` split as separate
      numbered notebooks -- see nested `cinemind_phase1/CLAUDE.md`), each executed
      end-to-end with real output saved
- [x] `src/07_omdb_enrichment.py` -- poster/plot/cast enrichment, 1,548/1,682 matched
- [x] `src/08_neo4j_graph.py` + `backend/graph.py` -- graph loaded and queried, verified
- [x] Redis cache-aside for recommendations -- verified with a real timing test
- [x] Langfuse tracing -- verified via Langfuse's own public API that a trace landed
- [x] FastAPI backend (`backend/`) -- all 7 routes, Docker Compose stack, CORS
- [x] React frontend (`frontend/`) -- all components/pages, verified in a real
      browser via Playwright against the live Docker API
- [x] React redesign -- cinematic dark/light theme, landing page, watchlist,
      genre filter, movie detail modal, skeleton loaders; verified in a real
      browser via Playwright screenshots (light/dark/mobile)
- [x] Streamlit public demo (`streamlit_app/app.py`) -- verified locally in browser
- [x] `backend/Dockerfile.render` + `render.yaml` -- single-service Render deploy,
      built and smoke-tested locally with `docker build`/`docker run`: `/health`
      and `/recommendations/{id}` confirmed working with no Qdrant/Postgres/
      Redis/Neo4j reachable (numpy fallback, SQLite fallback, graph disabled)
- [x] `frontend/vercel.json` + `.env.example` -- Vercel deploy config for the
      React app (SPA rewrite, `VITE_API_BASE`)

## What's genuinely left
- [ ] Actually click "Deploy" on Render and Vercel (config is written and
      smoke-tested locally, but neither service has been deployed yet --
      see `SETUP_GUIDE.md` Section 9.5)
- [ ] Deploy the Streamlit app to Streamlit Community Cloud (public link)
- [ ] The remaining ~134 unmatched movies in OMDb enrichment (obscure titles;
      may just not exist in OMDb's catalogue)
- [ ] Neo4j graph is currently genre + rating structure only -- no Director
      node/edge (the original design's "because you liked movies by this
      director" use case), since OMDb's Director field was never captured
      into `movie_meta.csv`

---

## Terms to know (quick reference)
- **Embedding:** a thing (movie, user) converted to a list of numbers; similar things = nearby numbers
- **ANN search:** find nearest vectors fast (Qdrant does this)
- **Two-tower:** twin neural nets producing user + movie vectors; dot product = match score
- **In-batch negatives:** each batch provides its own negatives automatically (512 pairs = 512x512 comparison matrix)
- **logQ correction:** subtract log(P(item)) from logits to fix popularity bias in in-batch negative sampling
- **RAG:** retrieve real data first, then let LLM generate from it (prevents hallucinated titles)
- **Cold start:** no history for a new user/item; solved by content embeddings + LLM onboarding chat
- **Langfuse:** observability layer; records every LLM step with cost, latency, inputs/outputs
- **LangChain LCEL:** declarative pipeline syntax for chaining LLM steps (parse -> retrieve -> rerank -> explain)

---

## Environment setup (run once)
```bash
# Python deps (see requirements.txt for the full, current list)
pip install -r requirements.txt

# Start infrastructure (pass --env-file explicitly -- see backend/docker-compose.yml
# header comment for why plain -f alone can silently drop your API keys)
docker compose --env-file .env -f backend/docker-compose.yml up -d --build

# Environment variables (.env at project root) -- only ONE of the two LLM
# keys is required; Anthropic is preferred if both are set
ANTHROPIC_API_KEY=your_key      # optional -- paid, preferred if set
GROQ_API_KEY=your_key           # optional -- free tier, used if Anthropic isn't set
OMDB_API_KEY=your_key           # optional -- poster/plot/cast; comma-separate multiple keys to rotate on quota
LANGFUSE_PUBLIC_KEY=your_key    # optional -- tracing (verified working, see status note)
LANGFUSE_SECRET_KEY=your_key    # optional
LANGFUSE_HOST=https://cloud.langfuse.com   # optional, this is the default
QDRANT_URL=http://localhost:6333
POSTGRES_URL=postgresql://user:pass@localhost:5432/cinemind
REDIS_URL=redis://localhost:6379   # recommendation cache, 5 min TTL
NEO4J_URI=bolt://localhost:7687     # graph insights
NEO4J_USER=neo4j
NEO4J_PASSWORD=cinemind123          # matches backend/docker-compose.yml's NEO4J_AUTH
```
Everything above is optional in the sense that the app runs and degrades
gracefully without it (numpy fallback, SQLite fallback, retrieval-only mode,
no cache, no graph insights) -- see `backend/recommender.py`,
`backend/llm_chains.py`, and `backend/graph.py`.

---

## Codex / OpenAI compatibility note
If running this context in OpenAI Codex, replace:
- `langchain-anthropic` -> `langchain-openai`
- `ChatAnthropic` -> `ChatOpenAI(model="gpt-4o-mini")`
- `ANTHROPIC_API_KEY` -> `OPENAI_API_KEY`
All other code remains identical — LangChain abstracts the model.
