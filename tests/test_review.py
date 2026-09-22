"""Tests for the human review queue."""
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
from review import collect, decide_review, load_queue


class ReviewQueueTest(unittest.TestCase):
    def setUp(self):
        self.audit = ROOT / "test_review_audit.jsonl"
        if self.audit.exists():
            self.audit.unlink()
        chunks = ingest(ROOT / "corpus")
        retr = TfidfRetriever(chunks)
        # edge-1 escalates under TF-IDF (score ~0.212)
        decide("Tell me about storage and handling requirements for warehouse goods.",
               retr.search("Tell me about storage and handling requirements for warehouse goods."),
               StubBackend(), audit_path=str(self.audit))

    def test_collect_pulls_escalations(self):
        n = collect(ROOT, str(self.audit))
        self.assertEqual(n, 1)
        # collecting twice must not duplicate
        self.assertEqual(collect(ROOT, str(self.audit)), 0)

    def test_decide_records_verdict_and_audits(self):
        collect(ROOT, str(self.audit))
        item = load_queue(ROOT)["items"][0]
        rec = decide_review(ROOT, item["id"], "approved", note="ok",
                            audit_path=str(self.audit))
        self.assertEqual(rec["verdict"], "approved")
        last = json.loads(self.audit.read_text().strip().split("\n")[-1])
        self.assertEqual(last["decision"], "review_decision")
        self.assertIn(item["id"], last["reason"])
        with self.assertRaises(ValueError):
            decide_review(ROOT, item["id"], "approved",
                          audit_path=str(self.audit))

    def test_rejects_bad_verdict(self):
        collect(ROOT, str(self.audit))
        item = load_queue(ROOT)["items"][0]
        with self.assertRaises(ValueError):
            decide_review(ROOT, item["id"], "maybe",
                          audit_path=str(self.audit))

    def tearDown(self):
        for f in ("test_review_audit.jsonl", "review_queue.json",
                  "review_queue.md", "review_decisions.jsonl"):
            p = ROOT / f
            if p.exists():
                p.unlink()


if __name__ == "__main__":
    unittest.main()
