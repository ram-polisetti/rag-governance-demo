# RAG Governance Demo

A **domain-agnostic, governance-gated Q&A template** for policy documents —
bring your own corpus. Ask questions, get answers grounded in the approved
policies with citations, and watch the system refuse when the evidence is
too thin. Packaged the way a regulated deployment should be: a governance
gate, full audit logging, a NIST AI RMF-style risk assessment, a model card,
and a pass/fail eval harness.

Built by an operator, for operators. Through-line: **governance of AI in
operational decision systems** — supply chain is where the builder comes
from, not the boundary of what this governs.

> **Synthetic data.** The `corpus/` policies are realistic but fictional,
> written for this demo. Not real company policies.

## Policy domains (pluggable)

```
corpus/
├── supply-chain/   # hazmat, cold chain, carrier selection, warehouse safety, ...
├── hr-hiring/      # hiring panels, equal opportunity, background checks, ...
├── data-privacy/   # retention, access control, breach notification, ...
└── lending/        # credit decisions, fair lending, adverse action, ...
```

Adding a domain is adding a folder of markdown: `corpus/<domain>/*.md`.
Ingestion, retrieval, gating, evals, and the review queue are all
domain-aware with zero code changes. Gate thresholds and out-of-scope
patterns are configurable per domain (`src/gate.py` — e.g. salary bands
are a legitimate question in `hr-hiring`, out-of-scope in `supply-chain`).

## Quickstart (stdlib only — no installs)

```bash
# List the policy domains
python3 -m src.cli --list-domains

# Ask within one domain (extractive stub backend: grounded by construction)
python3 -m src.cli --domain hr-hiring "When is the referral bonus paid?"

# ...or search all domains at once
python3 -m src.cli "How quickly must a suspected breach be reported to the DPO?"

# Run the eval harness (22 cases across 4 domains: groundedness, citations,
# refusals, cross-domain isolation)
python3 -m src.eval

# A/B: TF-IDF vs dense-embedding retrieval on the same test set
python3 -m src.eval --ab

# Use the dense retriever in the CLI
python3 -m src.cli --retriever embed --domain lending "What hours can collections calls be made?"

# Run the tests
python3 -m unittest discover tests
```

## Use a real model (Ollama Cloud)

```bash
export OLLAMA_API_KEY="..."            # your Ollama Cloud API key
export OLLAMA_CLOUD_MODEL="gpt-oss:20b"  # optional
python3 -m src.cli --backend ollama --domain data-privacy "How long are customer records retained?"
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
corpus/<domain>/*.md --ingest--> chunks --TF-IDF--> top-k --GATE--> answer | refuse | escalate
                                                                  |
                                                             audit_log.jsonl
```

1. **Ingest** (`src/ingest.py`): markdown policies -> deterministic,
   domain-tagged chunks (`<domain>/<doc>#c<n>` citations).
2. **Retrieve** (`src/retrieve.py`): TF-IDF cosine similarity (stdlib only,
   stopword-filtered) or dense hashed embeddings — same `search()`
   interface, per-domain indexes.
3. **Generate** (`src/backends.py`): `StubBackend` (extractive, cites chunk ids)
   or `OllamaCloudBackend` (Ollama Cloud chat, constrained to the excerpts).
4. **Gate** (`src/gate.py`): the gate that says no. Refuses when the top
   retrieval score is below threshold or the query is out of scope;
   escalates to a human reviewer on low confidence. Thresholds and
   out-of-scope patterns are configurable per domain. Every decision is
   audit-logged with its domain.

## Governance packaging

- `MODEL_CARD.md` — intended use, data, eval results, limitations, ethics.
- `RISK_ASSESSMENT.md` — NIST AI RMF (Govern / Map / Measure / Manage).
- `LIMITATIONS.md` — honest, explicit limits.
- `evals/test_set.json` + `src/eval.py` — pass/fail eval harness, per domain.
- `audit_log.jsonl` — every query and gate decision, hashed answers.
- `BUILD_SPEC.md` — architecture and roadmap.
