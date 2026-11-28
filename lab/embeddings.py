"""Pluggable local embedding backends (384-dim normalized vectors).

Backends:
  - 'fastembed' (recommended): Local ONNX neural embeddings via BAAI/bge-small-en-v1.5 (384d).
  - 'lsa' (zero-dependency fallback): Deterministic pure-Python TF-IDF + Random Projection (384d)
    for offline testing before installing fastembed.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

DIM = 384
DEFAULT_FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm < 1e-12:
        return [0.0] * len(vec)
    return [v / norm for v in vec]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _hash_feature_vec(tokens: list[str], idf: dict[str, float] | None = None) -> list[float]:
    """Signed random-projection hashing into 384d (Johnson-Lindenstrauss style)."""
    vec = [0.0] * DIM
    counts = Counter(tokens)
    total = max(1, len(tokens))
    # Include unigrams and bigrams for richer phrase geometry
    features: list[tuple[str, float]] = []
    for tok, cnt in counts.items():
        w = (1.0 + math.log(cnt)) * (idf.get(tok, 1.0) if idf else 1.0) / math.sqrt(total)
        features.append((tok, w))
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]}_{tokens[i + 1]}"
        features.append((bg, 0.7 / math.sqrt(total)))

    for feat, weight in features:
        h = hashlib.blake2b(feat.encode("utf-8"), digest_size=16).digest()
        # Project each feature into 4 sparse signed coordinates
        for k in range(4):
            idx = int.from_bytes(h[k * 4 : k * 4 + 2], "little") % DIM
            sign = 1.0 if (h[k * 4 + 2] & 1) == 0 else -1.0
            vec[idx] += sign * weight
    return l2_normalize(vec)


class LocalEmbedder:
    def __init__(self, backend: str = "auto", model_name: str = DEFAULT_FASTEMBED_MODEL):
        self.model_name = model_name
        self._fe_model = None
        self._idf: dict[str, float] = {}

        if backend == "auto":
            try:
                from fastembed import TextEmbedding  # type: ignore

                self._fe_model = TextEmbedding(model_name=model_name)
                self.backend = "fastembed"
            except ImportError:
                self.backend = "lsa"
        elif backend == "fastembed":
            from fastembed import TextEmbedding  # type: ignore

            self._fe_model = TextEmbedding(model_name=model_name)
            self.backend = "fastembed"
        elif backend == "lsa":
            self.backend = "lsa"
        else:
            raise ValueError(f"Unknown backend: {backend!r} (expected 'auto', 'fastembed', or 'lsa')")

    def fit_corpus(self, texts: list[str]) -> None:
        """Compute IDF weights when using the zero-dependency fallback backend."""
        if self.backend != "lsa":
            return
        n_docs = max(1, len(texts))
        df: Counter[str] = Counter()
        for t in texts:
            df.update(set(_tokenize(t)))
        self._idf = {tok: math.log((1 + n_docs) / (1 + freq)) + 1.0 for tok, freq in df.items()}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.backend == "fastembed":
            assert self._fe_model is not None
            return [l2_normalize(v.tolist()) for v in self._fe_model.embed(texts)]
        if not self._idf:
            self.fit_corpus(texts)
        return [_hash_feature_vec(_tokenize(t), self._idf) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.backend == "fastembed":
            assert self._fe_model is not None
            # BGE models benefit from query instruction prefix for retrieval
            q = f"Represent this sentence for searching relevant passages: {text}"
            vec = next(self._fe_model.embed([q]))
            return l2_normalize(vec.tolist())
        return _hash_feature_vec(_tokenize(text), self._idf)


def vec_to_pg_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"
