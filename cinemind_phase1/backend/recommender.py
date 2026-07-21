"""
recommender.py
===============
PHASE 2 — Core recommendation pipeline: ANN candidate generation -> ranking.

This wraps the artifacts produced by the Phase 1 notebooks/scripts (run from
the project root, in order 01 -> 05) behind a small set of plain functions
that main.py (and later streamlit_app/app.py) call directly:

    load()                          -- call once at startup
    recommend_for_user(user_id, k)  -- returning-user path (two-tower + pop prior)
    retrieve_candidates(query, k)   -- content-based RAG retrieval for chat/onboarding
    similar_to_movie(movie_id, k)   -- "movies like X" via content vectors
    movie_meta(movie_id)            -- title/genres lookup for explanations

Falls back gracefully wherever Phase 1 already established the pattern:
Qdrant -> numpy search if no server is reachable (see notebooks 05/06). There
is no fallback for missing artifacts themselves -- those must exist (run the
Phase 1 pipeline first).
"""

import os
import sys
import importlib.util
import re
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import torch

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(os.path.dirname(_BACKEND_DIR), "src")
for _p in (_SRC_DIR, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REQUIRED_FILES = [
    "data/train_positives.csv", "data/test_positives.csv", "data/items.csv",
    "artifacts/two_tower.pt", "artifacts/item_vecs.npy",
    "artifacts/content_vecs.npy", "artifacts/content_movie_ids.npy",
]

COLLECTION = "collab_vectors"

MOVIE_META_PATH = "artifacts/movie_meta.csv"

# Populated by load()
_loaded = False
items = None
title_of = {}
genres_of = {}
seen = {}
top_pop = None
log_pop = None
item_vecs = None
content_vecs = None
content_ids = None
model = None
_use_qdrant = False
_qdrant_client = None
enrich_of = {}   # movie_id -> {poster_url, overview, cast}, optional (step 07, OMDb)


def _import_two_tower_module():
    """04_two_tower.py has a numeric-prefixed filename, so it can't be
    imported with a normal `import` statement -- load it by path instead."""
    spec = importlib.util.spec_from_file_location(
        "two_tower_module", os.path.join(_SRC_DIR, "04_two_tower.py")
    )
    tt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tt)
    return tt


def load():
    """Load all artifacts and the trained model into memory. Idempotent --
    safe to call from FastAPI's startup event and again from a notebook."""
    global _loaded, items, title_of, genres_of, seen, top_pop, log_pop
    global item_vecs, content_vecs, content_ids, model, _use_qdrant, _qdrant_client, enrich_of

    if _loaded:
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    missing = [f for f in REQUIRED_FILES if not os.path.exists(f)]
    if missing:
        raise FileNotFoundError(
            "Missing Phase 1 artifacts: " + ", ".join(missing) +
            ". Run the notebooks/scripts 01 -> 06 first (see SETUP_GUIDE.md)."
        )

    train = pd.read_csv("data/train_positives.csv")
    test = pd.read_csv("data/test_positives.csv")
    items = pd.read_csv("data/items.csv")

    title_of = dict(zip(items.movie_id, items.title))
    genres_of = dict(zip(items.movie_id, items.genres))
    seen = train.groupby("user_id").movie_id.apply(set).to_dict()
    top_pop = train.movie_id.value_counts().index.to_numpy()

    item_vecs = np.load("artifacts/item_vecs.npy").astype(np.float32)
    n_items = item_vecs.shape[0]

    content_vecs = np.load("artifacts/content_vecs.npy").astype(np.float32)
    content_vecs = content_vecs / np.linalg.norm(content_vecs, axis=1, keepdims=True)
    content_ids = np.load("artifacts/content_movie_ids.npy")

    pop_cnt = train.movie_id.value_counts().reindex(range(n_items), fill_value=0).to_numpy()
    log_pop = np.log1p(pop_cnt)
    log_pop = log_pop / log_pop.max()

    # Rebuild the model architecture exactly as in notebook 04 so the saved
    # state_dict loads cleanly, then compute user vectors on demand.
    tt = _import_two_tower_module()
    genre_mat = np.zeros((n_items, 19), dtype=np.float32)
    flags = items[[f"g{i}" for i in range(19)]].to_numpy(dtype=np.float32)
    genre_mat[items.movie_id.values] = flags
    item_counts = pop_cnt.astype(np.float64) + 1.0
    n_users = int(max(train.user_id.max(), test.user_id.max())) + 1

    model = tt.TwoTower(n_users, n_items, torch.tensor(genre_mat), item_counts)
    model.load_state_dict(torch.load("artifacts/two_tower.pt", map_location="cpu"))
    model.eval()

    # Optional: real Qdrant for collab-vector ANN search (numpy fallback
    # otherwise) -- same auto-detect pattern as notebook 05.
    try:
        from qdrant_client import QdrantClient
        qdrant_url = os.environ.get("QDRANT_URL")
        if qdrant_url:
            parsed = urlparse(qdrant_url)
            _qdrant_client = QdrantClient(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6333,
                https=parsed.scheme == "https",
                timeout=3,
            )
        else:
            _qdrant_client = QdrantClient(host="localhost", port=6333, timeout=3)
        _qdrant_client.get_collections()
        _use_qdrant = True
    except Exception:
        _use_qdrant = False

    # Optional: poster/overview/cast from step 07 (OMDb enrichment). ml-100k
    # ships no links.csv, so this is produced by a separate title+year match
    # against the OMDb API rather than a join -- see src/07_omdb_enrichment.py.
    # Movies not yet enriched (or run without an OMDB_API_KEY at all) simply
    # get no poster/overview/cast; nothing downstream requires it.
    if os.path.exists(MOVIE_META_PATH):
        meta_df = pd.read_csv(MOVIE_META_PATH)
        enrich_of = {
            int(r.movie_id): {
                "poster_url": r.poster_url if pd.notna(r.poster_url) else None,
                "overview": r.overview if pd.notna(r.overview) else None,
                "cast": r.cast if pd.notna(r.cast) else None,
            }
            for r in meta_df.itertuples()
        }
    else:
        enrich_of = {}

    _loaded = True


def known_user(user_id: int) -> bool:
    """True if this user_id has training history (can use the two-tower
    model). New users must go through onboarding / content retrieval."""
    return user_id in seen


def _movie_payload(movie_id: int, score: float = None):
    """Build the dict shape every route/UI consumes for one movie: base
    MovieLens fields plus OMDb enrichment when available (poster_url/
    overview/cast are None if step 07 hasn't been run for this movie)."""
    movie_id = int(movie_id)
    payload = {
        "movie_id": movie_id,
        "title": title_of.get(movie_id, "Unknown"),
        "genres": genres_of.get(movie_id, "[]"),
    }
    if score is not None:
        payload["score"] = float(score)
    extra = enrich_of.get(movie_id, {})
    payload["poster_url"] = extra.get("poster_url")
    payload["overview"] = extra.get("overview")
    payload["cast"] = extra.get("cast")
    return payload


def recommend_for_user(user_id: int, k: int = 10, alpha: float = 0.30):
    """Returning-user path: two-tower similarity + a small popularity prior
    (the hybrid ranker that beat both pure approaches in notebook 04/07)."""
    if not _loaded:
        load()
    k = max(1, min(k, len(title_of)))
    with torch.no_grad():
        uv = model.user_vec(torch.tensor([user_id]))
        scores = (uv @ torch.tensor(item_vecs).t()).squeeze(0).numpy() + alpha * log_pop
    for m in seen.get(user_id, set()):
        scores[m] = -1e9
    top_idx = np.argpartition(-scores, k)[:k]
    top_idx = top_idx[np.argsort(-scores[top_idx])]
    return [
        _movie_payload(m, scores[m])
        for m in top_idx if int(m) in title_of
    ]


def retrieve_candidates(query: str, k: int = 30):
    """Free-text query -> top-k real movies by content similarity. This is
    the RAG grounding step: every candidate is a real row from items.csv, so
    downstream LLM chains can't hallucinate a title."""
    if not _loaded:
        load()
    k = max(1, min(k, len(content_ids)))
    try:
        from embedder import embed_query
        q_vec = embed_query(query)
        sims = content_vecs @ q_vec
        order = np.argsort(-sims)[:k]
        return [_movie_payload(content_ids[row], sims[row]) for row in order]
    except Exception:
        order, scores = _lexical_candidates(query, k)
    return [_movie_payload(m, scores[pos]) for pos, m in enumerate(order)]


def _lexical_candidates(query: str, k: int):
    """Offline fallback for first-run environments that cannot download E5."""
    tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
    rows = []
    for row in items.itertuples(index=False):
        haystack = f"{row.title} {row.genres}".lower()
        token_hits = sum(1 for token in tokens if token in haystack)
        popularity = float(log_pop[int(row.movie_id)]) if log_pop is not None else 0.0
        score = token_hits + 0.05 * popularity
        if score > 0:
            rows.append((int(row.movie_id), score))

    if not rows:
        rows = [(int(m), float(log_pop[int(m)]) if log_pop is not None else 0.0) for m in top_pop[:k]]

    rows.sort(key=lambda pair: pair[1], reverse=True)
    rows = rows[:k]
    return [m for m, _ in rows], [s for _, s in rows]


def similar_to_movie(movie_id: int, k: int = 10):
    """"Movies like X" via collaborative item vectors (Qdrant if available,
    numpy fallback otherwise) -- same taste-based neighbours as notebook 05."""
    if not _loaded:
        load()
    if movie_id < 0 or movie_id >= len(item_vecs):
        return []
    k = max(1, min(k, len(item_vecs) - 1))
    query_vec = item_vecs[movie_id]

    if _use_qdrant:
        hits = _qdrant_client.query_points(
            collection_name=COLLECTION, query=query_vec.tolist(), limit=k + 1,
        )
        neighbours = [(h.id, h.score) for h in hits.points]
    else:
        sims = item_vecs @ query_vec
        order = np.argsort(-sims)[:k + 1]
        neighbours = [(int(j), float(sims[j])) for j in order]

    return [
        _movie_payload(m, s)
        for m, s in neighbours if int(m) != movie_id
    ][:k]


def movie_meta(movie_id: int):
    """Metadata for one movie, or None if it doesn't exist -- used by
    /explain/{movie_id} to ground the LLM explanation in real fields."""
    if not _loaded:
        load()
    if movie_id not in title_of:
        return None
    return _movie_payload(movie_id)
