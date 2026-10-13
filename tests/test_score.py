"""Bộ chấm theo đáp án tay (docs/bench.md): khớp theo đoạn hay thuật ngữ, độ phủ, đúng tầng, quan hệ."""
import unittest

from paper_graph import blocks as blocks_mod
from paper_graph import gold as gold_mod
from paper_graph import score as score_mod
from paper_graph.check import parse_graph

from .helpers import SHA, blocks, graph, node

GOLD = {
    "version": 1,
    "paper": {"name": "toy", "sha256": SHA},
    "items": [
        {"id": "problem", "must": True, "tier": "top", "kinds": ["problem"], "terms": ["recurrent"],
         "anchors": [{"page": 1, "quote": "which precludes parallelization within a sequence"}]},
        {"id": "idea", "must": True, "tier": "top", "kinds": ["idea", "method"], "terms": ["flat widget"],
         "anchors": [{"page": 1, "quote": "We propose the flat widget"}]},
        {"id": "speed", "must": True, "tier": "under:result", "kinds": ["claim", "evidence", "result"],
         "terms": ["speedup"], "anchors": [{"page": 2, "quote": "with a measured speedup of four times"}]},
        {"id": "result", "must": False, "tier": "top", "kinds": ["result"], "terms": ["four times"],
         "anchors": [{"page": 2, "quote": "with a measured speedup of four times"}]},
    ],
    "relations": [{"from": "problem", "to": "idea"}, {"from": "speed", "to": "result", "ancestor_ok": True}],
}


def run(g):
    b, _ = blocks_mod.parse(blocks())
    gold, errs = gold_mod.parse(GOLD)
    assert not errs, errs
    parsed, _ = parse_graph(g)
    return score_mod.score(parsed, gold, b)


class Score(unittest.TestCase):
    def test_full_match(self):
        sc = run(graph())
        self.assertEqual(sc.summary()["coverage"], 1.0)
        self.assertEqual(sc.summary()["tier"], 1.0)
        self.assertEqual(sc.relation_rate, 1.0)

    def test_missing_item_lowers_coverage(self):
        g = graph()
        g["nodes"] = [n for n in g["nodes"] if n["id"] != "problem"]
        g["edges"] = [e for e in g["edges"] if e["from"] != "problem"]
        sc = run(g)
        self.assertAlmostEqual(sc.coverage, 2 / 3)
        self.assertEqual([i.id for i in sc.items if i.must and not i.matched], ["problem"])
        self.assertIn(("problem", "idea", False), sc.relations)

    def test_kind_must_fit(self):
        g = graph()
        node(g, "problem")["kind"] = "context"  # đúng đoạn nhưng sai loại ô
        self.assertEqual(next(i for i in run(g).items if i.id == "problem").matched, [])

    def test_term_match_without_shared_block(self):
        g = graph()
        node(g, "problem").update(anchors=[{"page": 2, "quote": "Throughput of the flat widget compared"}],
                                  explain="Recurrent widgets đọc từng token.")
        it = next(i for i in run(g).items if i.id == "problem")
        self.assertEqual((it.matched, it.how), (["problem"], "thuật ngữ"))

    def test_wrong_tier(self):
        g = graph()
        node(g, "r.claim")["parent"] = None  # tuyên bố nhảy lên tầng đầu, ra khỏi cây con của result
        g["edges"] = [e for e in g["edges"] if e["kind"] != "supports"]
        node(g, "r.fig")["parent"] = None
        it = next(i for i in run(g).items if i.id == "speed")
        self.assertTrue(it.matched)
        self.assertFalse(it.tier_ok)


if __name__ == "__main__":
    unittest.main()
