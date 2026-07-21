"""
cinemind_utils.py
=================
Shared helpers used by every Phase 1 script.

Keeping data-loading and the train/test split in ONE place means every
notebook trains and evaluates on EXACTLY the same data — which is what makes
the model comparisons in 06_evaluation fair.

Nothing in here trains a model. It only loads, cleans, and splits data.
"""

import os
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------------
# All scripts assume they are run from the project root (cinemind_phase1/).
# DATA_DIR points to the MovieLens 100K folder you downloaded.
# If your folder is somewhere else, change ONE line here and every script
# picks it up.
# ----------------------------------------------------------------------
DATA_DIR = os.environ.get("CINEMIND_DATA", "data/ml-100k")
ARTIFACT_DIR = "artifacts"   # where trained models + vectors are saved

# 19 MovieLens genre names, in the exact order of the binary flag columns
# inside u.item. Do not reorder these.
GENRES = [
    "unknown", "Action", "Adventure", "Animation", "Children's", "Comedy",
    "Crime", "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror",
    "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western",
]


def ensure_dirs():
    """Create the artifacts/ folder if it does not exist."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)


def load_ratings():
    """Load u.data -> DataFrame[user_id, movie_id, rating, timestamp]."""
    path = os.path.join(DATA_DIR, "u.data")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find {path}.\n"
            f"Download MovieLens 100K and place the ml-100k folder at: {DATA_DIR}\n"
            f"See SETUP_GUIDE.md section 'Downloading the data'."
        )
    return pd.read_csv(
        path, sep="\t",
        names=["user_id", "movie_id", "rating", "timestamp"],
    )


def load_items():
    """Load u.item -> DataFrame with movie_id, title, genre flags g0..g18."""
    path = os.path.join(DATA_DIR, "u.item")
    cols = ["movie_id", "title", "release", "video", "url"] + [f"g{i}" for i in range(19)]
    items = pd.read_csv(path, sep="|", encoding="latin-1", names=cols)
    # Human-readable list of genres per movie (handy for printing recs)
    items["genres"] = items[[f"g{i}" for i in range(19)]].apply(
        lambda row: [GENRES[i] for i, v in enumerate(row) if v == 1], axis=1
    )
    return items


def load_users():
    """Load u.user -> DataFrame[user_id, age, gender, occupation, zip]."""
    path = os.path.join(DATA_DIR, "u.user")
    return pd.read_csv(
        path, sep="|",
        names=["user_id", "age", "gender", "occupation", "zip"],
    )


def genre_matrix(items, n_items):
    """Return an (n_items x 19) float32 array of genre flags, indexed by movie_id."""
    g = np.zeros((n_items, 19), dtype=np.float32)
    flags = items[[f"g{i}" for i in range(19)]].to_numpy(dtype=np.float32)
    g[items.movie_id.values] = flags
    return g


def temporal_split(ratings, threshold=4, test_frac=0.2):
    """
    Convert ratings to implicit positives and split by TIME, per user.

    Why time-based and not random?
      A recommender predicts the FUTURE. If we randomly shuffled, the model
      could "see" a movie the user rated AFTER some test movies — peeking at
      the future and giving fake-good scores. So for each user we sort by
      timestamp and put their most recent `test_frac` interactions in test.

    Returns (train_df, test_df) of positive interactions only.
    """
    pos = ratings[ratings.rating >= threshold].copy()
    pos = pos.sort_values(["user_id", "timestamp"])
    pos["rank_pct"] = (
        pos.groupby("user_id").cumcount()
        / pos.groupby("user_id")["timestamp"].transform("count")
    )
    train = pos[pos.rank_pct < (1 - test_frac)].copy()
    test = pos[pos.rank_pct >= (1 - test_frac)].copy()
    return train, test


def precision_recall_at_k(rank_fn, truth, k=10):
    """
    Evaluate a ranking function.

    rank_fn(user_id) -> list/array of k recommended movie_ids
    truth: dict {user_id: set(movie_ids they liked in the test set)}

    Returns (precision@k, recall@k) averaged over all users.
    """
    P, R = [], []
    for u, liked in truth.items():
        recs = set(rank_fn(u))
        hits = len(recs & liked)
        P.append(hits / k)
        R.append(hits / len(liked) if liked else 0.0)
    return float(np.mean(P)), float(np.mean(R))


if __name__ == "__main__":
    # Quick self-test: prints dataset stats so you can confirm paths work.
    r = load_ratings()
    it = load_items()
    print(f"Ratings: {len(r):,}")
    print(f"Movies:  {len(it):,}")
    tr, te = temporal_split(r)
    print(f"Train positives: {len(tr):,}  Test positives: {len(te):,}")
    print("cinemind_utils OK")
