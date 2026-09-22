# Limitations — RAG Governance Demo

Honest limits of the system as built. Read before judging it, deploying it,
or citing it.

1. **Synthetic corpus.** The 6 policy documents are fictional. Retrieval and
   eval numbers reflect this tiny, clean corpus — not messy real-world docs.
2. **TF-IDF retrieval, not semantic.** Paraphrases with little word overlap
   will miss. This is a deliberate scaffold choice (deterministic, zero deps);
   embeddings are roadmap P2.
3. **Extractive default backend.** The stub quotes source chunks verbatim. That
   is the safest behavior for policy Q&A, but it cannot synthesize across
   documents or handle "compare X and Y" questions well.
4. **Thresholds are heuristic.** The 0.10/0.25 gate thresholds were tuned on
   12 eval cases. They are not statistically validated.
5. **No prompt-injection defenses yet.** A malicious document in the corpus
   could try to override instructions. Roadmap P4.
6. **Audit log is local JSONL.** Tamper-evident hashing of answers, but no
   tamper-proofing of the log itself. A production system needs signed,
   centralized logging.
7. **No access control, no PII handling.** Out of scope for the demo; any
   production use needs both.
8. **English only.** Tokenizer and corpus are English.
