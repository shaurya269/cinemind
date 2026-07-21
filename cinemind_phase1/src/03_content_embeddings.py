"""
03_content_embeddings.py
========================
PHASE 1, STEP 3 — Turn each movie's text into a "content vector" using a
sentence-embedding model, then test semantic "movies like X" search.

WHAT THIS DOES (plain English):
  A content vector is a list of numbers describing what a movie is ABOUT
  (its title + genres). Movies with similar meaning get similar numbers, so
  we can find "movies like Toy Story" by looking for nearby vectors — even
  for a movie nobody has rated yet (this is how we solve item cold-start).

MODEL USED:
  intfloat/e5-small-v2  (a small, fast, free, open-source embedding model).
  We use the SMALL version so it runs quickly on a laptop CPU. The design doc
  mentions e5-large-v2 for production; small is perfect for learning.

HOW TO RUN (from project root):
    python src/03_content_embeddings.py

FIRST RUN downloads the model (~130 MB) automatically. Later runs are instant.

REQUIRES (created by step 1):
    data/items.csv

OUTPUT (saved to artifacts/):
    artifacts/content_vecs.npy        <- one content vector per movie
    artifacts/content_movie_ids.npy   <- which movie_id each row belongs to
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu


def build_movie_text(row):
    """Compose the text we feed to the embedding model for one movie."""
    title = row["title"]
    genres = row["genres"]
    if isinstance(genres, str):
        # items.csv stores the list as a string like "['Action', 'Sci-Fi']"
        genres = genres.strip("[]").replace("'", "")
    # The "passage:" prefix is what E5 models expect for documents.
    return f"passage: {title}. Genres: {genres}."


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 3: Content Embeddings (E5)")
    print("=" * 60)

    cu.ensure_dirs()
    if not os.path.exists("data/items.csv"):
        raise FileNotFoundError("Run step 1 first: python src/01_data_exploration.py")

    # Lazy import so the script gives a friendly message if not installed
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("\nERROR: sentence-transformers is not installed.")
        print("Install it with:  pip install sentence-transformers")
        sys.exit(1)

    items = pd.read_csv("data/items.csv")
    texts = items.apply(build_movie_text, axis=1).tolist()
    movie_ids = items.movie_id.to_numpy()

    print(f"\nLoading embedding model (first run downloads ~130 MB) ...")
    model = SentenceTransformer("intfloat/e5-small-v2")

    print(f"Embedding {len(texts):,} movies ...")
    vecs = model.encode(
        texts, batch_size=64, show_progress_bar=True,
        normalize_embeddings=True,   # unit length -> dot product = cosine sim
    )
    vecs = np.asarray(vecs, dtype=np.float32)
    print(f"Done. Each movie is now a {vecs.shape[1]}-number content vector.")

    # ---- Save ----
    np.save(os.path.join(cu.ARTIFACT_DIR, "content_vecs.npy"), vecs)
    np.save(os.path.join(cu.ARTIFACT_DIR, "content_movie_ids.npy"), movie_ids)
    print(f"\nSaved artifacts/content_vecs.npy  shape={vecs.shape}")

    # ---- Demo: semantic 'movies like X' search ----
    title_of = dict(zip(items.movie_id, items.title))
    id_to_row = {mid: i for i, mid in enumerate(movie_ids)}

    def similar(movie_id, k=5):
        qi = id_to_row[movie_id]
        sims = vecs @ vecs[qi]            # cosine similarity to all movies
        order = np.argsort(-sims)
        out = [movie_ids[j] for j in order if movie_ids[j] != movie_id][:k]
        return out

    # Pick a well-known movie to demo (Toy Story = movie_id 1)
    demo_id = 1 if 1 in id_to_row else int(movie_ids[0])
    print(f"\nDemo — movies most similar to '{title_of.get(demo_id)}':")
    for mid in similar(demo_id, k=5):
        print(f"   {title_of.get(mid)}")

    print("\nNotice these are matched purely by TITLE + GENRE text — no ratings.")
    print("That is exactly why a brand-new movie can still be recommended.")
    print("Step 3 complete. Next: python src/04_two_tower.py")


if __name__ == "__main__":
    main()
