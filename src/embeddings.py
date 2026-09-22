"""Dense embeddings without dependencies: the hashing trick.

HashEmbedder maps each token to one of `dim` buckets via SHA-256 (unsigned
counts), then L2-normalizes. The result is a genuine dense vector: fixed
dimensionality, cosine-similarity retrieval, deterministic, zero deps.

This is a *lexical* dense embedding, not a neural one -- it has no notion of
synonymy beyond shared tokens. It exists to prove the retrieval interface:
any embed_fn (including a neural model) drops in behind EmbeddingRetriever
in src/retrieve.py without touching the gate, backends, or evals.

Verified 2026-09-22: Ollama Cloud does not expose /api/embed (the endpoint
returns 401 while /api/chat works with the same credentials), so neural
embeddings are not available there today. See src/ollama_embed.py for the
forward-compatible adapter.
"""
import hashlib
import math
import re

TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(t):
    return TOKEN.findall(t.lower())


class HashEmbedder:
    """Deterministic hashed bag-of-words -> unit dense vector."""

    def __init__(self, dim=512):
        self.dim = dim

    def _index(self, token):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % self.dim

    def embed(self, text):
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            vec[self._index(tok)] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_many(self, texts):
        return [self.embed(t) for t in texts]


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))
