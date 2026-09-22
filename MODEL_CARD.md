# Model Card — RAG Governance Demo

## Model details
- **System:** Governance-gated retrieval-augmented Q&A over supply-chain /
  logistics policy documents.
- **Version:** 0.1.0 (scaffold, 2026-09-21).
- **Builder:** Ram Charan Satya Sai Teja Polisetti.
- **Retrieval:** TF-IDF cosine similarity over 12 chunks from 6 documents
  (pure Python stdlib, deterministic).
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
- **Smoke tests** (`python3 -m unittest discover tests`): **6/6 passed**
  (ingestion, retrieval, refusal ×2, eval harness, audit-log schema).
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
