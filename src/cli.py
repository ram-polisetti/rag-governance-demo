"""CLI: python3 -m src.cli "your question" [--backend stub|ollama]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ingest
from retrieve import TfidfRetriever
from backends import StubBackend, OllamaCloudBackend
from gate import decide


def main():
    ap = argparse.ArgumentParser(description="Governance-gated policy Q&A")
    ap.add_argument("query")
    ap.add_argument("--backend", choices=["stub", "ollama"], default="stub")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    chunks = ingest(root / "corpus")
    retr = TfidfRetriever(chunks)
    backend = OllamaCloudBackend() if args.backend == "ollama" else StubBackend()
    res = decide(args.query, retr.search(args.query, args.top_k), backend,
                 audit_path=str(root / "audit_log.jsonl"))
    print(f"[{res.decision}] score={res.top_score:.3f} ({res.reason})\n")
    print(res.answer)


if __name__ == "__main__":
    main()
