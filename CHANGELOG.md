# Changelog — rag-governance-demo

All notable changes to this project are documented here. This demo is a
governed RAG Q&A template for AI-governance documentation; it has no
packaged version — milestones below are dated by commit.

## 2026-09-24 — Secure Ollama Cloud backend

### Added
- `SecureOllamaCloudBackend` in `src/backends.py`: Ollama Cloud access
  through the stored `custom.ollama` connector via authd surrogates.
  No raw API key is read, printed, persisted, or required in the
  environment. This is the backend the red-team generative battery now
  uses by default.

### Verified
- Full 49-case red-team battery run against this backend on 4 corpora
  (HotpotQA, SQuAD 2.0, EU AI Act, NIST AI RMF) across multiple models
  — see `ram-polisetti/rag-redteam` CHANGELOG 0.1.0 validation record.

## 2026-09-22 — Session 4: prompt-injection defenses, real-data corpus, red-team evals

### Added
- Prompt-injection defenses in the output gate (pattern-based checks).
- Real-data corpus wiring (HotpotQA, SQuAD 2.0, EU AI Act, NIST AI RMF)
  alongside the synthetic policy corpus.
- Red-team evaluation runs with the `rag-redteam` harness.

## 2026-09-22 — Domain-agnostic AI-governance Q&A template

### Changed
- Reframed as a domain-agnostic template: README, model card, NIST AI RMF
  risk assessment, limitations, and build spec.
- `corpus/<domain>/` layout with per-domain gate config; `--domain` CLI
  flag; 22-case multi-domain eval; stopword filtering; hash dim 2048.

### Added
- Domain corpora: supply-chain, hr-hiring, data-privacy, lending
  (21 synthetic docs).
- Human review queue: collect/list/decide CLI; verdicts append-only into
  the audit log; `review_queue.md` inbox.
- Dense embedding retriever (hash-based, stdlib) behind the same
  `search()` interface; A/B eval TF-IDF vs embeddings (12/12,
  hit-rate@1=1.0 both).

## 2026-09-22 — Governance packaging

### Added
- Model card, NIST AI RMF risk assessment, limitations doc.
- Eval harness (12 cases) and smoke tests.

## 2026-09-22 — Scaffold

### Added
- Repo layout, README, BUILD_SPEC, synthetic policy corpus (6 docs).
- RAG pipeline: ingest, TF-IDF retrieval, backends, governance gate, CLI.
