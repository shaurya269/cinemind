# CineMind

CineMind is a full-stack movie recommendation system combining a Two-Tower
deep learning model with content embeddings and an LLM reasoning layer
(Claude or Groq). This folder contains the Jupyter-prototype phase (Phase 1)
plus the FastAPI backend (Phase 2), React frontend (Phase 3), and Streamlit
demo (Phase 3.5) that were built on top of it. See `CLAUDE.md` for the full
architecture and current build status.

## What Phase 1 contains

| Script | What it does |
|--------|--------------|
| `src/01_data_exploration.py` | Loads MovieLens, explores it, saves train/test split |
| `src/02_rbm_baseline.py` | Reproduces the reference RBM as a baseline |
| `src/03_content_embeddings.py` | Builds content vectors with the E5 model |
| `src/04_two_tower.py` | Trains the modern two-tower model (the centrepiece) |
| `src/05_qdrant_indexing.py` | Loads vectors into Qdrant, tests ANN search |
| `src/06_evaluation.py` | Compares all approaches, saves results |
| `src/07_omdb_enrichment.py` | Poster/plot/cast via OMDb, title+year matched (optional) |
| `src/08_neo4j_graph.py` | Loads ratings + genres into Neo4j for graph insights (optional) |
| `src/cinemind_utils.py` | Shared data-loading + split + metrics |

## Quick start

```bash
# 1. Set up the environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Download MovieLens 100K and put the ml-100k folder in data/
#    (see SETUP_GUIDE.md for the exact download steps)

# 3. Run the scripts in order
python src/01_data_exploration.py
python src/02_rbm_baseline.py
python src/03_content_embeddings.py
python src/04_two_tower.py
python src/05_qdrant_indexing.py
python src/06_evaluation.py
python src/07_omdb_enrichment.py   # optional -- needs OMDB_API_KEY, adds posters/plot/cast
python src/08_neo4j_graph.py       # optional -- needs Neo4j running, adds graph insights
```

See **SETUP_GUIDE.md** for the full step-by-step walkthrough, including how to
run this in VS Code and save it to GitHub.

## Run the API, demo app, or frontend

After the Phase 1 artifacts exist, run any of these from the project root:

```bash
# API
uvicorn backend.main:app --reload --port 8000

# Public demo UI (Streamlit)
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py

# React frontend (needs Node.js; needs the API running for data)
cd frontend
npm install
npm run dev
```

The app works without Docker. Qdrant falls back to in-memory numpy search, and
feedback falls back to `backend/feedback.db` when Postgres is not configured.
Set `ANTHROPIC_API_KEY` or `GROQ_API_KEY` to enable LLM parsing, reranking, and
explanations; otherwise CineMind still returns grounded retrieval results.
Live semantic search uses a cached `intfloat/e5-small-v2` model when available;
set `CINEMIND_ALLOW_MODEL_DOWNLOAD=1` to let the app download it on first use.
Set `OMDB_API_KEY` (see `src/07_omdb_enrichment.py`) to show posters/plot/cast
in either UI; without it, cards just render without a poster. Recommendations
are cached in Redis for 5 minutes when reachable (falls back to always-fresh
otherwise). Set `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` to trace every LLM
call at cloud.langfuse.com. Run `src/08_neo4j_graph.py` (needs Neo4j) to enable
the "Graph insights" panel in either UI, showing which other users also liked
a movie and which movies share the most genres with it.

To run the full Docker stack (API + Qdrant + Postgres + Redis + Neo4j) instead
of the local fallbacks:
```bash
docker compose --env-file .env -f backend/docker-compose.yml up -d --build
python src/08_neo4j_graph.py   # load the graph once Neo4j is up
```

## Verified results (MovieLens 100K)

| Model | Precision@10 | Recall@10 |
|-------|-------------|-----------|
| Popularity baseline | 0.061 | 0.066 |
| RBM | 0.075 | 0.082 |
| Two-tower | 0.058 | 0.091 |
| Two-tower + pop prior | **0.093** | **0.126** |
