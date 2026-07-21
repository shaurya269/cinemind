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
| Graph database | Neo4j — **not yet built** (still "later phase", see status note below) |
| Cache | Redis — provisioned in `docker-compose.yml` but not yet wired into any code path |
| Relational DB | PostgreSQL (used for feedback storage; SQLite fallback when unreachable) |
| LLM API | Claude API (Haiku/Sonnet) **or** Groq (Llama 3.x, free tier) — provider auto-selected by whichever `ANTHROPIC_API_KEY`/`GROQ_API_KEY` is set, Anthropic preferred |
| LLM orchestration | LangChain (LCEL chains, PromptTemplates); retrieval is direct cosine search over content vectors, not a Qdrant-backed retriever object |
| Observability | Langfuse — **not yet wired up** (optional hook exists in code but has never been exercised with real keys; see status note below) |
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
  Neo4j    - NOT YET BUILT. Still deferred ("later phase") -- no graph queries
             exist anywhere in the codebase yet.
  Redis    - provisioned in docker-compose.yml (container runs) but no
             application code reads/writes it yet -- not actually wired in.
  Postgres - feedback logs (SQLite fallback when Postgres isn't reachable)

Layer 4: Online pipeline (per request)
  Step 1: Candidate generation - cosine search over content vectors -> ~30 candidates
  Step 2: Ranking - two-tower dot product + 0.30 * log-popularity prior (hybrid scorer)
  Step 3: LLM reasoning (LangChain), when ANTHROPIC_API_KEY or GROQ_API_KEY is set:
    a) Conversational query parsing (RAG)
    b) Re-ranking top ~30 -> final 10 (de-duplicated -- free-tier models can repeat ids)
    c) "Why this?" explanation generation (grounded in real metadata + plot when available)
    d) Cold-start onboarding chat (new users)
    Without a key, falls back to retrieval-only results (no crash).
  Langfuse tracing hook exists in code but has NOT been exercised with real
  keys yet -- see status note below.

Layer 5: Backend (FastAPI) -- built and verified
  GET  /recommendations/{user_id}
  POST /chat          (conversational search)
  POST /onboarding    (cold-start dialogue)
  POST /feedback      (clicks, ratings -> retraining)
  GET  /explain/{movie_id}
  GET  /health         (status, active LLM provider, feedback backend)
  Docker-compose: API + Qdrant + Postgres + Redis (Langfuse Cloud, not self-hosted)
  CORS enabled for the Vite dev server origin.

Layer 6: React Frontend -- built and verified (frontend/, Vite + react-router)
  Recommendation cards (poster + score + genres + cast + "Why this?" panel)
  Chat interface (LLM dialogue for conversational search)
  Onboarding wizard (cold-start flow)
  Thumbs up/down feedback
  Live API health badge in the nav bar

Phase 3.5: Streamlit public demo -- built and verified locally, not yet
  deployed to Streamlit Community Cloud. streamlit_app/app.py, thin wrapper
  over backend/recommender.py + llm_chains.py (no API hop).
```

### Status note: Neo4j and Langfuse
Both appear in the tech-stack table above because they're part of the
original design, but **neither is built yet**:
- **Neo4j**: zero code exists. No graph schema, no driver, no queries. It
  would slot into Layer 3 as a `user -> rated -> movie -> directed_by ->
  person -> directed -> movie` graph, used for explanations like "because
  you liked movies by this director" or graph-based candidate generation.
  Nothing downstream currently depends on it.
- **Langfuse**: `backend/llm_chains.py` and `notebooks/06_llm_layer.ipynb`
  both have an optional Langfuse callback-handler hook (see the "Langfuse
  tracing" section of the notebook), gated behind `LANGFUSE_PUBLIC_KEY` /
  `LANGFUSE_SECRET_KEY` being set -- but those keys have never actually been
  provided, so this path has never run end-to-end. It degrades silently
  (`LANGFUSE_AVAILABLE = False`) when unset, same pattern as every other
  optional integration in this codebase.

---

## Key design decisions (important for context)

1. **LLM choice:** Claude API (Haiku for most calls, Sonnet for complex re-ranking).
   Reason: small local models hallucinate movie titles badly. Embeddings are done locally with E5.

2. **Two-tower training:**
   - Implicit feedback: rating >= 4 = positive interaction
   - Temporal split: last 20% of each user's history = test (never random split)
   - In-batch negatives + logQ popularity correction (CRITICAL — without this the model loses to a popularity baseline)
   - 64-dim towers, item tower takes [ID embedding + 19 genre flags]

3. **Hybrid retrieval:** ANN(collab vector) + ANN(content vector of recent favorites) + trending fallback = ~200 candidates

4. **RAG pattern for conversations:** embed user query → Qdrant filtered search → LLM generates from retrieved real movies only (no hallucinations)

5. **Langfuse from day 1:** trace every LLM call, monitor cost/latency, version prompts, attach feedback signals

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
```

### Phase 2 — FastAPI backend
```
backend/
  main.py                  # FastAPI app, all routes
  recommender.py           # Core pipeline: ANN -> rank -> LLM
  embedder.py              # E5 content embedding utility
  llm_chains.py            # LangChain chains (rerank, explain, onboarding, RAG)
  feedback.py              # Feedback capture -> Postgres
  docker-compose.yml       # API + Qdrant + Postgres + Redis + Langfuse
```

### Phase 3 — React frontend
```
frontend/
  src/
    components/
      RecommendationCard.jsx    # Poster + score + "Why this?" expandable
      ChatSearch.jsx            # Conversational search input
      OnboardingWizard.jsx      # Cold-start dialogue flow
      ExplainPanel.jsx          # Detailed explanation panel
    pages/
      Home.jsx
      Search.jsx
      Profile.jsx
```

### Phase 3.5 — Streamlit public demo (parallel deployment track)
The React/FastAPI stack above remains the primary product architecture. Streamlit
is a **separate, lightweight deployment** for public/online access (recruiters,
portfolio reviewers) without needing to host React + FastAPI + Docker infra.
```
streamlit_app/
  app.py                   # Single-page Streamlit app: calls backend/recommender.py
                            # and llm_chains.py directly (no separate API hop)
  requirements.txt          # Streamlit-only subset of deps (no Neo4j/Redis/Postgres —
                            # use lightweight fallbacks: SQLite/local pickle for demo data)
```
Notes:
- Deploy via Streamlit Community Cloud (free, connects directly to the GitHub repo)
  -- **not done yet**; the app is built and verified locally only.
- Because Streamlit Cloud has no Docker-compose, the demo already degrades
  gracefully: Qdrant -> local/in-memory vector search fallback; Postgres ->
  SQLite (`backend/feedback.db`); Neo4j/Redis skipped (neither is used yet
  regardless of environment -- see the Neo4j/Langfuse status note above).
- Secrets (`ANTHROPIC_API_KEY` or `GROQ_API_KEY`, `OMDB_API_KEY`) go in
  Streamlit Cloud's secrets manager once deployed, not `.env`.
- `streamlit_app/app.py` is already a thin UI wrapper reusing
  `recommender.py` / `llm_chains.py` from the backend, as designed.

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
- [x] FastAPI backend (`backend/`) -- all 6 routes, Docker Compose stack, CORS
- [x] React frontend (`frontend/`) -- all components/pages, verified in a real
      browser via Playwright against the live Docker API
- [x] Streamlit public demo (`streamlit_app/app.py`) -- verified locally in browser

## What's genuinely left
- [ ] Deploy the Streamlit app to Streamlit Community Cloud (public link)
- [ ] Neo4j graph layer -- not started at all (see status note above)
- [ ] Langfuse tracing -- code path exists but never exercised with real keys
- [ ] The remaining ~134 unmatched movies in OMDb enrichment (obscure titles;
      may just not exist in OMDb's catalogue)

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
LANGFUSE_PUBLIC_KEY=your_key    # optional -- tracing, never exercised yet (see status note)
LANGFUSE_SECRET_KEY=your_key    # optional
QDRANT_URL=http://localhost:6333
POSTGRES_URL=postgresql://user:pass@localhost:5432/cinemind
REDIS_URL=redis://localhost:6379   # provisioned, not yet used by any code
```
Everything above is optional in the sense that the app runs and degrades
gracefully without it (numpy fallback, SQLite fallback, retrieval-only mode)
-- see `backend/recommender.py` and `backend/llm_chains.py`.

---

## Codex / OpenAI compatibility note
If running this context in OpenAI Codex, replace:
- `langchain-anthropic` -> `langchain-openai`
- `ChatAnthropic` -> `ChatOpenAI(model="gpt-4o-mini")`
- `ANTHROPIC_API_KEY` -> `OPENAI_API_KEY`
All other code remains identical — LangChain abstracts the model.
