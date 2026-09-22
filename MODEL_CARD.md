# Model Card — RAG Governance Demo

## Model details
- **System:** Governance-gated retrieval-augmented Q&A over supply-chain /
  logistics policy documents.
- **Version:** 0.1.0 (scaffold, 2026-09-21).
- **Builder:** Ram Charan Satya Sai Teja Polisetti.
- **Retrieval:** TF-IDF cosine similarity or dense-vector cosine similarity
  (deterministic hashed embeddings, stdlib-only; same `search()` interface)
  over 12 chunks from 6 documents. A neural-embedding adapter
  (`src/ollama_embed.py`) is provided but Ollama Cloud does not currently
  expose `/api/embed` (verified 2026-09-22: 401 while `/api/chat` works).
- **Generation:** `StubBackend` (extractive — quotes the top chunk with its
  chunk id) by default; `OllamaCloudBackend` (Ollama Cloud chat API,
  system-prompted to answer only from excerpts) optional.
- **Governance gate:** refuses below 0.10 top retrieval score or on
  out-of-scope patterns; escalates to human review below 0.25; audit-logs
  every decision.

## Intended use
Answering staff questions about warehouse/logistics policy from an approved
corpus, with citations, in settings where a wrong answer has safety or
compliance consequences. Demonstrates governance-by-design for operational AI.

## Out-of-scope uses
Anything outside the 6 policy documents. Medical, legal, or financial advice.
Production deployment without the roadmap hardening (see BUILD_SPEC.md).

## Training data
No model training. The corpus is 6 **synthetic, fictional** policy documents
written for this demo (hazmat handling, cold chain, carrier selection,
warehouse safety, returns & recall, customs documentation). No personal or
proprietary data.

## Evaluation (measured 2026-09-21, stub backend)
- **Eval harness** (`python3 -m src.eval`): **12/12 cases passed** —
  6 grounded answers with correct citations, 3 refusals (2 out-of-scope
  patterns, 1 low-score gibberish), 1 escalation on an ambiguous query,
  2 additional groundedness checks.
- **A/B retrieval** (`python3 -m src.eval --ab`, measured 2026-09-22):

  | retriever | cases passed | hit-rate@1 |
  |---|---|---|
  | TF-IDF | 12/12 | 1.000 |
  | dense (hashed embeddings) | 12/12 | 1.000 |

  Tie on this 12-case synthetic micro-corpus — expected: both are lexical,
  and the corpus is too small to separate them. The dense path's value is
  the interface (any neural `embed_fn` drops in) plus future paraphrase
  robustness at corpus scale (roadmap P5).
- **Governance finding from the A/B:** two edge cases flipped between
  `answer` and `escalate` across retrievers (scores 0.212→0.257 and
  0.279→0.244) while both stayed passing. Gate thresholds are
  retriever-specific and must be recalibrated whenever the retriever
  changes — recorded in RISK_ASSESSMENT.md.
- **Smoke tests** (`python3 -m unittest discover tests`): **13/13 passed**
  (ingestion, TF-IDF + dense retrieval, embedder determinism/norm,
  interface parity, refusal ×2, eval harness, A/B harness, audit-log schema).
- **Not yet evaluated:** paraphrase robustness, prompt-injection resistance,
  multi-document synthesis, latency.

## Limitations (summary — see LIMITATIONS.md)
Synthetic micro-corpus; TF-IDF is not semantic; thresholds are heuristic;
no prompt-injection defenses; local JSONL audit log; English only.

## Ethical considerations
Policy Q&A in warehouses affects worker safety. The system is designed to
refuse rather than guess, to cite everything, and to leave a trail — because
the failure mode that matters here is a confident wrong answer about hazmat
or cold chain. Extractive generation is a deliberate ethical choice for this
risk profile, not a capability shortcut.
