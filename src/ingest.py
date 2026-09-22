"""Document ingestion: load markdown corpus, chunk deterministically."""
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    doc_id: str
    chunk_id: str
    text: str
    section: str


def load_corpus(corpus_dir):
    docs = {}
    for p in sorted(Path(corpus_dir).glob("*.md")):
        docs[p.stem] = p.read_text(encoding="utf-8")
    return docs


def chunk_text(text, max_chars=800):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur, section = [], [], "top"
    for p in paras:
        m = re.match(r"^#{1,3}\s+(.*)", p)
        if m:
            section = m.group(1).strip()
        if cur and sum(len(c) for c in cur) + len(p) > max_chars:
            chunks.append(("\n\n".join(cur), section))
            cur = []
        cur.append(p)
    if cur:
        chunks.append(("\n\n".join(cur), section))
    return chunks


def ingest(corpus_dir):
    docs = load_corpus(corpus_dir)
    chunks = []
    for doc_id, text in docs.items():
        for i, (ctext, section) in enumerate(chunk_text(text)):
            chunks.append(Chunk(doc_id, f"{doc_id}#c{i}", ctext, section))
    return chunks
