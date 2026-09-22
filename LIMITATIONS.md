# Limitations — RAG Governance Demo

Honest limits of the system as built. Read before judging it, deploying it,
or citing it.

1. **Synthetic corpus.** The 21 policy documents across 4 domains are
   fictional. Retrieval and eval numbers reflect this tiny, clean corpus —
   not messy real-world docs.
2. **TF-IDF retrieval, not semantic.** Paraphrases with little word overlap
   will miss. This is a deliberate scaffold choice (deterministic, zero
   deps); the dense interface is ready for neural embeddings when
   available.
3. **Extractive default backend.** The stub quotes source chunks verbatim. That
   is the safest behavior for policy Q&A, but it cannot synthesize across
   documents or handle "compare X and Y" questions well.
4. **Thresholds are heuristic and retriever-specific.** Default 0.10/0.25
   gate thresholds were tuned on the eval set; they are not statistically
   validated, and they shift when the retriever changes. Per-domain
   overrides exist but have not been tuned per domain yet.
5. **Prompt-injection defenses are pattern-based and evadable (session 4
   added them; they are not bulletproof).** The query screen, chunk
   scanner, and output check use deterministic pattern matching — an
   attacker who paraphrases, encodes, or obfuscates instructions can
   evade them; there is no semantic classifier. False positives are also
   possible (a legitimate policy sentence that reads like an
   instruction could be quarantined). Quarantine is only as good as
   detection: a poisoned chunk the scanner doesn't recognize stays
   trusted. Measured 10/10 on the eval attack set — that measures the
   known attacks, not unknown ones. Full discussion:
   `docs/SESSION_4_REDTEAM.md` §9.
6. **Audit log is local JSONL.** Tamper-evident hashing of answers, but no
   tamper-proofing of the log itself. A production system needs signed,
   centralized logging.
7. **No access control, no PII handling.** Out of scope for the demo; any
   production use needs both.
8. **English only.** Tokenizer and corpus are English.
9. **Real-data corpus snapshots go stale.** The EU AI Act and NIST AI RMF
   texts are frozen at their 2026-09-22 retrieval dates; the law and the
   guidance evolve. Source URLs and retrieval dates are recorded in each
   file header so staleness is visible, but refreshing them is a
   deployer responsibility.
10. **The dense retriever is a hashed stand-in, not real embeddings.**
    On the 811-chunk EU AI Act corpus its top-1 disagrees with TF-IDF on
    vague queries (agreement on distinctive ones) — fine for the demo's
    A/B comparison, not a claim about real embedding models.
