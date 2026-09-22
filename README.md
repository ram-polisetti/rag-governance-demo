# RAG Governance Demo

A Q&A system over supply-chain / logistics policy documents, packaged the way
a regulated deployment should be: grounded generation with citations, a
governance gate that refuses when evidence is too thin, full audit logging,
a NIST AI RMF-style risk assessment, and an eval harness with pass/fail.

Built by an operator, for operators. Through-line: **governance of AI in
operational decision systems.**

> **Synthetic data.** The `corpus/` policies are realistic but fictional,
> written for this demo. Not real company policies.

## Quickstart (stdlib only — no installs)

```bash
# Ask a question (extractive stub backend: grounded by construction)
python3 -m src.cli "How far must Class 3 flammables be stored from oxidizers?"

# Run the eval harness (12 cases: groundedness, citations, refusals)
python3 -m src.eval

# A/B: TF-IDF vs dense-embedding retrieval on the same test set
python3 -m src.eval --ab

# Use the dense retriever in the CLI
python3 -m src.cli --retriever embed "What is the cold-chain temperature range?"

# Run the smoke tests
python3 -m unittest discover tests
```

## Use a real model (Ollama Cloud)

```bash
export OLLAMA_API_KEY="..."            # your Ollama Cloud API key
export OLLAMA_CLOUD_MODEL="gpt-oss:20b"  # optional
python3 -m src.cli --backend ollama "What is the cold-chain temperature range?"
```

## Human review queue

Escalated queries wait for a human verdict — collected from the audit log,
decided on the CLI, and every verdict is appended back to the audit trail
(append-only; history is never rewritten):

```bash
python3 -m src.review collect   # pull escalations from audit_log.jsonl
python3 -m src.review list      # show pending items
python3 -m src.review decide <id> approved --note "citation verified"
# verdicts: approved | corrected | rejected
```

## How it works

```
corpus/*.md --ingest--> chunks --TF-IDF--> top-k --GATE--> answer | refuse | escalate
                                                        |
                                                   audit_log.jsonl
```

1. **Ingest** (`src/ingest.py`): markdown policies -> deterministic chunks.
2. **Retrieve** (`src/retrieve.py`): TF-IDF cosine similarity (stdlib only).
   Swap in embeddings later via the same interface.
3. **Generate** (`src/backends.py`): `StubBackend` (extractive, cites chunk ids)
   or `OllamaCloudBackend` (Ollama Cloud chat, constrained to the excerpts).
4. **Gate** (`src/gate.py`): the gate that says no. Refuses when the top
   retrieval score is below threshold or the query is out of scope; escalates
   to a human reviewer on low confidence. Every decision is audit-logged.

## Governance packaging

- `MODEL_CARD.md` — intended use, data, eval results, limitations, ethics.
- `RISK_ASSESSMENT.md` — NIST AI RMF (Govern / Map / Measure / Manage).
- `LIMITATIONS.md` — honest, explicit limits.
- `evals/test_set.json` + `src/eval.py` — pass/fail eval harness.
- `audit_log.jsonl` — every query and gate decision, hashed answers.
- `BUILD_SPEC.md` — architecture and roadmap.
