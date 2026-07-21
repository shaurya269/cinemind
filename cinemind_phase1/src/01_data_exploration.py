"""
01_data_exploration.py
=======================
PHASE 1, STEP 1 — Understand the data before training anything.

This script LOADS the MovieLens 100K data, prints key statistics, draws a few
plots, and SAVES cleaned train/test CSV files that every later script uses.

It does NOT train any model.

HOW TO RUN (from the project root, cinemind_phase1/):
    python src/01_data_exploration.py

OUTPUT (saved to data/):
    data/train_positives.csv   <- used by 02, 04, 06
    data/test_positives.csv    <- used by 02, 04, 06
    data/items.csv             <- used by 03, 04, 06
Plots are saved to artifacts/eda_*.png so you can view them in VS Code.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # save plots to file instead of opening a window
import matplotlib.pyplot as plt

# Make sure we can import the shared utils whether run from root or src/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu


def main():
    cu.ensure_dirs()
    print("=" * 60)
    print("CineMind Phase 1 — Step 1: Data Exploration")
    print("=" * 60)

    # ---- 1. Load ----
    ratings = cu.load_ratings()
    items = cu.load_items()
    users = cu.load_users()
    n_users = ratings.user_id.max()
    n_movies = ratings.movie_id.max()

    print(f"\nRatings : {len(ratings):,}")
    print(f"Users   : {n_users:,}")
    print(f"Movies  : {n_movies:,}")

    # ---- 2. Sparsity ----
    sparsity = 1 - len(ratings) / (n_users * n_movies)
    print(f"\nSparsity: {sparsity*100:.2f}%  "
          f"(only {(1-sparsity)*100:.2f}% of the user x movie table is filled)")

    # ---- 3. Rating distribution ----
    dist = ratings.rating.value_counts().sort_index()
    print("\nRating distribution:")
    for star, cnt in dist.items():
        print(f"  {star} star: {cnt:,} ({cnt/len(ratings)*100:.1f}%)")

    pos = (ratings.rating >= 4).sum()
    print(f"\nPositives (rating >= 4): {pos:,} ({pos/len(ratings)*100:.1f}%)")
    print("These rating>=4 interactions are what the model learns from.")

    # ---- 4. Plots ----
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    # Rating distribution
    axes[0, 0].bar(dist.index, dist.values,
                   color=["#c0392b", "#e67e22", "#f1c40f", "#2ecc71", "#27ae60"])
    axes[0, 0].set_title("Rating distribution")
    axes[0, 0].set_xlabel("Stars"); axes[0, 0].set_ylabel("Count")

    # Ratings per movie (long tail)
    movie_counts = ratings.groupby("movie_id").size().sort_values(ascending=False)
    axes[0, 1].plot(range(1, len(movie_counts) + 1), movie_counts.values)
    axes[0, 1].set_yscale("log"); axes[0, 1].set_xscale("log")
    axes[0, 1].set_title("Long tail: popularity per movie (log-log)")
    axes[0, 1].set_xlabel("Movie rank"); axes[0, 1].set_ylabel("Ratings")

    # Ratings per user
    user_counts = ratings.groupby("user_id").size()
    axes[1, 0].hist(user_counts.values, bins=40, color="mediumorchid")
    axes[1, 0].set_title("Ratings per user")
    axes[1, 0].set_xlabel("Ratings"); axes[1, 0].set_ylabel("Users")

    # Genre counts
    genre_counts = {cu.GENRES[i]: int(items[f"g{i}"].sum())
                    for i in range(19) if cu.GENRES[i] != "unknown"}
    genre_counts = dict(sorted(genre_counts.items(), key=lambda x: -x[1]))
    axes[1, 1].barh(list(genre_counts.keys())[:10],
                    list(genre_counts.values())[:10], color="steelblue")
    axes[1, 1].invert_yaxis()
    axes[1, 1].set_title("Top 10 genres")

    plt.tight_layout()
    plot_path = os.path.join(cu.ARTIFACT_DIR, "eda_overview.png")
    plt.savefig(plot_path, dpi=120)
    print(f"\nSaved plots to {plot_path}")

    # ---- 5. Cold-start reality check ----
    cold_movies = (movie_counts <= 5).sum()
    print(f"\nMovies with <=5 ratings: {cold_movies} "
          f"({cold_movies/n_movies*100:.1f}%)  <- the item cold-start problem")

    # ---- 6. Temporal split + SAVE ----
    train, test = cu.temporal_split(ratings)
    train.to_csv("data/train_positives.csv", index=False)
    test.to_csv("data/test_positives.csv", index=False)
    items.to_csv("data/items.csv", index=False)

    print(f"\nSaved:")
    print(f"  data/train_positives.csv  ({len(train):,} rows)")
    print(f"  data/test_positives.csv   ({len(test):,} rows)")
    print(f"  data/items.csv            ({len(items):,} rows)")
    print("\nStep 1 complete. Next: python src/02_rbm_baseline.py")


if __name__ == "__main__":
    main()
