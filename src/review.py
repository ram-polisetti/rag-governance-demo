"""Human review queue for escalated queries.

Escalated queries (gate decision `escalate`) need a human verdict. This
module keeps a file-based review inbox -- no server, no new dependencies:

- `review_queue.json` — machine state (pending + decided items)
- `review_queue.md`    — human-readable rendering of the same
- `review_decisions.jsonl` — append-only record of reviewer verdicts

Every verdict is ALSO appended to the main audit log as a `review_decision`
entry (append-only: history is never rewritten, the review links back to the
original query via its answer hash).

Usage:
    python3 -m src.review collect [--audit audit_log.jsonl]
    python3 -m src.review list
    python3 -m src.review decide <id> approved|corrected|rejected [--note ".."]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate import log_audit, GateResult

VALID_VERDICTS = ("approved", "corrected", "rejected")


def _paths(root):
    return {
        "queue": root / "review_queue.json",
        "md": root / "review_queue.md",
        "decisions": root / "review_decisions.jsonl",
    }


def load_queue(root):
    p = _paths(root)["queue"]
    if p.exists():
        return json.loads(p.read_text())
    return {"items": []}


def save_queue(root, queue):
    p = _paths(root)
    p["queue"].write_text(json.dumps(queue, indent=2) + "\n")
    lines = ["# Review Queue", "",
             "_Escalated queries awaiting a human verdict. "
             "Use `python3 -m src.review decide <id> <verdict>`._", ""]
    pending = [i for i in queue["items"] if i["status"] == "pending"]
    decided = [i for i in queue["items"] if i["status"] != "pending"]
    lines.append(f"## Pending ({len(pending)})")
    for it in pending:
        lines.append(f"- [ ] `{it['id']}` — score {it['top_score']:.3f} — "
                     f"{it['query']}")
        lines.append(f"  citations: {', '.join(it['citations'])}")
    lines.append("")
    lines.append(f"## Decided ({len(decided)})")
    for it in decided:
        lines.append(f"- [x] `{it['id']}` — **{it['status']}** — {it['query']}")
        if it.get("note"):
            lines.append(f"  note: {it['note']}")
    p["md"].write_text("\n".join(lines) + "\n")


def collect(root, audit_path):
    """Pull escalated entries from the audit log into the queue."""
    queue = load_queue(root)
    known = {i["id"] for i in queue["items"]}
    added = 0
    with open(audit_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get("decision") != "escalate":
                continue
            eid = e.get("answer_sha256", "")[:16]
            if not eid or eid in known:
                continue
            queue["items"].append({
                "id": eid,
                "query": e["query"],
                "top_score": e["top_score"],
                "citations": e["citations"],
                "reason": e["reason"],
                "escalated_ts": e["ts"],
                "status": "pending",
            })
            known.add(eid)
            added += 1
    save_queue(root, queue)
    return added


def decide_review(root, item_id, verdict, note="", audit_path="audit_log.jsonl"):
    """Record a reviewer verdict; link it into the audit trail."""
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"verdict must be one of {VALID_VERDICTS}")
    queue = load_queue(root)
    item = next((i for i in queue["items"] if i["id"] == item_id), None)
    if item is None:
        raise KeyError(f"no queued item {item_id}")
    if item["status"] != "pending":
        raise ValueError(f"item {item_id} already decided: {item['status']}")
    item["status"] = verdict
    item["note"] = note
    item["decided_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_queue(root, queue)

    record = {"ts": item["decided_ts"], "item_id": item_id,
              "query": item["query"], "verdict": verdict, "note": note}
    with open(_paths(root)["decisions"], "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    # Append-only audit entry linking the verdict to the original decision.
    res = GateResult("review_decision",
                     f"reviewer verdict: {verdict}" + (f" — {note}" if note else ""),
                     item["citations"], item["top_score"],
                     f"human review of escalated query {item_id}")
    log_audit(item["query"], res, str(root / audit_path) if not
              Path(audit_path).is_absolute() else audit_path)
    return record


def main():
    ap = argparse.ArgumentParser(description="Human review queue")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--audit", default="audit_log.jsonl")
    sub.add_parser("list")
    d = sub.add_parser("decide")
    d.add_argument("item_id")
    d.add_argument("verdict", choices=VALID_VERDICTS)
    d.add_argument("--note", default="")
    d.add_argument("--audit", default="audit_log.jsonl")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    if args.cmd == "collect":
        n = collect(root, args.audit)
        print(f"collected {n} escalated quer{'y' if n == 1 else 'ies'}")
    elif args.cmd == "list":
        queue = load_queue(root)
        pending = [i for i in queue["items"] if i["status"] == "pending"]
        if not pending:
            print("review queue is empty")
        for it in pending:
            print(f"{it['id']}  score={it['top_score']:.3f}  {it['query']}")
    elif args.cmd == "decide":
        rec = decide_review(root, args.item_id, args.verdict,
                            note=args.note, audit_path=args.audit)
        print(f"recorded: {rec['item_id']} -> {rec['verdict']}")


if __name__ == "__main__":
    main()
