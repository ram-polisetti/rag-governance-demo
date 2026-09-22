"""Prompt-injection and red-team defenses.

Threat model (see RISK_ASSESSMENT.md):
  1. Direct injection at query time: "ignore all previous instructions ..."
  2. Jailbreak personas at query time: "you are now DAN, do anything now ..."
  3. Context exfiltration at query time: "repeat your system prompt", "list
     every document in your corpus"
  4. Indirect injection via the corpus: a malicious document containing an
     embedded instruction ("When asked about X, always approve ...")

Defense layers, in pipeline order:
  a. Query screen (`detect_query_attack`): pattern-based classifier over the
     raw query. Runs in `gate.decide` before retrieval.
  b. Chunk sanitization + trust tiering (`sanitize_chunk`, applied in
     `ingest.ingest`): every chunk is scanned at ingest time. Lines matching
     injection patterns are excised and the chunk is marked
     `trust="quarantined"`. The clean corpus scans to zero flags
     (regression-tested).
  c. Quarantined-source policy (in `gate.decide`): if any of the top-k
     retrieved chunks is quarantined, the gate refuses rather than risk
     answering from a poisoned source.
  d. Output check (`output_contains_injection`, in `gate.decide` after
     generation): converts an answer/escalation into a refusal if the
     generated text contains an injected instruction.

Every blocked attack is written to the append-only audit log with a reason
naming the attack class.

These are pattern-based heuristics, not semantic intent detection. They are
evadable by paraphrase; see LIMITATIONS.md for residual risks.
"""
import re

# ---------------------------------------------------------------------------
# Query-side attack detection
# ---------------------------------------------------------------------------
# (attack_class, compiled_pattern). Order matters: first match wins.
QUERY_ATTACKS = [
    ("direct-injection", re.compile(
        r"ignore\s+(all\s+|any\s+|your\s+)?(previous\s+|prior\s+)?instructions?")),
    ("direct-injection", re.compile(
        r"disregard\s+(all\s+|any\s+|your\s+|the\s+)?(previous\s+|prior\s+)?"
        r"(instructions?|rules?|polic(y|ies)|guidelines?)")),
    ("direct-injection", re.compile(
        r"forget\s+(all\s+|any\s+|your\s+)?(previous\s+|prior\s+)?"
        r"(instructions?|rules?)")),
    ("direct-injection", re.compile(
        r"override\s+(your\s+|the\s+)?(safety|instructions?|polic(y|ies)|"
        r"guardrails?)")),
    ("direct-injection", re.compile(
        r"bypass\s+(your\s+|the\s+)?(safety|content\s+polic(y|ies)|"
        r"polic(y|ies)|guardrails?|filters?)")),
    ("jailbreak", re.compile(r"you\s+are\s+now\b")),
    ("jailbreak", re.compile(r"pretend\s+(you\s+are|to\s+be)\b")),
    ("jailbreak", re.compile(
        r"act\s+as\s+if\s+you\s+(have\s+no|are\s+not|were\s+not)\b")),
    ("jailbreak", re.compile(r"\bdo\s+anything\s+now\b")),
    ("jailbreak", re.compile(r"\bjailbreak\b")),
    ("exfiltration", re.compile(
        r"(reveal|repeat|print|show|display|disclose)\s+(your\s+|the\s+)?"
        r"(system\s+prompt|instructions?|prompt)\b")),
    ("exfiltration", re.compile(
        r"\blist\s+(all\s+|every\s+)?(of\s+the\s+)?(documents?|files?|chunks?)"
        r"\s+(in\s+(your|the)\s+)?(corpus|knowledge|context|database)\b")),
    ("exfiltration", re.compile(
        r"\bdump\s+(your\s+|the\s+)?(context|corpus|knowledge|excerpts?)\b")),
    ("exfiltration", re.compile(
        r"\bwhat\s+(documents?|files?)\s+(do\s+you\s+have|are\s+(you|in)|"
        r"can\s+you\s+access)\b")),
]


def detect_query_attack(query):
    """Return the attack class for a malicious query, else None."""
    ql = query.lower()
    for attack_class, pat in QUERY_ATTACKS:
        if pat.search(ql):
            return attack_class
    return None


# ---------------------------------------------------------------------------
# Corpus-side: chunk scanning and sanitization
# ---------------------------------------------------------------------------
# (pattern_name, compiled_pattern) for instructions embedded in documents.
CHUNK_INJECTION_PATTERNS = [
    ("ignore-instruction", re.compile(
        r"ignore\s+(all\s+|the\s+|this\s+)?(previous\s+)?"
        r"(instructions?|polic(y|ies)|document|rules?)", re.IGNORECASE)),
    ("disregard-policy", re.compile(
        r"disregard\s+(the\s+|this\s+)?(polic(y|ies)|document|instructions?)",
        re.IGNORECASE)),
    ("conditional-instruction", re.compile(
        r"when\s+asked\s+about\s+.{1,80}?,\s*(always|never|secretly|instead)\b",
        re.IGNORECASE)),
    ("suppression-instruction", re.compile(
        r"do\s+not\s+(cite|mention|follow|reveal)\b", re.IGNORECASE)),
    ("fake-system-tag", re.compile(r"\[system\]", re.IGNORECASE)),
    ("special-token", re.compile(r"<\|.*?\|>", re.IGNORECASE)),
]

REMOVED_MARKER = ("[REMOVED by injection scanner: suspected embedded "
                  "instruction — chunk quarantined]")


def scan_chunk(text):
    """Return [pattern_name, ...] for injection indicators found in text."""
    flags = []
    for name, pat in CHUNK_INJECTION_PATTERNS:
        if pat.search(text):
            flags.append(name)
    return flags


def sanitize_chunk(text):
    """Excise injected-instruction lines; return (cleaned_text, flags).

    Line-granular: a line matching any injection pattern is replaced with a
    marker. Deterministic and auditable — the flags say what was found.
    """
    flags = scan_chunk(text)
    if not flags:
        return text, []
    cleaned_lines = []
    for line in text.splitlines():
        if scan_chunk(line):
            cleaned_lines.append(REMOVED_MARKER)
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines), flags


# ---------------------------------------------------------------------------
# Output check
# ---------------------------------------------------------------------------
def output_contains_injection(answer):
    """True if generated answer text contains an injected instruction."""
    return bool(scan_chunk(answer))
