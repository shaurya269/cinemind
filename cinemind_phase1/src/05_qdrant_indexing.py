"""
05_qdrant_indexing.py
=====================
PHASE 1, STEP 5 — Load the trained vectors into Qdrant (a vector database) and
test fast Approximate Nearest Neighbour (ANN) search.

WHAT THIS DOES (plain English):
  Step 4 produced one 64-number vector per movie. Searching them with plain
  numpy is fine for 1,682 movies but slow for millions. Qdrant stores vectors
  and finds the nearest ones in milliseconds using an index called HNSW. This
  is the search engine the live recommendation API will use.

THIS SCRIPT RUNS IN TWO MODES (it auto-detects):
  A) If a Qdrant server is reachable on localhost:6333  -> uses the real DB.
  B) Otherwise -> falls back to numpy search so you can still learn the flow.

TO RUN THE REAL QDRANT (recommended), start it first with Docker:
    docker run -p 6333:6333 qdrant/qdrant
  then in another terminal:
    python src/05_qdrant_indexing.py

REQUIRES (created by step 4):
    artifacts/item_vecs.npy
    data/items.csv
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu

COLLECTION = "collab_vectors"


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 5: Qdrant Indexing + ANN Search")
    print("=" * 60)

    if not os.path.exists("artifacts/item_vecs.npy"):
        raise FileNotFoundError("Run step 4 first: python src/04_two_tower.py")

    item_vecs = np.load("artifacts/item_vecs.npy").astype(np.float32)
    items = pd.read_csv("data/items.csv")
    title_of = dict(zip(items.movie_id, items.title))
    dim = item_vecs.shape[1]
    n = item_vecs.shape[0]
    print(f"\nLoaded {n:,} movie vectors of dimension {dim}.")

    # ---- Try to connect to a real Qdrant server ----
    use_qdrant = False
    client = None
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        client = QdrantClient(host="localhost", port=6333, timeout=3)
        client.get_collections()          # ping
        use_qdrant = True
        print("Connected to Qdrant on localhost:6333.")
    except Exception as e:
        print(f"\nNo Qdrant server reachable ({type(e).__name__}).")
        print("Falling back to numpy search. To use the real database:")
        print("  docker run -p 6333:6333 qdrant/qdrant")

    if use_qdrant:
        # ---- Create collection and upload vectors ----
        client.recreate_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        points = [
            PointStruct(id=int(mid), vector=item_vecs[mid].tolist())
            for mid in range(n)
        ]
        # Upload in batches of 500
        for s in range(0, len(points), 500):
            client.upsert(collection_name=COLLECTION, points=points[s:s+500])
        print(f"Uploaded {n:,} vectors to Qdrant collection '{COLLECTION}'.")

        def search(query_vec, k=5):
            hits = client.query_points(
                collection_name=COLLECTION,
                query=query_vec.tolist(), limit=k + 1,
            ).points
            return [(h.id, h.score) for h in hits]
    else:
        def search(query_vec, k=5):
            sims = item_vecs @ query_vec
            order = np.argsort(-sims)[:k + 1]
            return [(int(j), float(sims[j])) for j in order]

    # ---- Demo: nearest movies to a chosen movie ----
    demo_id = 50 if 50 < n else 1        # 50 = Star Wars in MovieLens 100K
    print(f"\nMovies nearest to '{title_of.get(demo_id)}' in taste space:")
    for mid, score in search(item_vecs[demo_id], k=5):
        if mid == demo_id:
            continue
        print(f"   {score:.3f}  {title_of.get(mid)}")

    print("\nThese neighbours are by COLLABORATIVE taste (who likes them together),")
    print("which is different from step 3's CONTENT similarity (what they're about).")
    print("Step 5 complete. Next: python src/06_evaluation.py")


if __name__ == "__main__":
    main()
