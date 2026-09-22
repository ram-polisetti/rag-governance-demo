# Risk Assessment — RAG Governance Demo
*Structured on NIST AI RMF 1.0 (Govern / Map / Measure / Manage). For the demo
system as built: TF-IDF retrieval + extractive stub backend + governance gate.*

## GOVERN
- **Ownership:** Charan (builder/operator). This is a portfolio demo, not a
  production system; no production deployment without a named owner and a
  review board.
- **Policies enforced in code:** answers only from the approved corpus;
  refusal when evidence is thin; escalation on low confidence; append-only
  audit log of every query/decision.
- **Data policy:** corpus is synthetic and fictional. No personal data, no
  proprietary data. Contributors must not add real company policies.

## MAP
- **Use case:** Q&A over supply-chain/logistics policy documents for
  warehouse and operations staff.
- **Stakeholders:** operations staff (users), EHS/compliance (policy owners),
  the human reviewer (escalations).
- **Failure modes:** (1) hallucinated policy numbers/procedures; (2) stale
  policy answered as current; (3) over-reliance — staff treat answers as
  authoritative; (4) retrieval miss on paraphrased questions; (5) prompt
  injection via a malicious corpus document.

## MEASURE
- **Eval harness** (`python3 -m src.eval`, 12 cases): groundedness
  (keywords from the cited chunk present), citation correctness (right doc),
  refusal on out-of-corpus queries, escalation on ambiguous queries.
- **Thresholds:** refuse below 0.10, escalate below 0.25 top retrieval score.
  Chosen conservatively; re-tune if the corpus or retriever changes.
- **Measured 2026-09-22 (A/B):** swapping TF-IDF for dense retrieval flipped
  two edge cases between `answer` and `escalate` (scores moved 0.212->0.257
  and 0.279->0.244) with no change in pass rate. Thresholds are therefore
  retriever-specific: any retriever swap requires recalibration on the eval
  set before deployment.
- **What is NOT yet measured:** paraphrase robustness, adversarial prompt
  injection, latency, multi-doc synthesis quality. (Roadmap: P4/P5.)

## MANAGE
- **Monitoring:** audit log reviewed for refusal/escalation rates; spikes
  indicate corpus gaps or misuse.
- **Incident response:** any wrong answer traced via citation -> chunk ->
  source doc; fix the doc, re-run evals.
- **Review cadence:** re-run the eval harness on every corpus or code change;
  CI should gate merges on it (roadmap P5).
- **Kill switch:** the gate's refuse path is the runtime kill switch — set
  thresholds to 1.0 and the system answers nothing.
