"""The governance gate: confidence thresholds, refusal, escalation, audit log.

The gate that says no: when retrieval evidence is too thin, the system refuses
to answer and says why, instead of hallucinating. Low-confidence answers are
flagged for human review. Every decision is written to an append-only audit
log with a hash of the answer.
"""
import hashlib
import json
import time
from dataclasses import dataclass, field

REFUSE_THRESHOLD = 0.10    # below this: evidence too thin -> refuse
ESCALATE_THRESHOLD = 0.25  # below this: answer, but flag for human review

REFUSAL_TEXT = (
    "I can't answer that from the approved policy corpus -- the retrieved "
    "evidence is too thin to give a grounded answer. This query has been "
    "logged for human review."
)

OUT_OF_SCOPE_PATTERNS = ("pto", "password", "stock price", "salary", "weather")


@dataclass
class GateResult:
    decision: str  # answer | refuse | escalate
    answer: str
    citations: list = field(default_factory=list)
    top_score: float = 0.0
    reason: str = ""


def decide(query, scored, backend, audit_path="audit_log.jsonl"):
    ql = query.lower()
    top_score = scored[0][0] if scored else 0.0
    citations = [c.chunk_id for _, c in scored[:3]]
    oos = next((p for p in OUT_OF_SCOPE_PATTERNS if p in ql), None)

    if oos or top_score < REFUSE_THRESHOLD:
        reason = (f"out-of-scope pattern '{oos}'" if oos
                  else f"top retrieval score {top_score:.3f} < {REFUSE_THRESHOLD}")
        res = GateResult("refuse", REFUSAL_TEXT, citations, top_score, reason)
    elif top_score < ESCALATE_THRESHOLD:
        answer = backend.generate(query, scored[:3])
        res = GateResult(
            "escalate",
            answer + "\n\n_⚠ Flagged for human review: low retrieval confidence._",
            citations, top_score,
            f"top score {top_score:.3f} < {ESCALATE_THRESHOLD}",
        )
    else:
        res = GateResult("answer", backend.generate(query, scored[:3]),
                         citations, top_score, "grounded")
    log_audit(query, res, audit_path)
    return res


def log_audit(query, res, path):
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query": query,
        "decision": res.decision,
        "top_score": round(res.top_score, 4),
        "citations": res.citations,
        "reason": res.reason,
        "answer_sha256": hashlib.sha256(res.answer.encode()).hexdigest()[:16],
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
