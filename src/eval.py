"""Eval harness: groundedness, citation correctness, refusal behavior.

Exit code 0 iff every case passes. CI-ready.

Each case names a policy domain; the question is evaluated against that
domain's corpus only (domain isolation is part of what is being tested).
`python3 -m src.eval --ab` runs an A/B: TF-IDF vs dense-embedding retrieval
through the same gate + backend, reporting per-case pass/fail and hit-rate@1
(top chunk's document == expected_doc) for each retriever.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ingest
from retrieve import TfidfRetriever, EmbeddingRetriever
from embeddings import HashEmbedder
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


def load_cases(repo_root):
    return json.loads((Path(repo_root) / "evals" / "test_set.json").read_text())


def domain_chunks(repo_root):
    """{domain: [Chunk]} for every domain in the corpus.

    The red-team corpus (evals/redteam_corpus/<domain>/*.md -- documents
    carrying embedded prompt-injection payloads) is folded into each
    domain's index so poisoned-chunk attack cases execute against the same
    pipeline as normal cases. Malicious chunks are sanitized and marked
    trust="quarantined" at ingest (src/ingest.py); the gate must refuse
    any query whose top-k evidence includes one.
    """
    by_domain = {}
    for ch in ingest(Path(repo_root) / "corpus"):
        by_domain.setdefault(ch.domain, []).append(ch)
    rt_dir = Path(repo_root) / "evals" / "redteam_corpus"
    if rt_dir.exists():
        for ch in ingest(rt_dir):
            by_domain.setdefault(ch.domain, []).append(ch)
    return by_domain


def run_eval(repo_root, verbose=True):
    root = Path(repo_root)
    cases = load_cases(root)
    chunks_by_domain = domain_chunks(root)
    retrievers = {d: TfidfRetriever(cs)
                  for d, cs in chunks_by_domain.items()}
    backend = StubBackend()
    audit = root / "eval_audit.jsonl"
    if audit.exists():
        audit.unlink()
    results = []
    for c in cases:
        domain = c.get("domain")
        retr = retrievers[domain]
        scored = retr.search(c["query"], top_k=3)
        res = decide(c["query"], scored, backend, audit_path=str(audit),
                     domain=domain)
        ok, notes = check(c, res)
        results.append({"id": c["id"], "domain": domain, "pass": ok,
                        "notes": notes, "decision": res.decision,
                        "top_score": round(res.top_score, 3)})
        if verbose:
            print(("PASS " if ok else "FAIL ") + c["id"] + " — " + notes)
    passed = sum(r["pass"] for r in results)
    if verbose:
        print(f"\n{passed}/{len(results)} eval cases passed")
        id2case = {c["id"]: c for c in cases}
        rt = [r for r in results if "attack" in id2case[r["id"]]]
        if rt:
            rt_pass = sum(r["pass"] for r in rt)
            print(f"red-team attack cases: {rt_pass}/{len(rt)} passed")
            by_attack = {}
            for r in rt:
                atk = id2case[r["id"]]["attack"]
                p, n = by_attack.get(atk, (0, 0))
                by_attack[atk] = (p + r["pass"], n + 1)
            for atk, (p, n) in sorted(by_attack.items()):
                print(f"  {atk}: {p}/{n}")
    return results


def _run_ab_main(root):
    summary = run_ab(root)
    ok = all(r["pass"] for r in summary["tfidf"]) and \
        all(r["pass"] for r in summary["embed"])
    sys.exit(0 if ok else 1)


def run_ab(repo_root, verbose=True):
    """A/B both retrievers through the identical gate+backend pipeline,
    per domain, on the full test set."""
    root = Path(repo_root)
    backend = StubBackend()
    cases = load_cases(root)
    chunks_by_domain = domain_chunks(root)
    for name in ("tfidf", "embed"):
        audit = root / f"eval_audit_{name}.jsonl"
        if audit.exists():
            audit.unlink()
    embedder = HashEmbedder(dim=2048)
    retrievers = {
        "tfidf": {d: TfidfRetriever(cs)
                  for d, cs in chunks_by_domain.items()},
        "embed": {d: EmbeddingRetriever(cs, embedder.embed)
                  for d, cs in chunks_by_domain.items()},
    }
    summary = {}
    for name in ("tfidf", "embed"):
        per_case, hits = [], 0
        answer_cases = 0
        for c in cases:
            domain = c.get("domain")
            retr = retrievers[name][domain]
            scored = retr.search(c["query"], top_k=3)
            res = decide(c["query"], scored, backend,
                         audit_path=str(root / f"eval_audit_{name}.jsonl"),
                         domain=domain)
            ok, notes = check(c, res)
            per_case.append({"id": c["id"], "domain": domain, "pass": ok,
                             "notes": notes, "decision": res.decision,
                             "top_score": round(res.top_score, 3),
                             "top_doc": scored[0][1].doc_id})
            if c["expect"] == "answer":
                answer_cases += 1
                if scored[0][1].doc_id == f"{domain}/{c['expected_doc']}":
                    hits += 1
        summary[name] = per_case
        summary[name + "_hit_rate_at_1"] = round(hits / answer_cases, 3) \
            if answer_cases else 0.0
    if verbose:
        print(f"{'case':<12}{'tfidf':<28}{'embed':<28}")
        for t, e in zip(summary["tfidf"], summary["embed"]):
            print(f"{t['id']:<12}"
                  f"{'PASS' if t['pass'] else 'FAIL'} {t['decision']:<8} "
                  f"s={t['top_score']:<6} "
                  f"{'PASS' if e['pass'] else 'FAIL'} {e['decision']:<8} "
                  f"s={e['top_score']:<6}")
        for name in ("tfidf", "embed"):
            p = sum(r["pass"] for r in summary[name])
            hr = summary[name + "_hit_rate_at_1"]
            print(f"\n{name}: {p}/{len(summary[name])} cases passed, "
                  f"hit-rate@1={hr}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", action="store_true",
                    help="A/B: TF-IDF vs embedding retrieval on the test set")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    if args.ab:
        _run_ab_main(root)
    results = run_eval(root)
    sys.exit(0 if all(r["pass"] for r in results) else 1)
