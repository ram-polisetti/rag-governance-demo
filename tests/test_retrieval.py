"""Tests for the dense embedding retriever and the A/B harness."""
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ingest import ingest
from retrieve import TfidfRetriever, EmbeddingRetriever
from embeddings import HashEmbedder
from eval import run_ab


class EmbedderTest(unittest.TestCase):
    def test_deterministic(self):
        e = HashEmbedder(dim=2048)
        self.assertEqual(e.embed("cold chain policy"), e.embed("cold chain policy"))

    def test_unit_norm_and_dim(self):
        e = HashEmbedder(dim=2048)
        v = e.embed("hazmat handling requirements")
        self.assertEqual(len(v), 2048)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in v)), 1.0, places=6)

    def test_similar_texts_score_higher(self):
        e = HashEmbedder(dim=2048)
        a = e.embed("forklift speed limit warehouse")
        b = e.embed("forklift speed warehouse")
        c = e.embed("customs export filing documentation")
        sab = sum(x * y for x, y in zip(a, b))
        sac = sum(x * y for x, y in zip(a, c))
        self.assertGreater(sab, sac)


class EmbeddingRetrieverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = ingest(ROOT / "corpus")
        cls.retr = EmbeddingRetriever(cls.chunks, HashEmbedder(dim=2048).embed)

    def test_interface_parity_with_tfidf(self):
        tfidf = TfidfRetriever(self.chunks)
        for retr in (tfidf, self.retr):
            scored = retr.search("forklift speed", top_k=3)
            self.assertEqual(len(scored), 3)
            scores = [s for s, _ in scored]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_finds_correct_doc(self):
        scored = self.retr.search(
            "What temperature range must pharmaceutical products be kept at?",
            top_k=3)
        self.assertIn("cold-chain-policy", scored[0][1].doc_id)

    def test_scores_in_cosine_range(self):
        scored = self.retr.search("hazmat", top_k=3)
        for s, _ in scored:
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0 + 1e-9)


class AbEvalTest(unittest.TestCase):
    def test_ab_runs_and_reports_hit_rate(self):
        summary = run_ab(ROOT, verbose=False)
        n_cases = len(json.loads(
            (ROOT / "evals" / "test_set.json").read_text()))
        for name in ("tfidf", "embed"):
            self.assertIn(name, summary)
            self.assertIn(name + "_hit_rate_at_1", summary)
            self.assertEqual(len(summary[name]), n_cases)


if __name__ == "__main__":
    unittest.main()
