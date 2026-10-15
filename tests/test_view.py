"""Bố cục (layout.py) và trình xem HTML tự chứa (view.py): TM-13..TM-15 ở `.agent/threat-model.md`."""
import base64
import contextlib
import hashlib
import io
import itertools
import json
import re
import tempfile
import unittest
from pathlib import Path

from paper_graph import cli, layout, view
from paper_graph.check import parse_graph
from paper_graph.files import InputError, read_json

from .helpers import SHA, blocks, graph, node

ROOT = Path(__file__).resolve().parents[1]
ATTENTION = ROOT / "bench/papers/attention/attention.graph.json"


def overlaps(a, b) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def inside(a, outer) -> bool:
    return (outer["x"] <= a["x"] and a["x"] + a["w"] <= outer["x"] + outer["w"] and outer["y"] <= a["y"]
            and a["y"] + a["h"] <= outer["y"] + outer["h"])


def reading_key(b) -> tuple:
    return round(b["y"] + b["h"] / 2, 1), b["x"]


class Layout(unittest.TestCase):
    def check_tiers(self, g):
        tiers = layout.layout_graph(g)
        self.assertEqual(set(tiers), {"" if n.parent is None else n.parent for n in g.nodes.values()})
        for key, t in tiers.items():
            members = {n.id for n in g.nodes.values() if (n.parent or "") == key}
            self.assertEqual(set(t["nodes"]), members, key)
            self.assertEqual(sorted(t["order"]), sorted(members), key)  # thứ tự đọc: đủ mỗi ô một lần
            boxes = t["nodes"]
            canvas = {"x": 0, "y": 0, "w": t["width"], "h": t["height"]}
            for (i, a), (j, b) in itertools.combinations(boxes.items(), 2):
                self.assertFalse(overlaps(a, b), f"{key}: {i} chồng {j}")
            for i, b in boxes.items():
                self.assertTrue(inside(b, canvas), f"{key}: {i} ra ngoài khung")
            grouped = set()
            for gr in t["groups"]:
                own = set(next(x for x in g.groups if x.id == gr["id"]).members)
                grouped |= own
                self.assertTrue(inside(gr, canvas), f"{key}: nhóm {gr['id']} ra ngoài khung")
                head = layout.GROUP_PAD + layout.GROUP_LABEL_H + layout.GROUP_LINE_H * (len(gr["lines"]) - 1)
                for line in gr["lines"]:  # nhãn nhóm nằm trong khung
                    self.assertLessEqual(len(line) * layout.CHAR_W, gr["w"] - 2 * layout.GROUP_PAD, gr["id"])
                for i, b in boxes.items():
                    if i in own:
                        self.assertTrue(inside(b, gr), f"{key}: {i} ra ngoài nhóm {gr['id']}")
                        self.assertGreaterEqual(b["y"], gr["y"] + head, f"{key}: {i} đè nhãn nhóm {gr['id']}")
                    else:
                        self.assertFalse(overlaps(b, gr), f"{key}: nhóm {gr['id']} trùm ô ngoài {i}")
                inner = [i for i in t["order"] if i in own]  # trong nhóm: liền nhau, theo hàng rồi trái sang phải
                start = t["order"].index(inner[0])
                self.assertEqual(t["order"][start:start + len(inner)], inner, gr["id"])
                self.assertEqual(inner, sorted(inner, key=lambda i: reading_key(boxes[i])), gr["id"])
            loose = [i for i in t["order"] if i not in grouped]
            self.assertEqual(loose, sorted(loose, key=lambda i: reading_key(boxes[i])), key)
            for e in t["edges"]:
                self.assertIn(e["shape"], ("down", "up", "side"))
        return tiers

    def test_reference_graph_has_clean_layout_and_is_deterministic(self):
        g, _ = parse_graph(read_json(ATTENTION, "sơ đồ"))
        first = self.check_tiers(g)
        self.assertEqual(first, layout.layout_graph(g))
        top = first[""]["nodes"]
        self.assertLess(top["problem"]["y"], top["idea"]["y"])  # mạch chính từ trên xuống

    def test_reading_order_follows_the_picture(self):  # review: Tab theo nhóm, không theo hình
        g, _ = parse_graph(read_json(ATTENTION, "sơ đồ"))
        order = layout.layout_graph(g)["method"]["order"]
        self.assertEqual(set(order[:2]), {"m.src", "m.tgt"})  # hai ô đầu vào ở hàng trên cùng
        self.assertEqual(order[-1], "m.out")

    def test_node_id_shaped_like_a_group_key(self):  # review: ô `g:grp` trùng khoá nội bộ của nhóm `grp`
        g = graph()
        node(g, "problem")["id"] = "g:grp"
        g["edges"][0]["from"] = "g:grp"
        g["nodes"].append({"id": "n", "parent": None, "kind": "context", "label": "Ô tên n",
                           "anchors": [{"page": 1, "quote": "A Toy Paper on Widgets"}]})
        g["groups"] = [{"id": "grp", "parent": None, "label": "Nhóm", "members": ["idea"]}]
        parsed, _ = parse_graph(g)
        self.check_tiers(parsed)

    def test_long_group_label_wraps_inside_its_frame(self):  # review: nhãn nhóm tràn khung
        g = graph()
        g["groups"] = [{"id": "grp", "parent": None, "label": "Tinh chỉnh dữ liệu có nhãn của từng việc " * 3,
                        "members": ["idea"]}]
        parsed, _ = parse_graph(g)
        gr = self.check_tiers(parsed)[""]["groups"][0]
        self.assertGreater(len(gr["lines"]), 1)
        self.assertLessEqual(len(gr["lines"]), layout.MAX_LINES)

    def test_cycles_and_isolated_nodes(self):
        g = graph()
        g["edges"].append({"from": "result", "to": "problem", "kind": "relates", "label": "vòng"})
        parsed, _ = parse_graph(g)
        self.check_tiers(parsed)

    def test_wrap(self):
        self.assertEqual(layout.wrap("một hai ba bốn", 7), ["một hai", "ba bốn"])
        self.assertEqual(len(layout.wrap("x " * 200, 10)), layout.MAX_LINES)
        self.assertTrue(layout.wrap("x " * 200, 10)[-1].endswith("…"))
        self.assertEqual(layout.wrap("a" * 25, 10), ["a" * 10, "a" * 10, "a" * 5])


class View(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "toy.blocks.json").write_text(json.dumps(blocks()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, g, **kw) -> str:
        p = self.d / "toy.graph.json"
        p.write_text(json.dumps(g), encoding="utf-8")
        page, _ = view.build(p, images=False, **kw)
        return page

    def data_of(self, page: str) -> dict:
        m = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S)
        return json.loads(m.group(1))

    def test_hostile_labels_cannot_escape_the_data_block(self):  # TM-13
        g = graph()
        evil = '</script><script>alert(1)</script><!-- <img src=x onerror=alert(2)>   & {{SCRIPT}}'
        node(g, "idea")["label"] = "ý " + evil[:50]
        node(g, "idea")["explain"] = evil
        g["paper"]["title"] = '</title><script>alert(3)</script>'
        page = self.build(g)
        self.assertEqual(len(re.findall(r"<script", page)), 2)  # khối dữ liệu và đúng một script
        self.assertNotIn("<img src=x", page)
        self.assertNotIn(" ", page)
        self.assertIn("<title>&lt;/title&gt;&lt;script&gt;", page)
        data = self.data_of(page)
        self.assertEqual(data["nodes"]["idea"]["explain"], evil)  # dữ liệu nguyên vẹn sau khi thoát
        for slot in ("{{CSP}}", "{{TITLE}}", "{{STYLE}}", "{{DATA}}"):
            self.assertNotIn(slot, page)
        self.assertEqual(page.count("{{SCRIPT}}"), 1)  # chỉ còn trong dữ liệu, như chữ: không bị thay thành mã

    def test_csp_pins_the_inline_script_and_style(self):  # TM-14
        page = self.build(graph())
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page).group(1)
        self.assertIn("default-src 'none'", csp)
        self.assertIn("img-src data:", csp)
        self.assertNotIn("unsafe", csp)
        script = re.findall(r"<script>(.*?)</script>", page, re.S)[0]
        style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
        for text in (script, style):
            digest = base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode()
            self.assertIn(f"'sha256-{digest}'", csp)
        outside_data = re.sub(r'<script type="application/json" id="data">.*?</script>', "", page, flags=re.S)
        self.assertNotRegex(outside_data, r"https?://(?!www\.w3\.org/2000/svg)")

    def test_viewer_script_never_writes_markup(self):  # TM-13
        js = (ROOT / "paper_graph/viewer/viewer.js").read_text("utf-8")
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function",
                    "setAttribute(\"on", "setAttribute('on", "srcdoc", "javascript:"):
            self.assertNotIn(bad, js)

    def test_lone_surrogate_is_refused(self):  # review: qua `check` nhưng `view` văng UnicodeEncodeError
        g = graph()
        node(g, "idea")["explain"] = "x\ud800y"
        with self.assertRaises(InputError):
            self.build(g)
        p = self.d / "toy.graph.json"
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["view", str(p), "--no-images"]), 2)

    def test_view_does_not_follow_a_planted_tmp_symlink(self):  # TM-9: thư mục bài tải về có sẵn `toy.html.tmp`
        victim = self.d / "victim.txt"
        victim.write_text("giữ nguyên", encoding="utf-8")
        (self.d / "toy.graph.json").write_text(json.dumps(graph()), encoding="utf-8")
        (self.d / "toy.html.tmp").symlink_to(victim)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["view", str(self.d / "toy.graph.json"), "--no-images"]), 0)
        self.assertEqual(victim.read_text(encoding="utf-8"), "giữ nguyên")
        out = self.d / "toy.html"
        self.assertFalse(out.is_symlink())
        self.assertTrue(out.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_graph_with_errors_is_refused(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "this sentence is not in the toy paper at all"}]
        with self.assertRaises(InputError):
            self.build(g)

    def test_data_has_tiers_children_and_anchor_blocks(self):
        data = self.data_of(self.build(graph()))
        self.assertEqual(set(data["tiers"]), {"", "result"})
        self.assertEqual(data["tiers"][""]["order"], ["problem", "idea", "result"])
        self.assertEqual(data["nodes"]["result"]["children"], 2)
        self.assertEqual(data["nodes"]["idea"]["anchors"][0]["block"], "p1-b2")
        self.assertEqual(data["images"], {})
        self.assertEqual(data["sha256"], SHA)


try:
    import pymupdf
except ImportError:
    pymupdf = None


@unittest.skipIf(pymupdf is None, "cần Python của VietPaper: ../pdf-translator/.venv/bin/python")
class ViewImages(unittest.TestCase):
    def test_images_are_png_data_uris_cut_from_the_matching_pdf(self):  # TM-15
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            doc = pymupdf.open()
            for _ in range(2):
                page = doc.new_page(width=612, height=792)
                page.insert_text((80, 120), "toy page text", fontsize=12)
            doc.save(d / "toy.pdf")
            b = blocks()
            b["source"]["sha256"] = hashlib.sha256((d / "toy.pdf").read_bytes()).hexdigest()
            b["pages"] = [b["pages"][0], b["pages"][1]]
            b["pages"][1]["text"] = True
            b["blocks"] = [x for x in b["blocks"] if x["page"] in (1, 2)]
            (d / "toy.blocks.json").write_text(json.dumps(b), encoding="utf-8")
            g = graph()
            g["paper"]["sha256"] = b["source"]["sha256"]
            (d / "toy.graph.json").write_text(json.dumps(g), encoding="utf-8")
            page, stats = view.build(d / "toy.graph.json")
            data = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1))
            self.assertGreater(stats["images"], 0)
            for uri in data["images"].values():
                self.assertTrue(uri.startswith("data:image/png;base64,iVBORw0KGgo"))
            self.assertIn("p2-f1", data["images"])  # hình của ô `result`

            # review: một vùng hỏng (bbox ngoài trang) chỉ mất ảnh của vùng đó, có báo ở chân trang
            b["figures"].append({"id": "p1-f9", "page": 1, "bbox": [5000, 5000, 5100, 5100], "kind": "chart"})
            (d / "toy.blocks.json").write_text(json.dumps(b), encoding="utf-8")
            page, stats = view.build(d / "toy.graph.json")
            data = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1))
            self.assertIn("p2-f1", data["images"])
            self.assertNotIn("p1-f9", data["images"])
            self.assertIn("p1-f9", stats["note"])


if __name__ == "__main__":
    unittest.main()
