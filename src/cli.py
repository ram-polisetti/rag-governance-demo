"""CLI: python3 -m src.cli "your question" [--domain hr-hiring] [--backend stub|ollama]

Domain-agnostic governed Q&A: pick a policy domain, or search all domains.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ingest, list_domains
from retrieve import TfidfRetriever, EmbeddingRetriever
from embeddings import HashEmbedder
from backends import StubBackend, OllamaCloudBackend
from gate import decide


def build_retriever(kind, chunks):
    if kind == "embed":
        return EmbeddingRetriever(chunks, HashEmbedder(dim=2048).embed)
    return TfidfRetriever(chunks)


def main(argv=None):
    root = Path(__file__).resolve().parent.parent
    domains = list_domains(root / "corpus")

    ap = argparse.ArgumentParser(description="Governance-gated policy Q&A")
    ap.add_argument("query", nargs="?",
                    help="question to answer from the policy corpus")
    ap.add_argument("--backend", choices=["stub", "ollama"], default="stub")
    ap.add_argument("--retriever", choices=["tfidf", "embed"], default="tfidf")
    ap.add_argument("--domain", choices=domains, default=None,
                    help="restrict to one policy domain (default: all)")
    ap.add_argument("--list-domains", action="store_true",
                    help="list available policy domains and exit")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args(argv)

    if args.list_domains:
        print("\n".join(domains))
        return 0
    if not args.query:
        ap.error("a query is required (or use --list-domains)")

    chunks = ingest(root / "corpus", domain=args.domain)
    retr = build_retriever(args.retriever, chunks)
    backend = OllamaCloudBackend() if args.backend == "ollama" else StubBackend()
    res = decide(args.query, retr.search(args.query, args.top_k), backend,
                 audit_path=str(root / "audit_log.jsonl"), domain=args.domain)
    print(f"[{res.decision}] score={res.top_score:.3f} ({res.reason})\n")
    print(res.answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
