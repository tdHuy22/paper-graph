"""Gắn hình, bảng vào ô liên quan (figlinks.py) và dữ liệu hình trong trình xem."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from paper_graph import blocks as blocks_mod
from paper_graph import figlinks, view
from paper_graph import model as m
from paper_graph.check import parse_graph

from .helpers import blocks, graph, node


def related(g, b=None, anchor_blocks=None):
    parsed, _ = parse_graph(g)
    bl, errs = blocks_mod.parse(b or blocks())
    assert not errs, errs
    ab = anchor_blocks or {n.id: [a.block for a in n.anchors] for n in parsed.nodes.values()}
    return figlinks.link(parsed, bl, ab)


def whys(rel, nid):
    return [(r["id"], r["why"], r["via"]) for r in rel[nid]]


class Links(unittest.TestCase):
    def test_own_evidence_and_child(self):
        rel, shown = related(graph())
        self.assertEqual(whys(rel, "r.fig"), [("p2-f1", "own", "")])
        self.assertEqual(whys(rel, "r.claim"), [("p2-f1", "evidence", "r.fig")])  # cạnh supports r.fig → r.claim
        self.assertEqual(whys(rel, "result"), [("p2-f1", "own", "")])  # trùng với tầng dưới: giữ lý do đầu
        self.assertEqual(whys(rel, "problem"), [])
        self.assertEqual(shown["p2-f1"]["label"], "Hình 1")
        self.assertEqual(shown["p2-f1"]["nodes"], ["result", "r.fig"])

    def test_anchor_in_caption(self):
        g = graph()
        del node(g, "r.fig")["figure"]
        node(g, "r.fig")["label"] = "Thông lượng"
        rel, _ = related(g, anchor_blocks={"r.fig": ["p2-b3"]})  # câu trích nằm ở đoạn chú thích của p2-f1
        self.assertEqual(whys(rel, "r.fig"), [("p2-f1", "caption", "")])

    def test_mentions_match_number_and_kind(self):
        g = graph()
        node(g, "idea")["explain"] = "Như Fig. 1 cho thấy"
        node(g, "problem")["explain"] = "Xem Figure 10 và Bảng 1"  # không có Hình 10, không có bảng nào
        rel, _ = related(g)
        self.assertEqual(whys(rel, "idea"), [("p2-f1", "mention", "")])
        self.assertEqual(whys(rel, "problem"), [])

    def test_child_figures_reach_the_parent(self):
        g = graph()
        del node(g, "result")["figure"]
        rel, _ = related(g)
        self.assertEqual(whys(rel, "result"), [("p2-f1", "child", "r.fig")])

    def test_cap_per_node_and_unused_formulas_hidden(self):
        b = blocks()
        for k in range(10):
            b["blocks"].append({"id": f"p3-b{k}", "page": 2, "bbox": [72, 10, 80, 20], "label": "figure_title",
                                "text": f"Table {k + 2}: extra"})
            b["figures"].append({"id": f"p3-f{k}", "page": 2, "bbox": [72, 10, 80, 20], "kind": "table",
                                 "caption": f"p3-b{k}"})
        b["figures"].append({"id": "p3-eq", "page": 2, "bbox": [72, 10, 80, 20], "kind": "formula"})
        g = graph()
        node(g, "idea")["explain"] = " ".join(f"Bảng {k + 2}" for k in range(10))
        rel, shown = related(g, b)
        self.assertEqual(len(rel["idea"]), figlinks.MAX_PER_NODE)
        self.assertNotIn("p3-eq", shown)
        for fid, f in shown.items():  # review: link ngược chỉ tới ô thật sự hiện hình đó trong thẻ
            for nid in f["nodes"]:
                self.assertIn(fid, [r["id"] for r in rel[nid]], (fid, nid))
        self.assertEqual(shown["p3-f9"]["nodes"], [])

    def test_mention_forms(self):  # review: "Figure 1a", danh sách "Tables 1 and 2"
        def keys(text):
            return figlinks._mentions(m.Node("x", None, "idea", text))
        self.assertEqual(keys("Figure 1a shows"), {("figure", 1)})
        self.assertEqual(keys("Fig. 2(a)"), {("figure", 2)})
        self.assertEqual(keys("Tables 1 and 2"), {("table", 1), ("table", 2)})
        self.assertEqual(keys("Hình 1, 2 và 3"), {("figure", 1), ("figure", 2), ("figure", 3)})
        self.assertEqual(keys("Table 2, 3 layers"), {("table", 2)})
        self.assertEqual(keys("Figure 10"), {("figure", 10)})
        self.assertEqual(keys("tabled 3, figurehead 2"), set())

    def test_hostile_caption_is_only_data(self):  # TM-13: chú thích lấy từ blocks.json sửa tay
        b = blocks()
        cap = next(x for x in b["blocks"] if x["id"] == "p2-b3")
        cap["text"] += " </script><script>alert(1)</script> \u2028 x\ud800y " + "a" * 1000
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "toy.blocks.json").write_text(json.dumps(b), encoding="utf-8")
            (d / "toy.graph.json").write_text(json.dumps(graph()), encoding="utf-8")
            page, stats = view.build(d / "toy.graph.json", images=False)
        self.assertEqual(len(re.findall(r"<script", page)), 2)
        data = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1))
        caption = data["figures"]["p2-f1"]["caption"]
        self.assertIn("</script><script>alert(1)", caption)  # nguyên văn sau JSON.parse, nhưng không thành thẻ
        self.assertLessEqual(len(caption), figlinks.MAX_CAPTION)
        self.assertEqual(stats["figures"], 1)
        self.assertEqual(data["nodes"]["r.claim"]["figures"][0]["why"], "evidence")


if __name__ == "__main__":
    unittest.main()
