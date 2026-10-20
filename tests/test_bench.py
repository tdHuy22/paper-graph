"""Sơ đồ mẫu của bộ đo phải sạch, và mỗi kiểu phá cài vào nó phải bị bắt đúng mã.

Cần blocks của bộ đo (không có trong git): ../pdf-translator/.venv/bin/python bench/prepare.py
"""
import copy
import json
import unittest
from pathlib import Path

from paper_graph import blocks as blocks_mod
from paper_graph import gold as gold_mod
from paper_graph.check import check, parse_graph, render

BENCH = Path(__file__).resolve().parents[1] / "bench" / "papers"


def load(name: str, suffix: str):
    p = BENCH / name / f"{name}.{suffix}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def run(g, blocks_doc):
    b, errs = blocks_mod.parse(blocks_doc)
    assert not errs, errs
    parsed, diags = parse_graph(g)
    return check(parsed, b, None, diags)


def codes(r):
    return sorted({d.code for d in r.diags if d.level == "error"})


KNOWN = [("PG309", "hình p9-f1")]  # cảnh báo đã biết của sơ đồ mẫu Attention, xem test_reference_is_clean


@unittest.skipIf(load("attention", "blocks") is None, "chưa có blocks của bộ đo: chạy bench/prepare.py")
class AttentionReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks = load("attention", "blocks")
        cls.graph = load("attention", "graph")

    def mutate(self, fn):
        g = copy.deepcopy(self.graph)
        fn(g)
        return run(g, self.blocks)

    def node(self, g, nid):
        return next(n for n in g["nodes"] if n["id"] == nid)

    def test_reference_is_clean(self):
        # PG309 Bảng 3 (thí nghiệm đổi kiến trúc) là chỗ thiếu đã biết của sơ đồ mẫu: giữ nguyên tới khi đo người đọc
        # thật, vì câu q10 của bộ câu hỏi hỏi đúng bảng đó (docs/do-hieu-bai.md)
        r = run(self.graph, self.blocks)
        self.assertEqual([(d.code, d.where) for d in r.diags], KNOWN, render(r, "attention"))
        self.assertEqual(r.stats["anchors_ok"], r.stats["anchors"])

    def test_sabotage(self):
        cases = {
            "fabricated quote": (lambda g: self.node(g, "idea")["anchors"][0].update(
                quote="we prove that attention is the optimal architecture for every task"), "PG201"),
            "quote on wrong page": (lambda g: self.node(g, "idea")["anchors"][0].update(page=2), "PG201"),
            "quote too short": (lambda g: self.node(g, "idea")["anchors"][0].update(quote="attention mechanisms"),
                                "PG202"),
            "anchor dropped": (lambda g: self.node(g, "why").update(anchors=[]), "PG200"),
            "dangling edge": (lambda g: g["edges"].append({"from": "idea", "to": "m.nope", "kind": "flow"}), "PG106"),
            "cross-tier edge": (lambda g: g["edges"].append({"from": "idea", "to": "m.out", "kind": "flow"}), "PG107"),
            "figure missing": (lambda g: self.node(g, "method").update(figure="p3-f9"), "PG207"),
            "tier overfull": (lambda g: g["nodes"].extend(
                {"id": f"extra{i}", "parent": "method", "kind": "step", "label": "x", "basis": "inference"}
                for i in range(2)), "PG300"),
            "other paper's sha": (lambda g: g["paper"].update(sha256=load("bert", "blocks")["source"]["sha256"]
                                                              if load("bert", "blocks") else "0" * 64), "PG206"),
        }
        for name, (fn, want) in cases.items():
            with self.subTest(name):
                self.assertIn(want, codes(self.mutate(fn)))

    def test_changed_number_is_flagged(self):  # TM-7 trên bài thật: số của Bảng 2 nằm trong chữ của vùng bảng
        r = self.mutate(lambda g: self.node(g, "r.table2_bleu").update(label="Bảng 2: BLEU 29,4 Anh–Đức, 41,8 Anh–Pháp"))
        self.assertEqual([(d.code, d.msg.rsplit(": ", 1)[-1]) for d in r.diags if (d.code, d.where) not in KNOWN],
                         [("PG220", "29,4")])

    def test_unbacked_claim_is_flagged(self):
        r = self.mutate(lambda g: g.update(edges=[e for e in g["edges"] if e["to"] != "r.general"]))
        self.assertIn("PG305", {d.code for d in r.diags})

    @unittest.skipIf(load("bert", "blocks") is None, "chưa có blocks của bert")
    def test_checked_against_another_paper(self):  # TM-3
        r = run(self.graph, load("bert", "blocks"))
        self.assertEqual(codes(r), ["PG206"])
        self.assertEqual(r.stats["anchors_ok"], 0)


class GoldFiles(unittest.TestCase):
    """Đáp án tay: đúng dạng, và mọi neo có thật trong bài (cần blocks của bộ đo)."""

    def test_gold_parses_and_anchors_exist(self):
        names = json.loads((BENCH.parent / "papers.json").read_text())["papers"]
        for p in names:
            with self.subTest(p["name"]):
                g, errs = gold_mod.parse(load(p["name"], "gold"))
                self.assertEqual(errs, [])
                self.assertEqual(g.sha256, p["sha256"])
                self.assertGreaterEqual(len(g.must), 8)
                blocks_doc = load(p["name"], "blocks")
                if blocks_doc is None:
                    self.skipTest("chưa có blocks: chạy bench/prepare.py")
                b, _ = blocks_mod.parse(blocks_doc)
                self.assertEqual(gold_mod.verify_anchors(g, b), [])

    @unittest.skipIf(load("attention", "blocks") is None, "chưa có blocks của bộ đo")
    def test_gold_fabricated_anchor_is_caught(self):  # review: verify_anchors chỉ được thử với đáp án đúng
        g, _ = gold_mod.parse(load("attention", "gold"))
        g.items["idea"].anchors[0].quote = "we prove attention is optimal for every possible task"
        b, _ = blocks_mod.parse(load("attention", "blocks"))
        errs = gold_mod.verify_anchors(g, b)
        self.assertEqual(len(errs), 1)
        self.assertIn("PG201", errs[0])

    def test_gold_anchor_on_scanned_page_counts_as_broken(self):  # review 2: PG210 trong đáp án
        import sys
        sys.path.insert(0, str(BENCH.parents[1]))
        from tests.helpers import SHA, blocks as toy_blocks

        doc = {"version": 1, "paper": {"name": "toy", "sha256": SHA},
               "items": [{"id": "a", "must": True, "tier": "top", "kinds": ["idea"], "terms": ["x"],
                          "anchors": [{"page": 3, "quote": "text that only exists on the scan"}]}]}
        g, errs = gold_mod.parse(doc)
        self.assertEqual(errs, [])
        b, _ = blocks_mod.parse(toy_blocks())
        self.assertEqual([e.split()[0] for e in gold_mod.verify_anchors(g, b)], ["PG210"])

    def test_gold_wrong_types_are_errors_not_crashes(self):  # review 2: V5
        base = load("attention", "gold")
        for mutate in (lambda g: g.update(items=5), lambda g: g.update(paper=[1]), lambda g: g.update(relations=7),
                       lambda g: g["items"][0].update(anchors=5),
                       lambda g: g["items"][0]["anchors"][0].update(block=["x"]),
                       lambda g: g["relations"][0].update({"from": ["problem"]})):
            g = copy.deepcopy(base)
            mutate(g)
            parsed, errs = gold_mod.parse(g)
            self.assertTrue(parsed is None and errs)

    def test_gold_rejects_broken_file(self):
        g = load("attention", "gold")
        g["items"][0]["tier"] = "under:nope"
        g["relations"].append({"from": "problem", "to": "ghost"})
        _, errs = gold_mod.parse(g)
        self.assertEqual(len(errs), 2, errs)


if __name__ == "__main__":
    unittest.main()
