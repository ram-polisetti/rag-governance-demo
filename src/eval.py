"""Eval harness: groundedness, citation correctness, refusal behavior.

Exit code 0 iff every case passes. CI-ready.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ingest
from retrieve import TfidfRetriever
from backends import StubBackend
from gate import decide


def check(case, res):
    kind = case["expect"]
    if kind == "answer":
        if res.decision == "refuse":
            return False, "expected answer, got refusal"
        if case["expected_doc"] not in res.citations[0]:
            return False, f"wrong doc cited: {res.citations[0]}"
        low = res.answer.lower()
        missing = [k for k in case["keywords"] if k.lower() not in low]
        if missing:
            return False, f"missing keywords {missing}"
        return True, "grounded answer with correct citation"
    if kind == "refuse":
        ok = res.decision == "refuse"
        return ok, f"decision={res.decision} ({res.reason})"
    if kind == "escalate_or_answer":
        ok = res.decision in ("escalate", "answer")
        return ok, f"decision={res.decision}"
    return False, "unknown expect kind"


def run_eval(repo_root, verbose=True):
    root = Path(repo_root)
    chunks = ingest(root / "corpus")
    retr = TfidfRetriever(chunks)
    backend = StubBackend()
    cases = json.loads((root / "evals" / "test_set.json").read_text())
    audit = root / "eval_audit.jsonl"
    if audit.exists():
        audit.unlink()
    results = []
    for c in cases:
        scored = retr.search(c["query"], top_k=3)
        res = decide(c["query"], scored, backend, audit_path=str(audit))
        ok, notes = check(c, res)
        results.append({"id": c["id"], "pass": ok, "notes": notes,
                        "decision": res.decision,
                        "top_score": round(res.top_score, 3)})
        if verbose:
            print(("PASS " if ok else "FAIL ") + c["id"] + " — " + notes)
    passed = sum(r["pass"] for r in results)
    if verbose:
        print(f"\n{passed}/{len(results)} eval cases passed")
    return results


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    results = run_eval(root)
    sys.exit(0 if all(r["pass"] for r in results) else 1)
