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


class Probes(unittest.TestCase):
    """Điểm soi: cạnh đúng loại và mức giữa hai phía; ô nêu đủ số và từ của chỗ bài tự lệch."""

    EDGE = {"id": "fig_strength", "type": "edge", "kind": "supports", "strength": ["strong"],
            "from": {"figures": ["p2-f1"]},
            "to": {"anchors": [{"page": 2, "quote": "a measured speedup of four times"}]}}
    NOTE = {"id": "bleu_steps", "type": "note", "numbers": [["28.4"], ["100000", "1e5"]], "words": [["BLEU"]],
            "at": {"anchors": [{"page": 2, "quote": "The flat widget reaches 28.4 BLEU"}]}}

    def run_probes(self, g, *probes):
        b, _ = blocks_mod.parse(blocks())
        gold, errs = gold_mod.parse({**GOLD, "probes": list(probes)})
        self.assertEqual(errs, [])
        parsed, _ = parse_graph(g)
        return {pid: (ok, why) for pid, ok, why in score_mod.score(parsed, gold, b).probes}

    def test_edge_kind_strength_and_direction(self):
        self.assertTrue(self.run_probes(graph(), self.EDGE)["fig_strength"][0])
        ok, why = self.run_probes(graph(), {**self.EDGE, "strength": ["moderate", "weak"]})["fig_strength"]
        self.assertEqual((ok, why), (False, "mức strong, mong moderate hay weak"))
        ok, why = self.run_probes(graph(), {**self.EDGE, "kind": "contradicts"})["fig_strength"]
        self.assertFalse(ok)
        self.assertIn("supports", why)
        g = graph()
        g["edges"][2].update({"from": "r.claim", "to": "r.fig"})  # cạnh ngược chiều: tuyên bố → bằng chứng
        self.assertFalse(self.run_probes(g, self.EDGE)["fig_strength"][0])
        g = graph()
        for x in ("r.fig", "result"):
            node(g, x)["figure"] = None  # không ô nào khớp phía from
        self.assertEqual(self.run_probes(g, self.EDGE)["fig_strength"], (False, "không ô nào khớp phía from"))

    def test_note_needs_every_number_and_word_group(self):
        g = graph()
        g["nodes"].append({"id": "r.bleu", "parent": "result", "kind": "evidence", "label": "BLEU 28,4",
                           "explain": "Đạt 28,4 BLEU sau 100.000 bước.",
                           "anchors": [{"page": 2, "quote": "The flat widget reaches 28.4 BLEU"}]})
        self.assertEqual(self.run_probes(g, self.NOTE)["bleu_steps"], (True, "ô r.bleu"))
        node(g, "r.bleu")["explain"] = "Đạt 28,4 BLEU."  # thiếu số của nhóm thứ hai
        self.assertFalse(self.run_probes(g, self.NOTE)["bleu_steps"][0])
        node(g, "r.bleu")["explain"] = "Đạt 28,4 điểm sau 100.000 bước."
        node(g, "r.bleu")["label"] = "Điểm dịch"  # thiếu từ BLEU
        self.assertFalse(self.run_probes(g, self.NOTE)["bleu_steps"][0])
        self.assertEqual(self.run_probes(graph(), self.NOTE)["bleu_steps"], (False, "không ô nào neo vào chỗ đó"))

    def test_bad_probes_are_errors_not_crashes(self):
        bad = [{"id": "a", "type": "vote"}, {"id": "b", "type": "edge"}, {"id": "c", "type": "note", "at": {}},
               {"id": "d", "type": "note", "at": {"figures": ["p2-f1"]}},
               {"id": "e", "type": "note", "at": {"figures": ["p2-f1"]}, "numbers": [["nhiều"]]},
               {"id": "f", "type": "edge", "from": {"figures": ["p2-f1"]}, "strength": ["high"]},
               {"id": "g", "type": "edge", "from": {"figures": ["<x>"]}}, "not a probe", {"id": 5},
               {"id": "h", "type": "edge", "from": {"figures": ["p2-f1"]}, "kind": ["supports"]},
               {"id": "i", "type": "edge", "from": {"figures": ["p2-f1"]}, "strength": [["strong"]]},
               {"id": "j", "type": "edge", "from": {"figures": ["p2-f1"]}, "kind": {"a": 1}}]
        for p in bad:
            gold, errs = gold_mod.parse({**GOLD, "probes": [p]})
            self.assertIsNone(gold, p)
            self.assertTrue(errs, p)
        self.assertTrue(gold_mod.parse({**GOLD, "probes": [self.EDGE, self.EDGE]})[1])  # id trùng
        self.assertTrue(gold_mod.parse({**GOLD, "probes": "x"})[1])

    def test_probe_anchors_and_figures_must_exist(self):
        b, _ = blocks_mod.parse(blocks())
        fake = {**self.NOTE, "at": {"anchors": [{"page": 2, "quote": "The flat widget reaches 99.9 BLEU"}],
                                    "figures": ["p9-f9"]}}
        gold, errs = gold_mod.parse({**GOLD, "probes": [fake]})
        self.assertEqual(errs, [])
        problems = gold_mod.verify_anchors(gold, b)
        self.assertTrue(any("PG201" in x and "bleu_steps" in x for x in problems), problems)
        self.assertTrue(any("p9-f9" in x for x in problems), problems)


if __name__ == "__main__":
    unittest.main()
