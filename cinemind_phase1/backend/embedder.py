"""
embedder.py
===========
E5 content-embedding utility, shared by recommender.py and llm_chains.py.

Wraps the same intfloat/e5-small-v2 model used offline in
notebooks/03_content_embeddings.ipynb so that a live query embeds into
EXACTLY the same vector space as artifacts/content_vecs.npy. If the vectors
were built with a different model, cosine similarity between them would be
meaningless.
"""

import os

import numpy as np

_model = None


def _get_model():
    """Lazy-load the model once per process (it's ~130MB, downloaded on
    first use and cached by sentence-transformers afterwards)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        allow_download = os.environ.get("CINEMIND_ALLOW_MODEL_DOWNLOAD") == "1"
        _model = SentenceTransformer(
            "intfloat/e5-small-v2",
            local_files_only=not allow_download,
        )
    return _model


def embed_query(text: str) -> np.ndarray:
    """Free-text search query -> unit-length embedding.

    E5 models expect a "query:" prefix for search queries (as opposed to
    "passage:" for the documents being searched over).
    """
    model = _get_model()
    return model.encode(f"query: {text}", normalize_embeddings=True)


def embed_passage(text: str) -> np.ndarray:
    """A document/item description -> unit-length embedding."""
    model = _get_model()
    return model.encode(f"passage: {text}", normalize_embeddings=True)
