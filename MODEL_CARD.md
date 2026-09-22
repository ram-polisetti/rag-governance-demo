# Model Card — RAG Governance Demo

## Model details
- **System:** Domain-agnostic, governance-gated retrieval-augmented Q&A over
  policy documents. Bring your own corpus: `corpus/<domain>/*.md`.
- **Version:** 0.4.0 (red-team defenses + real-data domains, 2026-09-22).
- **Builder:** Ram Charan Satya Sai Teja Polisetti.
- **Retrieval:** TF-IDF cosine similarity (stdlib-only, stopword-filtered) or
  dense-vector cosine similarity (deterministic hashed embeddings,
  dim=2048, stdlib-only; same `search()` interface, same tokenizer). A
  neural-embedding adapter (`src/ollama_embed.py`) is provided but Ollama
  Cloud does not currently expose `/api/embed` (verified 2026-09-22: 401
  while `/api/chat` works).
- **Generation:** `StubBackend` (extractive — quotes the top chunk with its
  chunk id) by default; `OllamaCloudBackend` (Ollama Cloud chat API,
  system-prompted to answer only from excerpts) optional.
- **Governance gate:** per-domain configurable thresholds (default: refuse
  below 0.10 top retrieval score, escalate below 0.25) and out-of-scope
  patterns; audit-logs every decision with its domain.

## Intended use
Answering staff questions from an approved policy corpus — any domain: HR,
privacy, lending, operations, compliance — with citations, in settings
where a wrong answer has safety, legal, or compliance consequences. A
template for governance-by-design in operational AI, not a single-domain
product.

## Out-of-scope uses
Anything outside the loaded policy domains. Medical, legal, or financial
advice. Production deployment without the roadmap hardening (see
BUILD_SPEC.md).

## Training data
No model training. The corpus is 23 documents / 997 chunks across 6
domains: 21 **synthetic, fictional** policy documents (supply-chain: 6,
hr-hiring: 5, data-privacy: 5, lending: 5) plus 2 **real public-data**
documents — Regulation (EU) 2024/1689 (EU AI Act, via EUR-Lex,
retrieved 2026-09-22) and NIST AI RMF 1.0 (via nvlpubs.nist.gov,
retrieved 2026-09-22). No personal or proprietary data. New domains are
added as folders — no code changes. Real-data files carry source URLs
and retrieval dates in their headers.

## Evaluation (measured 2026-09-22, stub backend, TF-IDF default)
- **Eval harness** (`python3 -m src.eval`): **37/37 cases passed** —
  grounded answers with correct citations across all 6 domains
  (incl. 5 on the real EU AI Act / NIST AI RMF corpora), refusals
  (out-of-scope patterns, gibberish, cross-domain isolation), ambiguous
  queries escalated-or-answered, and **10/10 red-team attack cases
  refused** (direct injection, jailbreak, exfiltration, poisoned corpus
  chunks).
- **A/B retrieval** (`python3 -m src.eval --ab`):

  | retriever | cases passed | hit-rate@1 |
  |---|---|---|
  | TF-IDF | 37/37 | 1.000 |
  | dense (hashed embeddings, dim=2048) | 37/37 | 1.000 |

  The dense path is a stdlib stand-in for real embeddings; on the
  811-chunk EU AI Act corpus its top-1 disagrees with TF-IDF on vague
  queries (agreement on distinctive ones) — a known limitation of hashed
  embeddings at corpus scale, documented in LIMITATIONS.md. Raising the
  hash dimension from 512 to 2048 cut collision noise (a gibberish query
  scored 0.127 at dim=512, 0.000 at dim=2048).
- **Governance finding from the A/B:** edge cases still flip between
  `answer` and `escalate` across retrievers with no pass-rate change. Gate
  thresholds are retriever-specific and must be recalibrated whenever the
  retriever changes — recorded in RISK_ASSESSMENT.md.
- **Real-model red-team check** (`evals/ollama_redteam.py`, gpt-oss:20b
  via Ollama Cloud, 2026-09-22): 10/10 attack cases refused with the
  model invoked 0 times; 3/3 grounded controls answered with citations;
  audit logging verified (13/13 entries). See
  `docs/SESSION_4_REDTEAM.md` for methodology and per-case results.
- **Tests** (`python3 -m unittest discover tests`): **41/41 passed**
  (ingestion incl. domain layout + real-data domains, TF-IDF + dense
  retrieval, embedder determinism/norm, interface parity, refusal ×3,
  cross-domain isolation, per-domain gate config, eval harness, A/B
  harness, review queue, audit-log schema, red-team defenses —
  classification, sanitization, quarantine policy, output check,
  attack audit logging).
- **Not yet evaluated:** paraphrase robustness of the injection
  detectors, multi-document synthesis, latency.

## Limitations (summary — see LIMITATIONS.md)
Synthetic micro-corpus; TF-IDF is not semantic; thresholds are heuristic
and retriever-specific; no prompt-injection defenses; local JSONL audit
log; English only.

## Ethical considerations
Policy Q&A affects worker safety, employment decisions, privacy rights, and
access to credit. The system is designed to refuse rather than guess, to
cite everything, and to leave a trail — because the failure mode that
matters here is a confident wrong answer about hazmat, a hiring decision,
or a loan. Extractive generation is a deliberate ethical choice for this
risk profile, not a capability shortcut. Per-domain gate config exists
because what counts as answerable — and what counts as out-of-scope —
depends on the domain being governed.
