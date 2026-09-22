"""Adapter for the Ollama /api/embed embeddings endpoint.

Forward-compatible adapter, NOT the active retriever. Verified 2026-09-22:
Ollama Cloud (https://ollama.com) does not currently expose /api/embed --
it returns HTTP 401 while /api/chat succeeds with the same credentials
(/api/embeddings 404s). This module is kept so a neural embed_fn can drop
into EmbeddingRetriever the day the endpoint exists (or against self-hosted
Ollama, where /api/embed works). Until then the stdlib HashEmbedder in
src/embeddings.py is the working dense retriever.

Usage:
    from ollama_embed import ollama_embed_fn
    retr = EmbeddingRetriever(chunks, ollama_embed_fn(model="nomic-embed-text"))
Requires OLLAMA_API_KEY in the environment.
"""
import json
import os
import urllib.request


def ollama_embed_fn(model="nomic-embed-text", batch_size=32):
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEY is not set")

    def _embed_batch(texts):
        body = json.dumps({"model": model, "input": texts}).encode()
        req = urllib.request.Request(
            "https://ollama.com/api/embed",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
        return out["embeddings"]

    def embed_fn(text):
        return _embed_batch([text])[0]

    def embed_many(texts):
        vecs = []
        for i in range(0, len(texts), batch_size):
            vecs.extend(_embed_batch(texts[i:i + batch_size]))
        return vecs

    embed_fn.many = embed_many
    return embed_fn
