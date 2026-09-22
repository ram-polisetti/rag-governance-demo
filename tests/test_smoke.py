"""Smoke tests: ingestion, retrieval, gate, eval, audit log."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ingest import ingest
from retrieve import TfidfRetriever
from backends import StubBackend
from gate import decide
from eval import run_eval


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = ingest(ROOT / "corpus")
        cls.retr = TfidfRetriever(cls.chunks)
        cls.backend = StubBackend()

    def test_ingest_produces_chunks(self):
        self.assertGreaterEqual(len(self.chunks), 12)
        doc_ids = {c.doc_id for c in self.chunks}
        self.assertEqual(len(doc_ids), 6)

    def test_retrieval_finds_hazmat(self):
        scored = self.retr.search(
            "How must Class 3 flammable liquids be segregated?", top_k=3)
        self.assertIn("hazmat-handling-policy", scored[0][1].doc_id)
        self.assertGreater(scored[0][0], 0.25)

    def test_gate_refuses_out_of_scope(self):
        res = decide("What is the PTO carryover policy?",
                     self.retr.search("What is the PTO carryover policy?"),
                     self.backend, audit_path=str(ROOT / "test_audit.jsonl"))
        self.assertEqual(res.decision, "refuse")

    def test_gate_refuses_gibberish(self):
        res = decide("blorpt quux zzz",
                     self.retr.search("blorpt quux zzz"),
                     self.backend, audit_path=str(ROOT / "test_audit.jsonl"))
        self.assertEqual(res.decision, "refuse")

    def test_eval_harness_passes(self):
        results = run_eval(ROOT, verbose=False)
        failed = [r["id"] for r in results if not r["pass"]]
        self.assertEqual(failed, [], f"eval failures: {failed}")

    def test_audit_log_written(self):
        p = ROOT / "test_audit.jsonl"
        decide("What is the PTO carryover policy?",
               self.retr.search("What is the PTO carryover policy?"),
               self.backend, audit_path=str(p))
        self.assertTrue(p.exists())
        entry = json.loads(p.read_text().strip().split("\n")[-1])
        for k in ("ts", "query", "decision", "top_score", "citations",
                  "reason", "answer_sha256"):
            self.assertIn(k, entry)

    @classmethod
    def tearDownClass(cls):
        for f in ("test_audit.jsonl",):
            p = ROOT / f
            if p.exists():
                p.unlink()


if __name__ == "__main__":
    unittest.main()
