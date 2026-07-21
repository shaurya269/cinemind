"""
llm_chains.py
=============
PHASE 2 — LangChain chains for conversational search, re-ranking, grounded
explanations, and cold-start onboarding. This is the production version of
notebooks/06_llm_layer.ipynb: same chains, now importable by main.py (and
later streamlit_app/app.py per CLAUDE.md).

Every chain here follows the RAG pattern from notebook 06: the LLM only ever
reasons over movies that recommender.retrieve_candidates() actually found in
items.csv, so it cannot invent a title or a movie_id.

Degrades gracefully (LLM_AVAILABLE flag) exactly like the notebook: if no
provider is configured, callers get a clear retrieval-only result instead of
a crash.

PROVIDER SELECTION -- checked in this order, first one with a key wins:
  1. Anthropic (ANTHROPIC_API_KEY)  -- Claude Haiku / Sonnet, paid
  2. Groq (GROQ_API_KEY)            -- Llama 3.x on Groq, generous free tier
This means the exact same chains below run on whichever provider is
configured, with no other code changes needed -- set ANTHROPIC_API_KEY later
and it takes over automatically.
"""

import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import json
import re
from ast import literal_eval

import recommender

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda


def _parse_json_loose(message):
    """Extract a JSON value from an LLM response, tolerating the extra prose,
    markdown fences, or inline '#' comments that free-tier models (Groq's
    Llama in particular) sometimes add despite being told "JSON only" --
    Claude follows that instruction strictly, but we can't assume every
    provider will, so this is used instead of a strict JsonOutputParser.
    """
    text = message.content if hasattr(message, "content") else str(message)
    text = re.sub(r"#.*", "", text)   # strip inline comments before parsing
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in LLM output: {text[:200]}")
    return json.loads(match.group(1))


_json_parser = RunnableLambda(_parse_json_loose)

LLM_PROVIDER = None   # "anthropic" | "groq" | None
_haiku = None          # small/cheap model -- parsing, explaining, onboarding
_sonnet = None         # larger model -- re-ranking (needs more judgement)

if os.environ.get("ANTHROPIC_API_KEY"):
    try:
        from langchain_anthropic import ChatAnthropic
        _haiku = ChatAnthropic(model="claude-3-5-haiku-latest", temperature=0)
        _sonnet = ChatAnthropic(model="claude-sonnet-4-5", temperature=0.3)
        LLM_PROVIDER = "anthropic"
    except ImportError:
        pass

if LLM_PROVIDER is None and os.environ.get("GROQ_API_KEY"):
    try:
        from langchain_groq import ChatGroq
        _haiku = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        _sonnet = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
        LLM_PROVIDER = "groq"
    except ImportError:
        pass

LLM_AVAILABLE = LLM_PROVIDER is not None

parse_query_chain = None
rerank_chain = None
explain_chain = None
onboarding_chain = None

if LLM_AVAILABLE:

    parse_query_chain = (
        ChatPromptTemplate.from_messages([
            ("system",
             "You turn a free-text movie request into a JSON search intent. "
             "Return ONLY JSON with keys: search_text (a short phrase to embed "
             "for similarity search), mood (one or two words), exclude_genres "
             "(list, may be empty). No prose, no markdown fences."),
            ("human", "{query}"),
        ])
        | _haiku | _json_parser
    )

    rerank_chain = (
        ChatPromptTemplate.from_messages([
            ("system",
             "You rank movies for a user request. You may ONLY choose from the "
             "candidate list given to you -- never invent a movie_id or title. "
             "Respond with NOTHING but a JSON array of up to 10 movie_id integers, "
             "best match first -- no explanation, no comments, no markdown fences, "
             "no text before or after the array."),
            ("human",
             "User request: {query}\n\nCandidates (movie_id | title | genres):\n"
             "{candidates}"),
        ])
        | _sonnet | _json_parser
    )

    explain_chain = (
        ChatPromptTemplate.from_messages([
            ("system",
             "Explain in 1-2 sentences why this movie fits the user's request. "
             "Ground your answer in the genres given, and in the plot summary "
             "when one is provided -- do not invent plot details, cast, or "
             "facts beyond what's given."),
            ("human",
             "User request: {query}\nMovie: {title} | Genres: {genres}\n"
             "Plot: {overview}"),
        ])
        | _haiku | StrOutputParser()
    )

    onboarding_chain = (
        ChatPromptTemplate.from_messages([
            ("system",
             "A new user answered onboarding questions about movies they like. "
             "Summarise their taste as a short search phrase (one sentence) "
             "suitable for a semantic movie search. Return ONLY that sentence, "
             "no preamble."),
            ("human", "{answers}"),
        ])
        | _haiku | StrOutputParser()
    )


def _invoke_or_none(chain, payload):
    """Run an optional LLM chain. Network/API failures should degrade the
    app to retrieval-only behavior instead of breaking recommendations."""
    try:
        return chain.invoke(payload)
    except Exception:
        return None


def conversational_search(query: str, k_candidates: int = 30, k_final: int = 10):
    """query -> parse -> retrieve (grounded) -> rerank -> explain top pick.

    Falls back to plain content retrieval (no parse/rerank/explain) if the
    LLM isn't configured, matching notebook 06.
    """
    if not LLM_AVAILABLE:
        return recommender.retrieve_candidates(query, k=k_final)

    intent = _invoke_or_none(parse_query_chain, {"query": query})
    if not isinstance(intent, dict):
        return recommender.retrieve_candidates(query, k=k_final)

    search_text = intent.get("search_text", query)

    candidates = recommender.retrieve_candidates(search_text, k=k_candidates)
    exclude = set(g.lower() for g in intent.get("exclude_genres", []))
    if exclude:
        candidates = [
            c for c in candidates
            if not exclude & set(g.lower() for g in literal_eval(c["genres"]))
        ]

    candidate_lines = "\n".join(
        f"{c['movie_id']} | {c['title']} | {c['genres']}" for c in candidates
    )
    ranked_ids = _invoke_or_none(rerank_chain, {"query": query, "candidates": candidate_lines})
    if not isinstance(ranked_ids, list):
        return candidates[:k_final]

    by_id = {c["movie_id"]: c for c in candidates}
    seen_ids = set()
    results = []
    for i in ranked_ids:
        # The rerank LLM occasionally repeats a movie_id in its output --
        # de-dupe while preserving its ranking order.
        if i in by_id and i not in seen_ids:
            seen_ids.add(i)
            results.append(by_id[i])
    results = results[:k_final]

    if results:
        top = results[0]
        why = _invoke_or_none(explain_chain, {
            "query": query, "title": top["title"], "genres": top["genres"],
            "overview": top.get("overview") or "not available",
        })
        if why:
            results[0] = {**top, "why": why}
    return results


def explain_recommendation(movie_id: int, query: str = "this recommendation"):
    """Grounded 'Why this?' explanation for one movie, used by
    GET /explain/{movie_id}."""
    meta = recommender.movie_meta(movie_id)
    if meta is None:
        return None
    if not LLM_AVAILABLE:
        return f"{meta['title']} matches your request based on genre similarity: {meta['genres']}."
    explanation = _invoke_or_none(explain_chain, {
        "query": query, "title": meta["title"], "genres": meta["genres"],
        "overview": meta.get("overview") or "not available",
    })
    if explanation:
        return explanation
    return f"{meta['title']} matches your request based on genre similarity: {meta['genres']}."


def onboard_new_user(answers: str, k: int = 10):
    """Cold-start path: free-text answers -> taste summary -> content-based
    seed recommendations. No rating history required."""
    if not LLM_AVAILABLE:
        return recommender.retrieve_candidates(answers, k=k)
    taste_summary = _invoke_or_none(onboarding_chain, {"answers": answers})
    if not taste_summary:
        taste_summary = answers
    return recommender.retrieve_candidates(taste_summary, k=k)
