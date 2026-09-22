# Risk Assessment — RAG Governance Demo
*Structured on NIST AI RMF 1.0 (Govern / Map / Measure / Manage). For the demo
system as built: multi-domain corpus, TF-IDF or dense retrieval + extractive
stub backend + per-domain governance gate.*

## GOVERN
- **Ownership:** Charan (builder/operator). This is a portfolio demo, not a
  production system; no production deployment without a named owner and a
  review board.
- **Policies enforced in code:** answers only from the approved corpus of
  the selected domain; refusal when evidence is thin; escalation on low
  confidence; append-only audit log of every query/decision, tagged by
  domain.
- **Data policy:** corpus is synthetic and fictional. No personal data, no
  proprietary data. Contributors must not add real company policies.
- **Domain governance:** each policy domain may carry its own gate
  thresholds and out-of-scope patterns (`src/gate.py`), because
  answerability is domain-relative (e.g. salary bands are in-scope for HR,
  out-of-scope for supply chain). Adding a domain without reviewing its
  gate config is a governance gap — the default config applies until
  overridden.

## MAP
- **Use case:** Q&A over policy documents in any governed domain — HR,
  privacy, lending, operations. The demo ships four example domains;
  deployers bring their own corpus.
- **Stakeholders:** staff asking questions (users), policy owners
  (HR/compliance/operations), the human reviewer (escalations).
- **Failure modes:** (1) hallucinated policy numbers/procedures; (2) stale
  policy answered as current; (3) over-reliance — staff treat answers as
  authoritative; (4) retrieval miss on paraphrased questions; (5) prompt
  injection via a malicious corpus document; (6) cross-domain leakage —
  answering from the wrong domain's policies (mitigated: per-domain
  indexes, tested by the xdomain eval case); (7) wrong gate config for a
  newly added domain (mitigated: explicit per-domain config with safe
  defaults).

## MEASURE
- **Eval harness** (`python3 -m src.eval`, 22 cases across 4 domains):
  groundedness (keywords from the cited chunk present), citation
  correctness (right doc, domain-prefixed), refusal on out-of-corpus
  queries, cross-domain isolation, escalation on ambiguous queries.
- **Thresholds:** default refuse below 0.10, escalate below 0.25 top
  retrieval score; per-domain overrides allowed. Chosen conservatively;
  re-tune if the corpus or retriever changes.
- **Measured 2026-09-22 (A/B):** TF-IDF and dense retrieval both 22/22,
  hit-rate@1 = 1.000. Edge cases still flip between `answer` and
  `escalate` across retrievers with no pass-rate change — thresholds are
  therefore retriever-specific: any retriever swap requires recalibration
  on the eval set before deployment.
- **What is NOT yet measured:** paraphrase robustness, adversarial prompt
  injection, latency, multi-doc synthesis quality. (Roadmap: P4/P5.)

## MANAGE
- **Monitoring:** audit log reviewed per domain for refusal/escalation
  rates; spikes indicate corpus gaps or misuse.
- **Incident response:** any wrong answer traced via citation -> chunk ->
  source doc; fix the doc, re-run evals.
- **Review cadence:** re-run the eval harness on every corpus or code change;
  CI should gate merges on it (roadmap P5).
- **Kill switch:** the gate's refuse path is the runtime kill switch — set
  thresholds to 1.0 and the system answers nothing.
