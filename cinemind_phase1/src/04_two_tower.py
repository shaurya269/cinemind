"""
04_two_tower.py
===============
PHASE 1, STEP 4 — Train the modern Two-Tower neural network (the centrepiece).
This is the model that replaces the RBM and produces the vectors the rest of
the system searches.

WHAT A TWO-TOWER MODEL IS (plain English):
  Two small neural networks ("towers"). The USER tower turns a user into a
  64-number vector. The ITEM tower turns a movie into a 64-number vector.
  Training makes the vectors of a user and a movie they LIKED point in a
  similar direction (high dot product). To recommend, we compute the user's
  vector and find the movie vectors closest to it.

KEY TRICK — logQ correction:
  With "in-batch negatives", popular movies appear so often they get used as
  negatives constantly, and the model wrongly learns to PENALISE popularity.
  We subtract log(P(item)) from each score during training to cancel this.
  Without it, the model LOSES to the popularity baseline.

HOW TO RUN (from project root):
    python src/04_two_tower.py

REQUIRES (created by step 1):
    data/train_positives.csv, data/test_positives.csv, data/items.csv

OUTPUT (saved to artifacts/):
    artifacts/two_tower.pt    <- trained model weights
    artifacts/item_vecs.npy   <- one 64-number vector per movie
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu

torch.manual_seed(42)
np.random.seed(42)


class Tower(nn.Module):
    """A small 2-layer network that outputs a unit-length vector."""
    def __init__(self, in_dim, out_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 128), nn.ReLU(), nn.Linear(128, out_dim)
        )

    def forward(self, x):
        return F.normalize(self.net(x), dim=-1)   # unit length -> dot = cosine


class TwoTower(nn.Module):
    def __init__(self, n_users, n_items, genre_t, item_counts, id_dim=64, out_dim=64):
        super().__init__()
        self.user_emb = nn.Embedding(n_users, id_dim)
        self.item_emb = nn.Embedding(n_items, id_dim)
        self.user_tower = Tower(id_dim, out_dim)
        self.item_tower = Tower(id_dim + 19, out_dim)   # ID + 19 genre flags
        self.temp = 0.07                                 # softmax temperature
        self.register_buffer("genre_t", genre_t)
        # logQ correction term: log of each item's training frequency
        logq = torch.log(torch.tensor(item_counts / item_counts.sum() + 1e-9))
        self.register_buffer("logq", logq.float())

    def user_vec(self, u):
        return self.user_tower(self.user_emb(u))

    def item_vec(self, i):
        return self.item_tower(torch.cat([self.item_emb(i), self.genre_t[i]], dim=-1))

    def forward(self, u, i):
        uv, iv = self.user_vec(u), self.item_vec(i)
        logits = uv @ iv.t() / self.temp     # [B,B] similarity matrix
        logits = logits - self.logq[i]       # logQ correction
        labels = torch.arange(len(u))        # the diagonal = true pairs
        return F.cross_entropy(logits, labels)


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 4: Two-Tower Model")
    print("=" * 60)

    cu.ensure_dirs()
    for f in ["data/train_positives.csv", "data/test_positives.csv", "data/items.csv"]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Missing {f}. Run step 1 first.")

    train = pd.read_csv("data/train_positives.csv")
    test = pd.read_csv("data/test_positives.csv")
    items = pd.read_csv("data/items.csv")

    n_items = int(max(train.movie_id.max(), test.movie_id.max(), items.movie_id.max())) + 1
    n_users = int(max(train.user_id.max(), test.user_id.max())) + 1

    # Genre matrix (item features)
    genre_mat = np.zeros((n_items, 19), dtype=np.float32)
    flags = items[[f"g{i}" for i in range(19)]].to_numpy(dtype=np.float32)
    genre_mat[items.movie_id.values] = flags
    genre_t = torch.tensor(genre_mat)

    # Item popularity counts (for logQ correction)
    item_counts = np.bincount(train.movie_id.values, minlength=n_items).astype(np.float64) + 1.0

    train_u = torch.tensor(train.user_id.values)
    train_i = torch.tensor(train.movie_id.values)

    model = TwoTower(n_users, n_items, genre_t, item_counts)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    # ---- Train ----
    print(f"\nTraining on {len(train):,} positive interactions ...")
    B = 512
    idx = np.arange(len(train))
    for epoch in range(60):
        np.random.shuffle(idx)
        total = 0.0
        for s in range(0, len(idx) - B, B):
            b = idx[s:s + B]
            loss = model(train_u[b], train_i[b])
            opt.zero_grad(); loss.backward(); opt.step()
            total += loss.item()
        if (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch+1:3d}  loss {total/(len(idx)//B):.4f}")

    # ---- Evaluate ----
    model.eval()
    with torch.no_grad():
        item_vecs = model.item_vec(torch.arange(n_items))    # precompute, like production
        seen = train.groupby("user_id").movie_id.apply(set).to_dict()
        truth = test.groupby("user_id").movie_id.apply(set).to_dict()
        top_pop = train.movie_id.value_counts().index.to_numpy()

        pop_cnt = train.movie_id.value_counts().reindex(range(n_items), fill_value=0).to_numpy()
        log_pop = np.log1p(pop_cnt); log_pop = log_pop / log_pop.max()

        def pop_rank(u, k=10):
            s = seen.get(u, set())
            return [m for m in top_pop if m not in s][:k]

        def tt_rank(u, k=10):
            uv = model.user_vec(torch.tensor([u]))
            scores = (uv @ item_vecs.t()).squeeze(0).numpy()
            for m in seen.get(u, set()):
                scores[m] = -1e9
            return np.argpartition(-scores, k)[:k]

        def hybrid_rank(u, k=10, alpha=0.30):
            uv = model.user_vec(torch.tensor([u]))
            scores = (uv @ item_vecs.t()).squeeze(0).numpy() + alpha * log_pop
            for m in seen.get(u, set()):
                scores[m] = -1e9
            return np.argpartition(-scores, k)[:k]

        p_pop, r_pop = cu.precision_recall_at_k(pop_rank, truth)
        p_tt, r_tt = cu.precision_recall_at_k(tt_rank, truth)
        p_hy, r_hy = cu.precision_recall_at_k(hybrid_rank, truth)

    print("\n" + "-" * 56)
    print(f"{'Model':<26}{'Precision@10':>14}{'Recall@10':>14}")
    print("-" * 56)
    print(f"{'Popularity baseline':<26}{p_pop:>14.4f}{r_pop:>14.4f}")
    print(f"{'Two-tower':<26}{p_tt:>14.4f}{r_tt:>14.4f}")
    print(f"{'Two-tower + pop prior':<26}{p_hy:>14.4f}{r_hy:>14.4f}")
    print("-" * 56)

    # ---- Save ----
    torch.save(model.state_dict(), os.path.join(cu.ARTIFACT_DIR, "two_tower.pt"))
    np.save(os.path.join(cu.ARTIFACT_DIR, "item_vecs.npy"), item_vecs.numpy())
    print(f"\nSaved artifacts/two_tower.pt and artifacts/item_vecs.npy")
    print("Step 4 complete. Next: python src/05_qdrant_indexing.py")


if __name__ == "__main__":
    main()
