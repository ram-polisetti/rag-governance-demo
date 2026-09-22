"""Generation backends.

StubBackend is extractive: it answers by quoting the top retrieved chunk with
its chunk id. Grounded by construction -- the safest default for policy Q&A.

OllamaCloudBackend calls the Ollama Cloud chat API, system-prompted to answer
ONLY from the provided excerpts and to refuse otherwise. Requires
OLLAMA_API_KEY in the environment.
"""
import json
import os
import urllib.request


class StubBackend:
    name = "stub-extractive"

    def generate(self, query, contexts):
        top = contexts[0][1]
        return (
            f"Based on **{top.doc_id}** (section: {top.section}):\n\n"
            f"{top.text.strip()}\n\n_Citation: `{top.chunk_id}`_"
        )


class OllamaCloudBackend:
    name = "ollama-cloud"

    def __init__(self, model=None):
        self.model = model or os.environ.get("OLLAMA_CLOUD_MODEL", "gpt-oss:20b")
        self.api_key = os.environ.get("OLLAMA_API_KEY")
        if not self.api_key:
            raise RuntimeError("OLLAMA_API_KEY is not set")

    def generate(self, query, contexts):
        ctx = "\n\n---\n\n".join(f"[{c.chunk_id}] {c.text}" for _, c in contexts)
        system = (
            "You answer ONLY from the policy excerpts provided below. "
            "Cite chunk ids like [doc#c0] for every factual claim. "
            "If the excerpts do not contain the answer, say so plainly and refuse. "
            "Never invent policy numbers, thresholds, or procedures."
        )
        body = json.dumps({
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Excerpts:\n{ctx}\n\nQuestion: {query}"},
            ],
        })
        req = urllib.request.Request(
            "https://ollama.com/api/chat",
            data=body.encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["message"]["content"]
