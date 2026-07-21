"""
main.py
=======
PHASE 2 — FastAPI app exposing the CineMind pipeline over HTTP.

Routes (per CLAUDE.md):
    GET  /recommendations/{user_id}   -- returning-user path (two-tower + pop prior)
    POST /chat                        -- conversational search (RAG parse/retrieve/rerank/explain)
    POST /onboarding                  -- cold-start dialogue for new users
    POST /feedback                    -- clicks/ratings -> storage for retraining
    GET  /explain/{movie_id}          -- grounded "Why this?" explanation
    GET  /graph/insights/{movie_id}   -- graph-derived context (co-raters, shared genres)
    GET  /health                      -- readiness probe

Run locally (no Docker required -- everything below degrades gracefully):
    uvicorn backend.main:app --reload --port 8000
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import recommender
import llm_chains
import feedback
import graph

app = FastAPI(title="CineMind API", version="0.1.0")

# The React frontend (Vite dev server / static build) runs on a different
# origin than the API, so the browser needs an explicit CORS allow-list --
# without this every fetch() from frontend/ fails before reaching a route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    recommender.load()
    graph.load()


class ChatRequest(BaseModel):
    query: str


class OnboardingRequest(BaseModel):
    answers: str


class FeedbackRequest(BaseModel):
    user_id: int
    movie_id: int
    rating: float | None = None
    clicked: bool | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_available": llm_chains.LLM_AVAILABLE,
        "llm_provider": llm_chains.LLM_PROVIDER,
        "langfuse_tracing": llm_chains.LANGFUSE_AVAILABLE,
        "feedback_backend": feedback.backend_in_use(),
        "recs_cache": "redis" if recommender._redis_client is not None else "none",
        "graph_available": graph.GRAPH_AVAILABLE,
    }


@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: int, k: int = 10):
    if not recommender.known_user(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"No history for user_id={user_id}. New users should call POST /onboarding.",
        )
    return {"user_id": user_id, "recommendations": recommender.recommend_for_user(user_id, k=k)}


@app.post("/chat")
def chat(req: ChatRequest):
    return {"query": req.query, "results": llm_chains.conversational_search(req.query)}


@app.post("/onboarding")
def onboarding(req: OnboardingRequest):
    return {"seed_recommendations": llm_chains.onboard_new_user(req.answers)}


@app.post("/feedback")
def post_feedback(req: FeedbackRequest):
    return feedback.log_feedback(req.user_id, req.movie_id, rating=req.rating, clicked=req.clicked)


@app.get("/explain/{movie_id}")
def explain(movie_id: int, query: str = "this recommendation"):
    explanation = llm_chains.explain_recommendation(movie_id, query=query)
    if explanation is None:
        raise HTTPException(status_code=404, detail=f"Unknown movie_id={movie_id}")
    return {"movie_id": movie_id, "explanation": explanation}


@app.get("/graph/insights/{movie_id}")
def graph_insights(movie_id: int, k: int = 5):
    insights = graph.graph_insights(movie_id, k=k)
    if insights is None:
        raise HTTPException(
            status_code=404,
            detail=f"No graph data for movie_id={movie_id} (unrated in training data, "
                    "or Neo4j isn't reachable -- check GET /health's graph_available field).",
        )
    return {"movie_id": movie_id, **insights}
