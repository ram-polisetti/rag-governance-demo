"""Tests for the domain-agnostic corpus: per-domain gate config, domain
isolation, and cross-domain refusal."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ingest import ingest
from retrieve import TfidfRetriever
from backends import StubBackend
from gate import decide, gate_config


class DomainGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = ingest(ROOT / "corpus")
        cls.by_domain = {}
        for c in cls.chunks:
            cls.by_domain.setdefault(c.domain, []).append(c)
        cls.backend = StubBackend()

    def test_default_config_unchanged(self):
        cfg = gate_config()
        self.assertEqual((cfg["refuse"], cfg["escalate"]), (0.10, 0.25))
        self.assertIn("salary", cfg["out_of_scope"])

    def test_hr_hiring_allows_salary_questions(self):
        # salary bands are a legitimate HR topic, not out-of-scope there
        cfg = gate_config("hr-hiring")
        self.assertNotIn("salary", cfg["out_of_scope"])
        self.assertNotIn("pto", cfg["out_of_scope"])
        retr = TfidfRetriever(self.by_domain["hr-hiring"])
        q = "What is the L4 compensation band?"
        res = decide(q, retr.search(q), self.backend,
                     audit_path=str(ROOT / "test_audit.jsonl"),
                     domain="hr-hiring")
        self.assertIn(res.decision, ("answer", "escalate"))

    def test_supply_chain_still_refuses_salary(self):
        cfg = gate_config("supply-chain")
        self.assertIn("salary", cfg["out_of_scope"])

    def test_unknown_domain_falls_back_to_default(self):
        cfg = gate_config("nonexistent-domain")
        self.assertEqual((cfg["refuse"], cfg["escalate"]), (0.10, 0.25))

    def test_cross_domain_query_refuses(self):
        # a supply-chain question asked of the lending domain: no evidence
        retr = TfidfRetriever(self.by_domain["lending"])
        q = "What is the cold-chain temperature range for pharmaceuticals?"
        res = decide(q, retr.search(q), self.backend,
                     audit_path=str(ROOT / "test_audit.jsonl"),
                     domain="lending")
        self.assertEqual(res.decision, "refuse")

    def test_audit_log_records_domain(self):
        import json
        p = ROOT / "test_audit.jsonl"
        if p.exists():
            p.unlink()
        retr = TfidfRetriever(self.by_domain["data-privacy"])
        q = "How quickly must a suspected breach be reported to the DPO?"
        decide(q, retr.search(q), self.backend, audit_path=str(p),
               domain="data-privacy")
        entry = json.loads(p.read_text().strip().split("\n")[-1])
        self.assertEqual(entry["domain"], "data-privacy")
        p.unlink()

    @classmethod
    def tearDownClass(cls):
        p = ROOT / "test_audit.jsonl"
        if p.exists():
            p.unlink()


if __name__ == "__main__":
    unittest.main()
