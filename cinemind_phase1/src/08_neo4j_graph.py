"""
08_neo4j_graph.py
==================
Loads the ratings + genre data into Neo4j as a graph, closing the Neo4j gap
called out in CLAUDE.md's data layer (previously "later phase", never built).

WHY A GRAPH (plain English):
  The two-tower model and Qdrant answer "which movies are numerically close
  to this user/movie". A graph answers a *different* kind of question well:
  "which other USERS also liked this movie, and what else did THEY like" --
  a direct traversal, not a vector comparison. That's what backend/graph.py's
  graph_insights() uses this data for (see GET /graph/insights/{movie_id}).

SCHEMA:
    (:User {user_id})
    (:Movie {movie_id, title})
    (:Genre {name})
    (User)-[:RATED {rating, timestamp}]->(Movie)
    (Movie)-[:HAS_GENRE]->(Genre)

REQUIRES:
    data/train_positives.csv, data/test_positives.csv, data/items.csv
    (created by step 1). A running Neo4j instance -- see
    backend/docker-compose.yml (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD in .env,
    defaults match the docker-compose service).

HOW TO RUN (from project root, with Neo4j running):
    docker compose --env-file .env -f backend/docker-compose.yml up -d neo4j
    python src/08_neo4j_graph.py

Idempotent: uses MERGE throughout, so re-running clears and reloads
relationships without creating duplicate nodes/edges.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "cinemind123")
BATCH_SIZE = 2000


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 8: Neo4j Graph Loading")
    print("=" * 60)

    for f in ["data/train_positives.csv", "data/test_positives.csv", "data/items.csv"]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Missing {f}. Run step 1 first: python src/01_data_exploration.py")

    from neo4j import GraphDatabase

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        raise SystemExit(
            f"Could not connect to Neo4j at {NEO4J_URI} ({type(e).__name__}: {e}).\n"
            "Start it with: docker compose --env-file .env -f backend/docker-compose.yml up -d neo4j"
        )
    print(f"Connected to Neo4j at {NEO4J_URI}.")

    train = pd.read_csv("data/train_positives.csv")
    test = pd.read_csv("data/test_positives.csv")
    ratings = pd.concat([train, test], ignore_index=True)
    items = pd.read_csv("data/items.csv")

    with driver.session() as session:
        print("\nCreating constraints (idempotent)...")
        session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
        session.run("CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE")
        session.run("CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE")

        print(f"Loading {len(items):,} movies + genres...")
        movie_rows = [
            {
                "movie_id": int(row.movie_id),
                "title": row.title,
                "genres": [g.strip(" '\"") for g in row.genres.strip("[]").split(",") if g.strip(" '\"")],
            }
            for row in items.itertuples(index=False)
        ]
        session.run(
            """
            UNWIND $rows AS row
            MERGE (m:Movie {movie_id: row.movie_id})
            SET m.title = row.title
            WITH m, row
            UNWIND row.genres AS genre_name
            MERGE (g:Genre {name: genre_name})
            MERGE (m)-[:HAS_GENRE]->(g)
            """,
            rows=movie_rows,
        )

        print(f"Loading {len(ratings):,} ratings (User-RATED->Movie)...")
        rating_rows = [
            {"user_id": int(r.user_id), "movie_id": int(r.movie_id),
             "rating": float(r.rating), "timestamp": int(r.timestamp)}
            for r in ratings.itertuples(index=False)
        ]
        for start in range(0, len(rating_rows), BATCH_SIZE):
            batch = rating_rows[start:start + BATCH_SIZE]
            session.run(
                """
                UNWIND $rows AS row
                MERGE (u:User {user_id: row.user_id})
                MERGE (m:Movie {movie_id: row.movie_id})
                MERGE (u)-[r:RATED]->(m)
                SET r.rating = row.rating, r.timestamp = row.timestamp
                """,
                rows=batch,
            )
            print(f"  {min(start + BATCH_SIZE, len(rating_rows)):,}/{len(rating_rows):,} ratings loaded")

        counts = session.run(
            "MATCH (u:User) WITH count(u) AS users "
            "MATCH (m:Movie) WITH users, count(m) AS movies "
            "MATCH ()-[r:RATED]->() WITH users, movies, count(r) AS rated "
            "MATCH (:Movie)-[hg:HAS_GENRE]->() "
            "RETURN users, movies, rated, count(hg) AS has_genre"
        ).single()
        print(f"\nGraph loaded: {counts['users']:,} User nodes, {counts['movies']:,} Movie nodes, "
              f"{counts['rated']:,} RATED edges, {counts['has_genre']:,} HAS_GENRE edges.")

    driver.close()
    print("\nStep 8 complete. backend/graph.py will use this automatically on next connect.")
    print("Browse the graph at http://localhost:7474 (user: neo4j, see NEO4J_PASSWORD in .env).")


if __name__ == "__main__":
    main()
