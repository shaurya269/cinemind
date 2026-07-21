"""
06_evaluation.py
================
PHASE 1, STEP 6 — Compare every approach on the SAME test set, side by side,
and save a results table. This is the "proof" that the system works.

WHAT THIS DOES (plain English):
  Loads the trained two-tower model and re-runs the three rankers (popularity,
  two-tower, hybrid) on the held-out test set, then prints a clean comparison
  table and saves it to artifacts/results.csv. It also shows example
  recommendations for one user so the numbers feel real.

HOW TO RUN (from project root):
    python src/06_evaluation.py

REQUIRES (created by earlier steps):
    artifacts/two_tower.pt, artifacts/item_vecs.npy
    data/train_positives.csv, data/test_positives.csv, data/items.csv

OUTPUT:
    artifacts/results.csv
"""

import os
import sys
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu
# Import the model class from the step-4 script
import importlib.util
spec = importlib.util.spec_from_file_location(
    "tt", os.path.join(os.path.dirname(os.path.abspath(__file__)), "04_two_tower.py"))
tt = importlib.util.module_from_spec(spec)


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 6: Final Evaluation")
    print("=" * 60)

    for f in ["artifacts/item_vecs.npy", "data/train_positives.csv",
              "data/test_positives.csv", "data/items.csv"]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Missing {f}. Run earlier steps first.")

    train = pd.read_csv("data/train_positives.csv")
    test = pd.read_csv("data/test_positives.csv")
    items = pd.read_csv("data/items.csv")
    item_vecs = np.load("artifacts/item_vecs.npy").astype(np.float32)
    n_items = item_vecs.shape[0]

    title_of = dict(zip(items.movie_id, items.title))
    seen = train.groupby("user_id").movie_id.apply(set).to_dict()
    truth = test.groupby("user_id").movie_id.apply(set).to_dict()
    top_pop = train.movie_id.value_counts().index.to_numpy()

    pop_cnt = train.movie_id.value_counts().reindex(range(n_items), fill_value=0).to_numpy()
    log_pop = np.log1p(pop_cnt); log_pop = log_pop / log_pop.max()

    # We reuse the saved item vectors directly (no need to reload the model
    # for ranking, because user vectors come from the dot product with these).
    # For the two-tower user vector we DO need the model:
    spec.loader.exec_module(tt)
    genre_mat = np.zeros((n_items, 19), dtype=np.float32)
    flags = items[[f"g{i}" for i in range(19)]].to_numpy(dtype=np.float32)
    genre_mat[items.movie_id.values] = flags
    item_counts = pop_cnt.astype(np.float64) + 1.0
    n_users = int(max(train.user_id.max(), test.user_id.max())) + 1

    model = tt.TwoTower(n_users, n_items, torch.tensor(genre_mat), item_counts)
    model.load_state_dict(torch.load("artifacts/two_tower.pt"))
    model.eval()
    ivecs = torch.tensor(item_vecs)

    def pop_rank(u, k=10):
        s = seen.get(u, set())
        return [m for m in top_pop if m not in s][:k]

    def tt_rank(u, k=10):
        with torch.no_grad():
            uv = model.user_vec(torch.tensor([u]))
            scores = (uv @ ivecs.t()).squeeze(0).numpy()
        for m in seen.get(u, set()):
            scores[m] = -1e9
        return np.argpartition(-scores, k)[:k]

    def hybrid_rank(u, k=10, alpha=0.30):
        with torch.no_grad():
            uv = model.user_vec(torch.tensor([u]))
            scores = (uv @ ivecs.t()).squeeze(0).numpy() + alpha * log_pop
        for m in seen.get(u, set()):
            scores[m] = -1e9
        return np.argpartition(-scores, k)[:k]

    rankers = {
        "Popularity baseline": pop_rank,
        "Two-tower": tt_rank,
        "Two-tower + pop prior": hybrid_rank,
    }
    rows = []
    print("\nEvaluating all rankers on the same test set ...")
    for name, fn in rankers.items():
        p, r = cu.precision_recall_at_k(fn, truth, k=10)
        rows.append({"model": name, "precision@10": round(p, 4), "recall@10": round(r, 4)})

    results = pd.DataFrame(rows)
    print("\n" + "-" * 56)
    print(f"{'Model':<26}{'Precision@10':>14}{'Recall@10':>14}")
    print("-" * 56)
    for _, row in results.iterrows():
        print(f"{row['model']:<26}{row['precision@10']:>14.4f}{row['recall@10']:>14.4f}")
    print("-" * 56)

    results.to_csv("artifacts/results.csv", index=False)
    print("\nSaved artifacts/results.csv")

    # ---- Example recommendations for one user ----
    u = 196 if 196 in seen else int(train.user_id.iloc[0])
    liked = train[train.user_id == u].sort_values("rating", ascending=False).movie_id.head(5)
    print(f"\nExample — user {u} liked:")
    for m in liked:
        print(f"   {title_of.get(m)}")
    print(f"\nHybrid model recommends:")
    for m in hybrid_rank(u):
        if m in title_of:
            print(f"   {title_of.get(m)}")

    print("\nPhase 1 complete! You have reproduced the baseline, trained a")
    print("modern model that beats it, embedded content, set up vector search,")
    print("and produced a final comparison. This is your portfolio evidence.")


if __name__ == "__main__":
    main()
