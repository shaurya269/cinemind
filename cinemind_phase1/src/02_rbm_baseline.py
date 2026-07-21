"""
02_rbm_baseline.py
==================
PHASE 1, STEP 2 — Reproduce the reference repo's Restricted Boltzmann Machine
and measure its Precision@10 / Recall@10.

This gives us the BASELINE that our modern two-tower model (step 4) must beat.

WHAT AN RBM IS (plain English):
  Two layers of "neurons". The visible layer has one neuron per movie (on if
  the user liked it). The hidden layer has taste-detector neurons the model
  invents on its own. Training nudges the connection weights so the model can
  reconstruct a user's likes from the hidden tastes. To recommend, we feed in
  a user's known likes and read off which UNSEEN movies light up.

HOW TO RUN (from project root):
    python src/02_rbm_baseline.py

REQUIRES (created by step 1):
    data/train_positives.csv
    data/test_positives.csv

OUTPUT:
    Prints Precision@10 / Recall@10 for the RBM and a popularity baseline.
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cinemind_utils as cu

torch.manual_seed(42)
np.random.seed(42)


class RBM:
    """A minimal Restricted Boltzmann Machine for collaborative filtering."""

    def __init__(self, n_visible, n_hidden=100, lr=0.1):
        self.n_visible = n_visible
        self.n_hidden = n_hidden
        self.lr = lr
        # Weights connect every movie to every hidden taste unit
        self.W = torch.randn(n_visible, n_hidden) * 0.01
        self.v_bias = torch.zeros(n_visible)
        self.h_bias = torch.zeros(n_hidden)

    def sample_h(self, v):
        """Given visible (movies), compute hidden taste activations."""
        prob_h = torch.sigmoid(v @ self.W + self.h_bias)
        return prob_h, torch.bernoulli(prob_h)

    def sample_v(self, h):
        """Given hidden tastes, reconstruct the visible (movie) layer."""
        prob_v = torch.sigmoid(h @ self.W.t() + self.v_bias)
        return prob_v, torch.bernoulli(prob_v)

    def train(self, data, epochs=15, batch_size=64):
        """Contrastive Divergence (CD-1) training."""
        n = data.shape[0]
        for epoch in range(epochs):
            err = 0.0
            perm = torch.randperm(n)
            for i in range(0, n - batch_size, batch_size):
                v0 = data[perm[i:i + batch_size]]
                ph0, h0 = self.sample_h(v0)        # positive phase
                pv1, v1 = self.sample_v(h0)         # reconstruct
                ph1, _ = self.sample_h(v1)          # negative phase
                # Update weights toward data, away from reconstruction
                self.W += self.lr * (v0.t() @ ph0 - v1.t() @ ph1) / batch_size
                self.v_bias += self.lr * (v0 - v1).mean(0)
                self.h_bias += self.lr * (ph0 - ph1).mean(0)
                err += (v0 - v1).pow(2).mean().item()
            if (epoch + 1) % 5 == 0:
                print(f"  epoch {epoch+1:2d}  reconstruction error {err/(n//batch_size):.4f}")

    def recommend_scores(self, v):
        """One Gibbs step -> reconstruction probabilities = recommendation scores."""
        ph, _ = self.sample_h(v)
        pv, _ = self.sample_v(ph)
        return pv


def main():
    print("=" * 60)
    print("CineMind Phase 1 — Step 2: RBM Baseline")
    print("=" * 60)

    # ---- Load the SAME split step 1 produced ----
    if not os.path.exists("data/train_positives.csv"):
        raise FileNotFoundError("Run step 1 first: python src/01_data_exploration.py")
    train = pd.read_csv("data/train_positives.csv")
    test = pd.read_csv("data/test_positives.csv")

    n_items = int(max(train.movie_id.max(), test.movie_id.max())) + 1
    n_users = int(max(train.user_id.max(), test.user_id.max())) + 1

    # ---- Build the user x movie binary matrix (1 if liked in train) ----
    matrix = torch.zeros(n_users, n_items)
    for u, m in zip(train.user_id.values, train.movie_id.values):
        matrix[u, m] = 1.0

    print(f"\nTraining RBM on {n_users} users x {n_items} movies ...")
    rbm = RBM(n_visible=n_items, n_hidden=100, lr=0.1)
    rbm.train(matrix, epochs=15, batch_size=64)

    # ---- Build evaluation truth + seen sets ----
    seen = train.groupby("user_id").movie_id.apply(set).to_dict()
    truth = test.groupby("user_id").movie_id.apply(set).to_dict()
    top_pop = train.movie_id.value_counts().index.to_numpy()

    # ---- RBM ranking function ----
    def rbm_rank(u, k=10):
        v = matrix[u].unsqueeze(0)
        scores = rbm.recommend_scores(v).squeeze(0).numpy()
        for m in seen.get(u, set()):
            scores[m] = -1e9          # never re-recommend a seen movie
        return np.argpartition(-scores, k)[:k]

    # ---- Popularity baseline ----
    def pop_rank(u, k=10):
        s = seen.get(u, set())
        return [m for m in top_pop if m not in s][:k]

    print("\nEvaluating (this scores every test user) ...")
    p_pop, r_pop = cu.precision_recall_at_k(pop_rank, truth, k=10)
    p_rbm, r_rbm = cu.precision_recall_at_k(rbm_rank, truth, k=10)

    print("\n" + "-" * 50)
    print(f"{'Model':<22}{'Precision@10':>14}{'Recall@10':>14}")
    print("-" * 50)
    print(f"{'Popularity baseline':<22}{p_pop:>14.4f}{r_pop:>14.4f}")
    print(f"{'RBM':<22}{p_rbm:>14.4f}{r_rbm:>14.4f}")
    print("-" * 50)
    print("\nThese are the numbers the two-tower model (step 4) aims to beat.")
    print("Step 2 complete. Next: python src/03_content_embeddings.py")


if __name__ == "__main__":
    main()
