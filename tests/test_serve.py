"""Sửa trên sơ đồ: edits.py (TM-18, TM-20), bố cục có ô ghim, và server cục bộ serve.py (TM-16, TM-17, TM-19)."""
import hashlib
import http.client
import itertools
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path

from paper_graph import blocks as blocks_mod
from paper_graph import edits, layout
from paper_graph.check import parse_graph
from paper_graph.serve import App, make_server

from paper_graph.files import format_graph, read_json

from .helpers import blocks, graph, node

ATTENTION = Path(__file__).resolve().parents[1] / "bench/papers/attention/attention.graph.json"


def parsed(g):
    out, _ = parse_graph(g)
    return out


class Edits(unittest.TestCase):
    def setUp(self):
        self.bl, _ = blocks_mod.parse(blocks())

    def test_text_edit_sets_accepted_and_keeps_other_fields(self):
        new = edits.edit_node(graph(), "idea", {"label": "  Xử lý mọi từ cùng lúc ", "term": ""}, self.bl)
        n = node(new, "idea")
        self.assertEqual(n["label"], "Xử lý mọi từ cùng lúc")
        self.assertEqual(n["status"], "accepted")
        self.assertNotIn("term", n)
        self.assertEqual(n["anchors"], node(graph(), "idea")["anchors"])

    def test_refused_edits(self):  # TM-18
        g = graph()
        node(g, "result")["status"] = "locked"
        cases = [("idea", {"anchors": []}), ("idea", {"kind": "result"}), ("nope", {"label": "x"}),
                 ("../x", {"label": "x"}), ("idea", {"label": ""}), ("idea", {"label": "x" * 500}),
                 ("idea", {"status": "done"}), ("idea", {"status": []}), ("idea", {"status": {}}),
                 ("idea", {"label": 5}), ("idea", {}), ("idea", []),
                 ("result", {"label": "Nhanh hơn"}),  # ô khoá
                 ("idea", {"label": "Nhanh hơn 99 lần"})]  # số không có trong câu trích (PG220)
        for nid, ch in cases:
            with self.subTest(nid=nid, ch=ch), self.assertRaises(edits.EditError):
                edits.edit_node(g, nid, ch, self.bl)
        with self.assertRaises(edits.EditError) as cm:
            edits.edit_node(g, "idea", {"label": "Nhanh hơn 99 lần"}, self.bl)
        self.assertTrue(any(d.startswith("PG220") for d in cm.exception.diags))

    def test_lock_and_unlock(self):
        g = edits.edit_node(graph(), "idea", {"status": "locked"}, self.bl)
        self.assertEqual(node(g, "idea")["status"], "locked")
        g = edits.edit_node(g, "idea", {"status": "accepted"}, self.bl)
        self.assertEqual(node(g, "idea")["status"], "accepted")

    def test_pins_file_is_checked(self):  # TM-20
        g = parsed(graph())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "toy.layout.json"
            p.write_text('{"sha256": "%s", "tiers": {"": {"idea": [40, 50], "problem": [NaN, 1], "result": [-1, 2], '
                         '"r.fig": [1, 2], "ghost": [1, 1], "x": "y"}, "result": {"r.fig": [1e308, 0]}, '
                         '"nope": {}}}' % g.sha256)
            pins, warn = edits.read_pins(p, g)
            self.assertEqual(pins, {"": {"idea": (40.0, 50.0)}})
            self.assertIn("bỏ", warn)
            p.write_text(json.dumps({"sha256": "b" * 64, "tiers": {"": {"idea": [1, 1]}}}))
            self.assertEqual(edits.read_pins(p, g)[0], {})
            edits.write_pins(p, g, {"": {"idea": (8.0, 16.0)}})
            self.assertEqual(edits.read_pins(p, g), ({"": {"idea": (8.0, 16.0)}}, ""))

    def test_move_validates(self):
        g = parsed(graph())
        for tier, moves in [("nope", {"idea": [1, 1]}), ("", {"r.fig": [1, 1]}), ("", {"idea": [float("nan"), 1]}),
                            ("", {"idea": [1, 1e9]}), ("", {"idea": [True, 1]}), ("", {}), ("", {"idea": "1,1"})]:
            with self.subTest(tier=tier, moves=moves), self.assertRaises(edits.EditError):
                edits.move({}, g, tier, moves)
        pins = edits.move({}, g, "", {"idea": [400, 8]})
        self.assertEqual(pins, {"": {"idea": (400.0, 8.0)}})
        self.assertEqual(edits.move(pins, g, "", None), {})


class PinnedLayout(unittest.TestCase):
    def check(self, g, pins, exact=True):
        tiers = layout.layout_graph(g, pins)
        for key, t in tiers.items():
            boxes = t["nodes"]
            sh = t["shift"]
            for nid, (x, y) in (pins.get(key) or {}).items():
                if not exact:
                    continue
                self.assertEqual((boxes[nid]["x"] - sh[0], boxes[nid]["y"] - sh[1]), (x, y), nid)
            for (i, a), (j, b) in itertools.combinations(boxes.items(), 2):
                self.assertFalse(a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"]
                                 and b["y"] < a["y"] + a["h"], f"{i} chồng {j}")
            for i, b in boxes.items():
                self.assertGreaterEqual(min(b["x"], b["y"]), 0)
                self.assertLessEqual(b["x"] + b["w"], t["width"])
                self.assertLessEqual(b["y"] + b["h"], t["height"])
            for gr in t["groups"]:
                members = next(x for x in g.groups if x.id == gr["id"]).members
                for i in members:
                    b = boxes[i]
                    self.assertTrue(gr["x"] <= b["x"] and b["x"] + b["w"] <= gr["x"] + gr["w"] and gr["y"] <= b["y"]
                                    and b["y"] + b["h"] <= gr["y"] + gr["h"], f"{i} ra ngoài nhóm")
                for i, b in boxes.items():  # review: khung nhóm không trùm ô chưa ghim của nhóm khác
                    if i not in members and i not in t["pinned"]:
                        self.assertFalse(b["x"] < gr["x"] + gr["w"] and gr["x"] < b["x"] + b["w"] and b["y"] < gr["y"]
                                         + gr["h"] and gr["y"] < b["y"] + b["h"], f"{key}: nhóm {gr['id']} trùm {i}")
            self.assertEqual(sorted(t["order"]), sorted(boxes))
        return tiers

    def test_pin_on_top_of_auto_nodes_pushes_them_aside(self):
        g = parsed(graph())
        auto = layout.layout_graph(g)[""]["nodes"]
        target = (auto["problem"]["x"], auto["problem"]["y"])  # đặt `result` đúng chỗ của `problem`
        t = self.check(g, {"": {"result": target}})[""]
        self.assertEqual(t["pinned"], ["result"])

    def test_pinned_group_member_near_the_top(self):
        gd = graph()
        gd["groups"] = [{"id": "grp", "parent": None, "label": "Nhóm có nhãn dài " * 4, "members": ["idea", "result"]}]
        t = self.check(parsed(gd), {"": {"idea": (0.0, 0.0), "problem": (600.0, 0.0)}})[""]
        self.assertGreater(t["shift"][1], 0)  # khung nhóm nhô lên trên ô ghim: cả tầng dịch xuống

    def test_dragging_a_member_out_never_swallows_other_nodes(self):  # review: khung nhóm phình ra trùm ô khác
        g = parsed(read_json(ATTENTION, "sơ đồ"))
        auto = layout.layout_graph(g)
        for key, t in auto.items():
            if not t["groups"]:
                continue
            spots = [(x, y) for x in (0, 200, 400, 640) for y in (0, 120, 300, 520)]
            for gr in t["groups"]:
                member = next(x for x in g.groups if x.id == gr["id"]).members[0]
                for xy in spots:
                    with self.subTest(key=key, member=member, xy=xy):
                        self.check(g, {key: {member: (float(xy[0]), float(xy[1]))}})

    def test_pins_that_collide_are_separated(self):  # review: nhãn sửa dài ra làm hai ô ghim chồng nhau
        g = parsed(graph())
        t = self.check(g, {"": {"problem": (40.0, 40.0), "idea": (40.0, 60.0)}}, exact=False)[""]
        self.assertEqual(t["nodes"]["problem"]["y"] - t["shift"][1], 40.0)  # ô đầu theo thứ tự giữ chỗ, ô sau dời xuống

    def test_no_pins_same_as_before(self):
        g = parsed(graph())
        self.assertEqual(layout.layout_graph(g, {}), layout.layout_graph(g))


class Server(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "toy.blocks.json").write_text(json.dumps(blocks()), encoding="utf-8")
        g = graph()
        node(g, "result")["status"] = "locked"
        self.gp = self.d / "toy.graph.json"
        self.gp.write_text(format_graph(g), encoding="utf-8")
        self.app = App(self.gp, None, None, images=False, crops=False)
        self.srv = make_server(self.app, 0)
        self.port = self.app.port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def req(self, method, path, body=None, **headers):
        h = {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "X-PG-Token": self.app.token}
        h.update({k.replace("_", "-"): v for k, v in headers.items()})
        h = {k: v for k, v in h.items() if v is not None}
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        data = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
        conn.request(method, path, body=data, headers=h)
        r = conn.getresponse()
        out = (r.status, dict(r.getheaders()), r.read())
        conn.close()
        return out

    def version(self):
        return hashlib.sha256(self.gp.read_bytes()).hexdigest()

    def edit(self, set_, nid="idea", **headers):
        return self.req("POST", "/api/edit", {"version": self.version(), "node": nid, "set": set_}, **headers)

    def test_page_has_token_and_strict_headers(self):
        code, h, body = self.req("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"])
        self.assertIn("connect-src 'self'", h["Content-Security-Policy"])
        self.assertEqual(h["X-Frame-Options"], "DENY")
        data = json.loads(re.search(rb'id="data">(.*?)</script>', body, re.S).group(1))
        self.assertEqual(data["edit"], {"token": self.app.token, "version": self.version()})

    def test_wrong_host_is_refused_everywhere(self):  # TM-17: DNS rebinding
        for method, path in (("GET", "/"), ("POST", "/api/edit")):
            code, _, body = self.req(method, path, {"version": self.version(), "node": "idea", "set": {"label": "x"}},
                                     Host="evil.example:%d" % self.port)
            self.assertEqual(code, 403, method)
            self.assertNotIn(self.app.token.encode(), body)
        self.assertEqual(self.req("GET", "/toy.graph.json")[0], 404)  # không phục vụ file theo đường dẫn

    def test_cross_site_requests_are_refused(self):  # TM-16
        before = self.gp.read_bytes()
        bad = [dict(X_PG_Token=None), dict(X_PG_Token="x" * 43), dict(X_PG_Token="é".encode("latin-1").decode("latin-1")),
               dict(Origin="https://evil.example"),
               dict(Origin="null"), dict(Sec_Fetch_Site="cross-site"), dict(Content_Type="text/plain"),
               dict(Content_Type="application/x-www-form-urlencoded")]
        for h in bad:
            with self.subTest(h=h):
                code, _, _ = self.edit({"label": "Bị sửa"}, **h)
                self.assertIn(code, (403, 415))
        code, _, _ = self.req("POST", "/api/edit", b"x" * (70 * 1024))
        self.assertEqual(code, 413)
        self.assertEqual(self.gp.read_bytes(), before)

    def test_edit_lock_and_refusals(self):  # TM-18
        code, _, body = self.edit({"label": "Xử lý mọi từ cùng lúc"}, Origin=f"http://127.0.0.1:{self.port}",
                                  Sec_Fetch_Site="same-origin")
        self.assertEqual(code, 200, body)
        reply = json.loads(body)
        self.assertEqual(reply["nodes"]["idea"]["label"], "Xử lý mọi từ cùng lúc")
        self.assertEqual(reply["version"], self.version())
        self.assertEqual(node(json.loads(self.gp.read_text("utf-8")), "idea")["status"], "accepted")
        before = self.gp.read_bytes()
        for nid, set_ in (("result", {"label": "Đổi ô khoá"}), ("idea", {"label": "Nhanh hơn 99 lần"}),
                          ("idea", {"anchors": []})):
            code, _, body = self.edit(set_, nid)
            self.assertEqual(code, 422, body)
        self.assertEqual(self.gp.read_bytes(), before)
        self.assertEqual(self.edit({"status": "accepted"}, "result")[0], 200)  # mở khoá rồi mới sửa được
        self.assertEqual(self.edit({"label": "Nhanh hơn bốn lần"}, "result")[0], 200)

    def test_stale_version_is_a_conflict(self):  # TM-19
        newer = json.loads(self.gp.read_text("utf-8"))
        node(newer, "problem")["label"] = "Bản dựng lại mới hơn"
        self.gp.write_text(json.dumps(newer, ensure_ascii=False), encoding="utf-8")
        code, _, _ = self.req("POST", "/api/edit", {"version": "0" * 64, "node": "idea", "set": {"label": "x y"}})
        self.assertEqual(code, 409)
        self.assertEqual(node(json.loads(self.gp.read_text("utf-8")), "problem")["label"], "Bản dựng lại mới hơn")

    def test_move_and_reset(self):  # TM-20
        code, _, body = self.req("POST", "/api/move", {"version": self.version(), "tier": "", "pos": {"idea": [480, 8]}})
        self.assertEqual(code, 200, body)
        t = json.loads(body)["tiers"][""]
        self.assertEqual(t["pinned"], ["idea"])
        self.assertEqual(t["nodes"]["idea"]["x"] - t["shift"][0], 480)
        saved = json.loads((self.d / "toy.layout.json").read_text("utf-8"))
        self.assertEqual(saved["tiers"], {"": {"idea": [480.0, 8.0]}})
        code, _, _ = self.req("POST", "/api/move", b'{"version": "%s", "tier": "", "pos": {"idea": [NaN, 1]}}'
                              % self.version().encode())
        self.assertEqual(code, 422)
        code, _, body = self.req("POST", "/api/move", {"version": self.version(), "tier": "", "reset": True})
        self.assertEqual(json.loads(body)["tiers"][""]["pinned"], [])
        self.assertEqual(json.loads((self.d / "toy.layout.json").read_text("utf-8"))["tiers"], {})


if __name__ == "__main__":
    unittest.main()


class ServerMore(Server):
    def test_edit_changes_only_its_line(self):  # review: lưu một lần không định dạng lại cả file
        before = self.gp.read_text("utf-8").splitlines()
        self.assertEqual(self.edit({"label": "Xử lý mọi từ cùng lúc"})[0], 200)
        after = self.gp.read_text("utf-8").splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)

    def test_move_conflict_and_broken_layout_file(self):  # TM-19 cho move; review: file layout hỏng không bị xoá lặng lẽ
        code, _, _ = self.req("POST", "/api/move", {"version": "0" * 64, "tier": "", "pos": {"idea": [8, 8]}})
        self.assertEqual(code, 409)
        lp = self.d / "toy.layout.json"
        lp.write_text('{"version": 1, "sha256": "x", "tiers": {"": {"idea": [8, 8],}}}', encoding="utf-8")
        code, _, body = self.req("POST", "/api/move", {"version": self.version(), "tier": "", "pos": {"problem": [8, 8]}})
        self.assertEqual(code, 422, body)
        self.assertIn(b"layout.json", body)
        self.assertIn('"idea": [8, 8],}', lp.read_text("utf-8"))
        lp.write_text(" " * (edits.LAYOUT_MAX_BYTES + 1), encoding="utf-8")  # quá trần: bỏ khi xem, kèm cảnh báo
        self.assertIn("bỏ qua", edits.read_pins(lp, parsed(graph()))[1])

    def test_odd_bodies_get_json_errors_not_dropped_connections(self):  # review: ngoại lệ lọt ra, cắt kết nối
        for set_ in ({"status": []}, {"status": {}}, {"label": None}):
            code, _, body = self.edit(set_)
            self.assertEqual(code, 422, set_)
            self.assertTrue(json.loads(body)["error"])

    def test_idle_connection_does_not_block_others(self):  # review: kết nối rảnh chặn server một luồng
        import socket  # noqa: PLC0415
        import time  # noqa: PLC0415

        idle = socket.create_connection(("127.0.0.1", self.port))
        try:
            t0 = time.monotonic()
            self.assertEqual(self.req("GET", "/")[0], 200)
            self.assertLess(time.monotonic() - t0, 5)
        finally:
            idle.close()


class Fmt(unittest.TestCase):
    def test_fmt_round_trips_and_is_idempotent(self):
        import contextlib  # noqa: PLC0415
        import io  # noqa: PLC0415

        from paper_graph import cli  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "toy.graph.json"
            p.write_text(json.dumps(graph(), ensure_ascii=False, indent=2), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["fmt", str(p)]), 0)
            text = p.read_text("utf-8")
            self.assertEqual(json.loads(text), graph())
            # {, version, paper, "nodes": [, 5 ô, ], "edges": [, 3 cạnh, ], "groups": [], }
            self.assertEqual(len(text.splitlines()), 17)
            self.assertEqual(format_graph(json.loads(text)), text)
