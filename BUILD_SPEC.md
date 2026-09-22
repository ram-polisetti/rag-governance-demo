# Build Spec — RAG Governance Demo

## Goal
A portfolio-grade demo proving two things at once: (1) real RAG engineering
chops, (2) governance thinking baked into the system, not bolted on.
Audience: hiring managers and fellowship reviewers in AI governance /
 Responsible AI / applied AI roles.

## Architecture

```
+----------------+     +----------------+     +------------------+
| corpus/*.md    | --> | ingest.py      | --> | chunks (doc_id,   |
| (6 syn. policy |     | deterministic  |     |  chunk_id, text,  |
|  docs)         |     | chunking       |     |  section)        |
+----------------+     +----------------+     +--------+---------+
                                                     |
                                                     v
+----------------+     +----------------+     +------------------+
| User question  | --> | retrieve.py    | --> | top-k scored     |
|                |     | TF-IDF cosine  |     | (score, chunk)   |
|                |     | (stdlib only)  |     |                  |
+----------------+     +----------------+     +--------+---------+
                                                     |
                                                     v
                                              +------+-------+
                                              | gate.py      |
                                              | score < 0.10 +----> REFUSE (evidence too thin)
                                              |   or out-of- |
                                              |   scope      |
                                              | 0.10-0.25    +----> ESCALATE (answer + human review flag)
                                              | >= 0.25      +----> ANSWER (with citations)
                                              +------+-------+
                                                     |
                                              audit_log.jsonl
                                              (ts, query, decision, score,
                                               citations, reason, answer hash)

Generation backends (src/backends.py):
- StubBackend (default): extractive — answers by quoting the top chunk with
  its chunk id. Grounded by construction; zero hallucination surface.
- OllamaCloudBackend: Ollama Cloud chat API, system-prompted to answer ONLY
  from the excerpts and to refuse otherwise. Needs OLLAMA_API_KEY.
```

## Component choices (and why)

| Decision | Choice | Rationale |
|---|---|---|
| Retrieval | TF-IDF cosine, pure stdlib | Deterministic, zero deps, runs anywhere; proves the pipeline before spending on embeddings. Interface allows a drop-in embedding retriever later. |
| Generation default | Extractive stub | Governance-first: for a policy Q&A demo, quoting the source with a citation is the safest possible behavior. Shows judgment, not just model-chasing. |
| Real-model path | Ollama Cloud via API | Charan's existing cloud access; no GPU needed; constrained decoding via system prompt + gate. |
| Chunking | Paragraph-grouped, <=800 chars, section-tracked | Citations name the section; humans can verify. |
| Thresholds | refuse < 0.10, escalate < 0.25 | Conservative by design; tuned on the eval set (see src/eval.py). Documented in RISK_ASSESSMENT.md. |
| Audit log | Append-only JSONL, answer SHA-256 | Tamper-evident-ish trail: what was asked, what was retrieved, what was decided, and a hash of what was said. |
| Corpus | 6 synthetic policy docs | Realistic (hazmat, cold chain, carrier selection, warehouse safety, returns/recall, customs) but clearly synthetic — no proprietary data risk. |

## Governance packaging plan
- MODEL_CARD.md: intended use / out-of-scope uses, data card for the corpus,
  eval results (from `python3 -m src.eval`), limitations, ethical notes.
- RISK_ASSESSMENT.md: NIST AI RMF 1.0 mapping — Govern (ownership, policies),
  Map (use case, stakeholders, failure modes), Measure (eval metrics, thresholds),
  Manage (monitoring, incident response, review cadence).
- LIMITATIONS.md: explicit non-goals and known weaknesses.
- Evals: 12-case harness — groundedness, citation correctness, refusal on
  out-of-corpus, escalation on ambiguity. CI-ready (`exit 1` on failure).

## Roadmap (later sessions)
- P2: embedding retriever (Ollama Cloud embeddings) behind the same
  interface; A/B eval TF-IDF vs embeddings on the test set.
- P3: human review queue (escalated queries -> review UI / markdown inbox).
- P4: prompt-injection tests (malicious corpus chunk trying to override
  instructions) + mitigation.
- P5: larger corpus, multi-doc synthesis answers, GitHub Actions CI.
