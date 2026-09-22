"""Document ingestion: load a multi-domain markdown corpus, chunk deterministically.

Corpus layout: corpus/<domain>/<doc>.md. doc_id is "<domain>/<doc>" so
citations always name the domain; every Chunk carries its domain for
per-domain retrieval and evaluation.
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path

from redteam import sanitize_chunk


@dataclass
class Chunk:
    doc_id: str
    chunk_id: str
    text: str
    section: str
    domain: str
    trust: str = "trusted"  # "trusted" | "quarantined" (see src/redteam.py)


def load_corpus(corpus_dir):
    """Return {doc_id: (domain, text)} for every *.md under corpus_dir."""
    docs = {}
    for p in sorted(Path(corpus_dir).rglob("*.md")):
        rel = p.relative_to(corpus_dir)
        domain = rel.parent.name if len(rel.parts) > 1 else "general"
        doc_id = str(rel.with_suffix("")).replace(os.sep, "/")
        docs[doc_id] = (domain, p.read_text(encoding="utf-8"))
    return docs


def list_domains(corpus_dir):
    """Sorted list of policy domains present in the corpus."""
    return sorted({domain for domain, _ in load_corpus(corpus_dir).values()})


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


def ingest(corpus_dir, domain=None):
    """Ingest the corpus; if domain is given, only that domain's documents.

    Every chunk is scanned for embedded prompt-injection indicators
    (src/redteam.py). Flagged chunks are sanitized (injected lines excised)
    and marked trust="quarantined"; the gate refuses to answer from
    quarantined evidence.
    """
    docs = load_corpus(corpus_dir)
    chunks = []
    for doc_id, (ddomain, text) in docs.items():
        if domain is not None and ddomain != domain:
            continue
        for i, (ctext, section) in enumerate(chunk_text(text)):
            cleaned, flags = sanitize_chunk(ctext)
            trust = "quarantined" if flags else "trusted"
            chunks.append(Chunk(doc_id, f"{doc_id}#c{i}", cleaned, section,
                               ddomain, trust))
    return chunks
