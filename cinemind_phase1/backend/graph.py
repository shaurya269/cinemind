"""
graph.py
========
PHASE 2 — Neo4j graph queries for graph-powered explanations.

Wraps the graph built by src/08_neo4j_graph.py (User-RATED->Movie,
Movie-HAS_GENRE->Genre) behind one function used by GET /graph/insights:

    graph_insights(movie_id, k=5)

This answers a genuinely different question than the vector stores do:
Qdrant/two-tower find movies numerically close to a vector; this finds
movies connected through actual OTHER USERS' behaviour (collaborative
graph traversal) and shared genre structure -- e.g. "943 other users who
rated this movie highly also rated these movies highly", which is a direct
graph fact, not a similarity score.

Degrades gracefully like every other optional store in this codebase: if
Neo4j isn't reachable, GRAPH_AVAILABLE is False and callers get None instead
of a crash.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "cinemind123")

_driver = None
GRAPH_AVAILABLE = False


def load():
    """Connect to Neo4j. Idempotent -- safe to call from FastAPI's startup
    event and again elsewhere; a failed connection just leaves
    GRAPH_AVAILABLE False rather than raising."""
    global _driver, GRAPH_AVAILABLE
    if _driver is not None:
        return
    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _driver.verify_connectivity()
        GRAPH_AVAILABLE = True
    except Exception:
        _driver = None
        GRAPH_AVAILABLE = False


def graph_insights(movie_id: int, k: int = 5):
    """Graph-derived context for one movie, or None if Neo4j isn't
    reachable or the movie isn't in the graph yet.

    Returns:
        {
          "total_raters": int,           -- how many users rated this movie at all
          "also_liked_by_raters": [...], -- movies other raters of this one also rated highly,
                                             ranked by how many raters they share
          "shared_genre_movies": [...],  -- movies sharing the most genres with this one
        }
    """
    if not GRAPH_AVAILABLE:
        load()
    if not GRAPH_AVAILABLE:
        return None

    with _driver.session() as session:
        total_raters = session.run(
            "MATCH (:Movie {movie_id: $movie_id})<-[:RATED]-(u:User) RETURN count(u) AS n",
            movie_id=movie_id,
        ).single()
        if total_raters is None or total_raters["n"] == 0:
            return None

        also_liked = session.run(
            """
            MATCH (m:Movie {movie_id: $movie_id})<-[r:RATED]-(u:User)
            WHERE r.rating >= 4
            MATCH (u)-[r2:RATED]->(other:Movie)
            WHERE other.movie_id <> $movie_id AND r2.rating >= 4
            WITH other, count(DISTINCT u) AS co_raters
            ORDER BY co_raters DESC
            LIMIT $k
            RETURN other.movie_id AS movie_id, other.title AS title, co_raters
            """,
            movie_id=movie_id, k=k,
        )
        also_liked_rows = [dict(r) for r in also_liked]

        shared_genre = session.run(
            """
            MATCH (m:Movie {movie_id: $movie_id})-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(other:Movie)
            WHERE other.movie_id <> $movie_id
            WITH other, count(DISTINCT g) AS shared_genres
            ORDER BY shared_genres DESC
            LIMIT $k
            RETURN other.movie_id AS movie_id, other.title AS title, shared_genres
            """,
            movie_id=movie_id, k=k,
        )
        shared_genre_rows = [dict(r) for r in shared_genre]

    return {
        "total_raters": total_raters["n"],
        "also_liked_by_raters": also_liked_rows,
        "shared_genre_movies": shared_genre_rows,
    }
