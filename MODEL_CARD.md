# Model Card — RAG Governance Demo

## Model details
- **System:** Domain-agnostic, governance-gated retrieval-augmented Q&A over
  policy documents. Bring your own corpus: `corpus/<domain>/*.md`.
- **Version:** 0.3.0 (multi-domain, 2026-09-22).
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
No model training. The corpus is 21 **synthetic, fictional** policy
documents across 4 domains (supply-chain: 6, hr-hiring: 5, data-privacy: 5,
lending: 5), written for this demo. No personal or proprietary data. New
domains are added as folders — no code changes.

## Evaluation (measured 2026-09-22, stub backend, TF-IDF default)
- **Eval harness** (`python3 -m src.eval`): **22/22 cases passed** — 14
  grounded answers with correct citations across all 4 domains, 4 refusals
  (2 out-of-scope patterns, 1 gibberish, 1 cross-domain isolation), 4
  ambiguous queries escalated-or-answered.
- **A/B retrieval** (`python3 -m src.eval --ab`):

  | retriever | cases passed | hit-rate@1 |
  |---|---|---|
  | TF-IDF | 22/22 | 1.000 |
  | dense (hashed embeddings, dim=2048) | 22/22 | 1.000 |

  Tie on this synthetic micro-corpus — expected: both are lexical, and the
  corpus is too small to separate them. The dense path's value is the
  interface (any neural `embed_fn` drops in) plus future paraphrase
  robustness at corpus scale (roadmap P5). Raising the hash dimension from
  512 to 2048 cut collision noise (a gibberish query scored 0.127 at
  dim=512, 0.000 at dim=2048).
- **Governance finding from the A/B:** edge cases still flip between
  `answer` and `escalate` across retrievers with no pass-rate change. Gate
  thresholds are retriever-specific and must be recalibrated whenever the
  retriever changes — recorded in RISK_ASSESSMENT.md.
- **Tests** (`python3 -m unittest discover tests`): **24/24 passed**
  (ingestion incl. domain layout, TF-IDF + dense retrieval, embedder
  determinism/norm, interface parity, refusal ×3, cross-domain isolation,
  per-domain gate config, eval harness, A/B harness, review queue,
  audit-log schema).
- **Not yet evaluated:** paraphrase robustness, prompt-injection resistance,
  multi-document synthesis, latency.

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
