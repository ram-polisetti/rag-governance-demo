"""TF-IDF retrieval over chunks. Pure stdlib, deterministic.

The Retriever interface (search(query, top_k) -> [(score, Chunk), ...]) is
deliberate: a future embedding retriever (e.g. Ollama Cloud embeddings) can
replace TfidfRetriever without touching the gate, backends, or evals.
"""
import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(t):
    return TOKEN.findall(t.lower())


class TfidfRetriever:
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
