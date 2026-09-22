"""Retrieval over chunks: TF-IDF (sparse) and dense embeddings.

TfidfRetriever is pure stdlib and deterministic. EmbeddingRetriever takes any
embed_fn(text) -> unit vector, so a neural embedding model drops in behind
the same search() interface without touching the gate, backends, or evals.
"""
import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")

# Common English function words carry no topical signal. In a small corpus
# they dominate cosine scores and let unrelated queries match (e.g. "what is
# the ..." matching any chunk). Filtering them is standard IR practice.
STOPWORDS = frozenset("""
a an the and or but if then else when at by for with about into through
during before after above below to from up down in out on off over under
of is are was were be been being have has had do does did will would shall
should can could may might must what which who whom whose how why where
that this these those it its as not no so than too very just any all each
both few more most other some such only own same s t d ll re ve m
""".split())


def tokenize(t):
    return [tok for tok in TOKEN.findall(t.lower()) if tok not in STOPWORDS]


class TfidfRetriever:
    name = "tfidf"

    def __init__(self, chunks):
        self.chunks = chunks
        df = Counter()
        self.doc_tf = []
        for ch in chunks:
            tf = Counter(tokenize(ch.text))
            self.doc_tf.append(tf)
            for tok in tf:
                df[tok] += 1
        n = len(chunks)
        self.idf = {tok: math.log((n + 1) / (c + 1)) + 1.0 for tok, c in df.items()}
        self.doc_vecs = []
        for tf in self.doc_tf:
            tot = sum(tf.values()) or 1
            v = {tok: (c / tot) * self.idf[tok] for tok, c in tf.items()}
            norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            self.doc_vecs.append({tok: x / norm for tok, x in v.items()})

    def _vec(self, text):
        tf = Counter(tokenize(text))
        tot = sum(tf.values()) or 1
        v = {tok: (c / tot) * self.idf[tok] for tok, c in tf.items() if tok in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {tok: x / norm for tok, x in v.items()}

    def search(self, query, top_k=3):
        qv = self._vec(query)
        scored = []
        for ch, dv in zip(self.chunks, self.doc_vecs):
            s = sum(qv.get(t, 0.0) * w for t, w in dv.items())
            scored.append((s, ch))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


class EmbeddingRetriever:
    """Dense-vector retrieval behind the same search() interface.

    embed_fn: callable text -> L2-normalized dense vector (list of floats).
    Ships with src.embeddings.HashEmbedder (stdlib, deterministic); swap in
    src.ollama_embed.ollama_embed_fn for neural embeddings when available.
    """

    name = "embedding"

    def __init__(self, chunks, embed_fn):
        self.chunks = chunks
        self.embed_fn = embed_fn
        many = getattr(embed_fn, "many", None)
        texts = [c.text for c in chunks]
        self.vecs = many(texts) if many else [embed_fn(t) for t in texts]

    def search(self, query, top_k=3):
        qv = self.embed_fn(query)
        scored = []
        for ch, v in zip(self.chunks, self.vecs):
            s = sum(x * y for x, y in zip(qv, v))  # cosine: inputs normalized
            scored.append((s, ch))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]
