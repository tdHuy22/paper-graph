"""Dựng sơ đồ qua API (build.py), với hàm gọi OpenRouter giả: TM-21..TM-25 ở `.agent/threat-model.md`."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from paper_graph import build
from paper_graph.files import format_graph

from .helpers import blocks, graph, node

KEY = "sk-or-v1-" + "0123456789abcdef" * 4


def reply(content, cost=0.001):
    return {"choices": [{"message": {"content": content}}], "usage": {"cost": cost}}


class Fake:
    """Trả lần lượt các câu trả lời đã định, ghi lại thân request."""

    def __init__(self, *answers, cost=0.001):
        self.answers = list(answers)
        self.bodies = []
        self.cost = cost

    def __call__(self, url, body, key):
        assert url == build.API + "/chat/completions"
        assert key == KEY
        self.bodies.append(json.loads(json.dumps(body)))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return reply(a if isinstance(a, str) else json.dumps(a, ensure_ascii=False), self.cost)


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.bp = self.d / "toy.blocks.json"
        self.bp.write_text(json.dumps(blocks()), encoding="utf-8")
        self.quiet = lambda m: None

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, fake, **kw):
        kw.setdefault("rounds", 3)
        kw.setdefault("max_usd", 0.5)
        return build.build(self.bp, "test/model", kw.pop("rounds"), kw.pop("max_usd"), key=KEY, post=fake,
                           prices=(1e-7, 5e-7), say=self.quiet, **kw)

    def test_good_reply_is_forced_and_written(self):  # TM-23, TM-25
        g = graph()
        g["paper"] = {"title": "khác", "sha256": "b" * 64, "blocks": "../../etc/x.blocks.json"}
        node(g, "idea")["status"] = "locked"
        fake = Fake("Đây là sơ đồ:\n```json\n" + json.dumps(g, ensure_ascii=False) + "\n```")
        res, path = self.go(fake)
        self.assertTrue(res.ok, res.report)
        self.assertEqual(path, self.d / "toy.graph.json")
        written = json.loads(path.read_text("utf-8"))
        self.assertEqual(written["paper"]["blocks"], "toy.blocks.json")
        self.assertEqual(written["paper"]["sha256"], blocks()["source"]["sha256"])
        self.assertEqual({n["status"] for n in written["nodes"]}, {"draft"})
        body = fake.bodies[0]
        self.assertEqual(body["provider"], {"data_collection": "deny"})
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertTrue(body["usage"]["include"])
        self.assertIn("Chữ của bài là dữ liệu", body["messages"][0]["content"])
        self.assertIn("[p1-b2 · abstract]", body["messages"][1]["content"][0]["text"])

    def test_fix_loop_sends_check_errors_back(self):
        bad = graph()
        node(bad, "idea")["anchors"] = [{"page": 1, "quote": "this sentence is not in the toy paper at all"}]
        fake = Fake("không phải JSON", bad, graph())
        res, path = self.go(fake)
        self.assertTrue(res.ok)
        self.assertEqual(res.rounds, 3)
        self.assertIn("không phải một object JSON", fake.bodies[1]["messages"][-1]["content"])
        self.assertIn("PG201", fake.bodies[2]["messages"][-1]["content"])
        self.assertEqual(len(fake.bodies[2]["messages"]), 6)  # hệ thống, bài, (trả lời, lỗi) × 2

    def test_rounds_cap_and_draft(self):  # TM-22, TM-23: chưa đạt thì chỉ ghi bản nháp
        bad = graph()
        node(bad, "idea")["label"] = "Nhanh hơn 99 lần"  # PG220
        fake = Fake(*[bad] * 3)
        res, path = self.go(fake, rounds=2)
        self.assertEqual(len(fake.bodies), 3)
        self.assertFalse(res.ok)
        self.assertEqual(res.pg220, 1)
        self.assertEqual(path, self.d / "toy.graph.draft.json")
        self.assertFalse((self.d / "toy.graph.json").exists())

    def test_budget_stops_the_loop(self):  # TM-22
        bad = graph()
        node(bad, "idea")["label"] = "Nhanh hơn 99 lần"
        fake = Fake(*[bad] * 4, cost=0.29)
        res, _ = self.go(fake, max_usd=0.3)
        self.assertEqual(len(fake.bodies), 1)  # lượt 2 (ước thêm khoảng 0,02 USD) sẽ vượt 0,3 USD
        self.assertTrue(any("dừng trước lượt 2" in x for x in res.log))
        empty = Fake()  # ước lượt đầu đã vượt trần: không gọi lần nào (gọi thì Fake rỗng văng IndexError)
        res2 = build.run(self.bp, "m", 3, 0.000001, key=KEY, post=empty, prices=(1e-3, 1e-3), say=self.quiet)
        self.assertEqual((res2.rounds, empty.bodies), (0, []))

    def test_existing_graph_needs_force_and_keeps_locked(self):  # TM-24
        old = graph()
        node(old, "result")["status"] = "locked"
        node(old, "idea")["status"] = "accepted"
        out = self.d / "toy.graph.json"
        out.write_text(format_graph(old), encoding="utf-8")
        fake = Fake()
        with self.assertRaises(build.BuildError):
            self.go(fake)
        self.assertEqual(fake.bodies, [])  # từ chối trước khi tốn tiền
        changed = graph()  # model đổi nhãn ô khoá và trả lại ô accepted y nguyên
        node(changed, "result")["label"] = "Nhanh hơn rõ rệt"
        fake = Fake(changed)
        res, path = self.go(fake, force=True)
        self.assertTrue(res.ok, res.report)  # review: trước đây không bao giờ đạt vì ô khoá bị ép về draft
        written = {n["id"]: n for n in json.loads(path.read_text("utf-8"))["nodes"]}
        self.assertEqual(written["result"], node(old, "result"))  # ô khoá lấy nguyên từ bản cũ
        self.assertEqual(written["idea"]["status"], "accepted")  # accepted không đổi nội dung thì giữ
        self.assertEqual(json.loads((self.d / "toy.graph.old.json").read_text("utf-8")), old)
        self.assertIn('"id": "result"', fake.bodies[0]["messages"][3]["content"])  # model được báo ô khoá

    def test_graph_changed_during_build_is_not_overwritten(self):  # review: race ở TM-24
        out = self.d / "toy.graph.json"

        def sneaky(url, body, key):
            out.write_text("{}", encoding="utf-8")  # người dùng ghi graph.json trong lúc chờ model
            return reply(json.dumps(graph(), ensure_ascii=False))
        res, path = build.build(self.bp, "m", 0, 0.5, key=KEY, post=sneaky, prices=(1e-7, 5e-7), say=self.quiet)
        self.assertTrue(res.ok)
        self.assertEqual(path, self.d / "toy.graph.draft.json")
        self.assertEqual(out.read_text("utf-8"), "{}")

    def test_api_error_after_first_round_keeps_paid_work(self):  # review: lỗi giữa vòng làm mất bản đã trả tiền
        bad = graph()
        node(bad, "idea")["label"] = "Nhanh hơn 99 lần"
        res, path = self.go(Fake(bad, build.BuildError("OpenRouter trả 400: context too long")))
        self.assertEqual(path, self.d / "toy.graph.draft.json")
        self.assertTrue(path.exists())
        self.assertIn("PG220", (self.d / "toy.graph.draft.txt").read_text("utf-8"))
        self.assertTrue(any("dừng, giữ bản tốt nhất" in x for x in res.log))

    def test_fix_rounds_start_from_the_best_answer(self):  # bản sau tệ hơn thì lượt sau vẫn sửa từ bản tốt nhất
        good_ish = graph()
        node(good_ish, "idea")["label"] = "Nhanh hơn 99 lần"  # 1 PG220
        worse = graph()
        node(worse, "idea")["anchors"] = [{"page": 1, "quote": "this sentence is not in the toy paper at all"}]
        node(worse, "problem")["label"] = "Chậm 77 lần"
        fake = Fake(good_ish, worse, graph())
        res, _ = self.go(fake)
        self.assertTrue(res.ok)
        third = fake.bodies[2]["messages"]
        self.assertEqual(len(third), 4)  # hệ thống, bài, bản tốt nhất, lỗi của nó: không cả lịch sử
        self.assertIn("99", third[2]["content"])

    def test_truncated_reply_asks_for_shorter_text(self):
        def cut(url, body, key):
            cut.n += 1
            if cut.n == 1:
                return {"choices": [{"message": {"content": '{"nodes": [{"id": "x"'}, "finish_reason": "length"}],
                        "usage": {"cost": 0.001}}
            assert "bị cắt vì quá dài" in body["messages"][-1]["content"]
            return reply(json.dumps(graph(), ensure_ascii=False))
        cut.n = 0
        res, _ = self.go(cut)
        self.assertTrue(res.ok)

    def test_reasoning_has_its_own_budget(self):  # TM-22: suy luận ăn hết max_tokens làm JSON bị cắt (Opus 5.5)
        fake = Fake(graph())
        self.go(fake)
        body = fake.bodies[0]
        self.assertEqual(body["reasoning"], {"max_tokens": build.REASONING_TOKENS})
        self.assertEqual(body["max_tokens"], build.MAX_OUT_TOKENS + build.REASONING_TOKENS)

    def test_estimate_follows_measured_tokens(self):  # TM-22: ước theo ký tự/3 thấp hơn tiền thật với chữ tiếng Việt
        said = []
        bad = graph()
        node(bad, "idea")["label"] = "Nhanh hơn 99 lần"

        def tokens(url, body, key):
            tokens.sent.append(sum(len(m["content"]) if isinstance(m["content"], str) else len(m["content"][0]["text"])
                                   for m in body["messages"]))
            r = reply(json.dumps(bad, ensure_ascii=False))
            r["usage"]["prompt_tokens"] = tokens.sent[-1]  # 1 ký tự mỗi token: nặng hơn mức ước ban đầu
            return r
        tokens.sent = []
        p_in, p_out = 1e-6, 1e-6
        build.run(self.bp, "m", 1, 5, key=KEY, post=tokens, prices=(p_in, p_out), say=said.append)
        est = [float(x.split("ước tối đa ")[1].split(" USD")[0]) for x in said if "ước tối đa" in x]
        out = (build.MAX_OUT_TOKENS + build.REASONING_TOKENS) * p_out
        self.assertAlmostEqual(est[0], tokens.sent[0] / build.CHARS_PER_TOKEN * p_in + out, delta=0.001)
        self.assertAlmostEqual(est[1], tokens.sent[1] / 0.9 * p_in + out, delta=0.001)  # tỉ lệ thật, trừ hao 10%

    def test_unreadable_paid_reply_is_kept(self):  # đã trả tiền mà không ra JSON: ghi lại, không bỏ
        res, path = self.go(Fake('{"nodes": [{"id": "x"', '{"nodes": ['), rounds=1)
        self.assertIsNone(res.graph)
        self.assertFalse((self.d / "toy.graph.json").exists())
        self.assertFalse((self.d / "toy.graph.draft.json").exists())
        txt = (self.d / "toy.graph.raw.txt").read_text(encoding="utf-8")
        self.assertIn('{"nodes": [', txt)
        self.assertIn("không đọc được JSON", txt)

    def test_api_error_after_an_unreadable_reply_keeps_it(self):  # review: lượt 2 lỗi API làm mất câu trả lời lượt 1
        res, _ = self.go(Fake('{"nodes": [{"id": "x"', build.BuildError("OpenRouter trả 400: hỏng")), rounds=2)
        self.assertEqual(res.rounds, 1)
        self.assertGreater(res.cost, 0)
        self.assertIn('{"nodes": [{"id": "x"', (self.d / "toy.graph.raw.txt").read_text(encoding="utf-8"))
        with self.assertRaises(build.BuildError):  # lượt đầu lỗi thì chưa trả tiền gì: vẫn báo lỗi
            self.go(Fake(build.BuildError("OpenRouter trả 400: hỏng")))

    def test_measured_ratio_is_capped(self):  # TM-22: token báo thấp bất thường không được làm ước thấp đi
        said = []
        bad = graph()
        node(bad, "idea")["label"] = "Nhanh hơn 99 lần"

        def few(url, body, key):
            few.sent.append(sum(len(m["content"]) if isinstance(m["content"], str) else len(m["content"][0]["text"])
                                for m in body["messages"]))
            r = reply(json.dumps(bad, ensure_ascii=False))
            r["usage"]["prompt_tokens"] = 1
            return r
        few.sent = []
        info = build.ModelInfo(1e-4, 1e-7, None, False)  # giá vào lớn để chênh của phần thêm lộ ra
        build.run(self.bp, "m", 1, 5, key=KEY, post=few, prices=info, say=said.append)
        est = [float(x.split("ước tối đa ")[1].split(" USD")[0]) for x in said if "ước tối đa" in x]
        head = few.sent[0]
        want = (head / 3.6 + (few.sent[1] - head) / build.CHARS_PER_TOKEN) * 1e-4 + build.MAX_OUT_TOKENS * 1e-7
        self.assertAlmostEqual(est[1], want, delta=0.001)

    def test_missing_cost_counts_the_upper_estimate(self):  # TM-22: không có usage.cost thì tính mức ước trên
        def nocost(url, body, key):
            return {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {}}
        info = build.ModelInfo(1e-6, 1e-6, None, True)
        res = build.run(self.bp, "m", 0, 5, key=KEY, post=nocost, prices=info, say=self.quiet)
        self.assertGreaterEqual(res.cost, (build.MAX_OUT_TOKENS + build.REASONING_TOKENS) * 1e-6)

    def test_model_limits_shape_the_request(self):  # review: max_tokens vượt mức model cho, model không suy luận
        rows = [{"id": "big", "pricing": {"prompt": "0.000004", "completion": "0.00002", "input_cache_write": "0.000005"},
                 "top_provider": {"max_completion_tokens": 128000}, "supported_parameters": ["reasoning"]},
                {"id": "small", "pricing": {"prompt": "0.0000001", "completion": "0.0000004"},
                 "top_provider": {"max_completion_tokens": 32768}, "supported_parameters": ["max_tokens"]}]
        big = build.model_info("big", lambda url: {"data": rows})
        self.assertEqual((big.p_in, big.max_out, big.reasoning), (0.000005, 128000, True))  # giá ghi cache cao hơn
        small = build.model_info("small", lambda url: {"data": rows})
        fake = Fake(graph())
        build.run(self.bp, "small", 0, 1, key=KEY, post=fake, prices=small, say=self.quiet)
        self.assertNotIn("reasoning", fake.bodies[0])
        self.assertEqual(fake.bodies[0]["max_tokens"], build.MAX_OUT_TOKENS)
        tiny = build.ModelInfo(1e-7, 4e-7, 20000, True)
        fake = Fake(graph())
        build.run(self.bp, "tiny", 0, 1, key=KEY, post=fake, prices=tiny, say=self.quiet)
        self.assertEqual(fake.bodies[0]["max_tokens"], 20000)

    def test_prices_without_a_fixed_rate_are_refused(self):  # review: giá -1 làm trần tiền vô hiệu
        def models(rows):
            return lambda url: {"data": rows}
        for row in ({"id": "m", "pricing": {"prompt": "-1", "completion": "-1"}},
                    {"id": "m", "pricing": {"prompt": "0", "completion": "0"}},
                    {"id": "m", "pricing": {"prompt": "nan", "completion": "1"}}):
            with self.subTest(row=row), self.assertRaises(build.BuildError):
                build.price("m", models([row]))
        self.assertEqual(build.price("m:free", models([{"id": "m:free", "pricing": {"prompt": "0", "completion": "0"}}])),
                         (0.0, 0.0))

    def test_timeouts_count_toward_the_budget(self):  # review: thử lại sau timeout có thể đã bị tính tiền
        t = build.BuildError("hết giờ chờ OpenRouter: timed out")
        with mock.patch.object(build.time, "sleep"):
            fake = Fake(t, t, t)
            with self.assertRaises(build.BuildError):
                build.run(self.bp, "m", 0, 0.03, key=KEY, post=fake, prices=(1e-7, 5e-7), say=self.quiet)
            self.assertEqual(len(fake.bodies), 1)  # ước mỗi lượt khoảng 0,018 USD: lần thử lại sẽ vượt 0,03

    def test_allow_training_only_for_free_models(self):  # TM-25
        with self.assertRaises(build.BuildError):
            build.run(self.bp, "deepseek/x", 0, 0.5, key=KEY, post=Fake(), prices=(1e-7, 5e-7), say=self.quiet,
                      allow_training=True)
        fake = Fake(graph())
        build.run(self.bp, "vendor/m:free", 0, 0.5, key=KEY, post=fake, prices=(0.0, 0.0), say=self.quiet,
                  allow_training=True)
        self.assertEqual(fake.bodies[0]["provider"], {"data_collection": "allow"})

    def test_error_inside_a_200_reply_is_an_api_error(self):  # nhà cung cấp hết giờ, OpenRouter vẫn trả 200
        def gateway(url, body, key):
            gateway.n += 1
            if gateway.n < 3:
                return {"id": "x", "error": {"message": "Gateway timeout", "code": 504}}
            return reply(json.dumps(graph(), ensure_ascii=False))
        gateway.n = 0
        with mock.patch.object(build.time, "sleep"):
            res, _ = self.go(gateway)
        self.assertTrue(res.ok)
        self.assertEqual(gateway.n, 3)

    def test_redirects_are_not_followed(self):  # review: redirect mang Authorization sang host khác
        h = build._NoRedirect()
        self.assertIsNone(h.redirect_request(None, None, 302, "Found", {}, "http://evil.example/"))
        self.assertTrue(any(isinstance(x, build._NoRedirect) for x in build._OPENER.handlers))

    def test_errors_never_show_the_key(self):  # TM-21
        boom = build.BuildError(f"OpenRouter trả 401: invalid key {KEY}")
        with self.assertRaises(build.BuildError) as cm:
            self.go(Fake(boom))
        self.assertNotIn(KEY, str(cm.exception))
        self.assertIn("[khoá]", str(cm.exception))
        self.assertEqual(build.redact("x sk-or-v1-abcdefabcdef y", ""), "x [khoá] y")

    def test_transient_errors_retry_a_bounded_number_of_times(self):  # TM-22
        self.assertTrue(build._retryable(build.BuildError("phản hồi của OpenRouter không phải JSON")))
        err = build.BuildError("OpenRouter trả 503: busy")
        with mock.patch.object(build.time, "sleep"):
            res, _ = self.go(Fake(err, err, graph()))
            self.assertTrue(res.ok)
            with self.assertRaises(build.BuildError):
                self.go(Fake(err, err, err), force=True)

    def test_key_sources(self):  # TM-21
        kf = self.d / "openrouter.key"
        with mock.patch.object(build, "KEY_FILE", kf), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(build.KEY_ENV, None)
            with self.assertRaises(build.BuildError):
                build.load_key()  # chưa có
            kf.write_text(KEY)
            kf.chmod(0o644)
            with self.assertRaises(build.BuildError) as cm:
                build.load_key()  # người khác đọc được
            self.assertNotIn(KEY, str(cm.exception))
            kf.chmod(0o600)
            self.assertEqual(build.load_key(), KEY)
            kf.write_text("# khoá của tôi\n" + KEY)  # review: dòng ghi chú làm khoá lọt vào traceback của header
            with self.assertRaises(build.BuildError) as cm:
                build.load_key()
            self.assertNotIn(KEY, str(cm.exception))
            os.environ[build.KEY_ENV] = "sk-or-from-env-1234567890"
            self.assertEqual(build.load_key(), "sk-or-from-env-1234567890")
            os.environ.pop(build.KEY_ENV)

    def test_http_post_refuses_other_hosts(self):  # TM-21
        with self.assertRaises(build.BuildError):
            build.http_post("https://evil.example/api/v1/chat/completions", {}, KEY)

    def test_instructions_follow_the_skill(self):
        text = build.instructions()
        self.assertIn("### 3. Lập bản đồ", text)
        self.assertIn("### 4. Viết", text)
        self.assertIn("Chỗ lệch:", text)  # mẫu khó viết
        self.assertNotIn("### 1. Lấy chữ", text)  # bước gọi lệnh bị bỏ
        self.assertNotIn("### 6. Báo cáo", text)

    def test_huge_paper_is_refused_before_calling(self):  # TM-22
        b = blocks()
        b["blocks"][1]["text"] = "word " * (build.MAX_PAPER_CHARS // 4)
        self.bp.write_text(json.dumps(b), encoding="utf-8")
        fake = Fake()
        with self.assertRaises(build.BuildError):
            self.go(fake)
        self.assertEqual(fake.bodies, [])


if __name__ == "__main__":
    unittest.main()
