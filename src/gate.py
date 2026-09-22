"""The governance gate: confidence thresholds, refusal, escalation, audit log.

The gate that says no: when retrieval evidence is too thin, the system refuses
to answer and says why, instead of hallucinating. Low-confidence answers are
flagged for human review. Every decision is written to an append-only audit
log with a hash of the answer.

Gate behavior is configurable per policy domain: thresholds and out-of-scope
patterns may differ between, say, supply-chain and HR corpora, because what
counts as a legitimate question depends on the domain.
"""
import hashlib
import json
import time
from dataclasses import dataclass, field

DEFAULT_GATE = {
    "refuse": 0.10,    # below this: evidence too thin -> refuse
    "escalate": 0.25,  # below this: answer, but flag for human review
    "out_of_scope": ("pto", "password", "stock price", "salary", "weather"),
}

# Per-domain overrides. A domain inherits DEFAULT_GATE except where it
# overrides. Example: salary bands and PTO are legitimate HR topics, so
# hr-hiring drops those from its out-of-scope patterns.
DOMAIN_GATE = {
    "hr-hiring": {"out_of_scope": ("stock price", "weather", "password")},
    "data-privacy": {"out_of_scope": ("stock price", "weather", "pto",
                                      "salary")},
    "lending": {"out_of_scope": ("stock price", "weather", "pto", "password")},
}


def gate_config(domain=None):
    """Resolved gate config for a domain (defaults when unknown/None)."""
    cfg = dict(DEFAULT_GATE)
    if domain and domain in DOMAIN_GATE:
        cfg.update(DOMAIN_GATE[domain])
    return cfg


REFUSAL_TEXT = (
    "I can't answer that from the approved policy corpus -- the retrieved "
    "evidence is too thin to give a grounded answer. This query has been "
    "logged for human review."
)


@dataclass
class GateResult:
    decision: str  # answer | refuse | escalate
    answer: str
    citations: list = field(default_factory=list)
    top_score: float = 0.0
    reason: str = ""


def decide(query, scored, backend, audit_path="audit_log.jsonl", domain=None):
    cfg = gate_config(domain)
    refuse_at, escalate_at = cfg["refuse"], cfg["escalate"]
    ql = query.lower()
    top_score = scored[0][0] if scored else 0.0
    citations = [c.chunk_id for _, c in scored[:3]]
    oos = next((p for p in cfg["out_of_scope"] if p in ql), None)

    if oos or top_score < refuse_at:
        reason = (f"out-of-scope pattern '{oos}'" if oos
                  else f"top retrieval score {top_score:.3f} < {refuse_at}")
        res = GateResult("refuse", REFUSAL_TEXT, citations, top_score, reason)
    elif top_score < escalate_at:
        answer = backend.generate(query, scored[:3])
        res = GateResult(
            "escalate",
            answer + "\n\n_⚠ Flagged for human review: low retrieval confidence._",
            citations, top_score,
            f"top score {top_score:.3f} < {escalate_at}",
        )
    else:
        res = GateResult("answer", backend.generate(query, scored[:3]),
                         citations, top_score, "grounded")
    log_audit(query, res, audit_path, domain=domain)
    return res


def log_audit(query, res, path, domain=None):
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query": query,
        "decision": res.decision,
        "domain": domain,
        "top_score": round(res.top_score, 4),
        "citations": res.citations,
        "reason": res.reason,
        "answer_sha256": hashlib.sha256(res.answer.encode()).hexdigest()[:16],
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
