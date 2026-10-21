"""Script chấm phép đo người đọc thật (bench/hieu_bai.py)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import hieu_bai  # noqa: E402


class HieuBai(unittest.TestCase):
    def setUp(self):
        self.known = hieu_bai.quizzes()
        self.att = next(k for k, v in self.known.items() if v["name"] == "attention")
        self.rag = next(k for k, v in self.known.items() if v["name"] == "rag")

    def line(self, who, group, sha, how, right_first, extra=None):
        qs = self.known[sha]["questions"]
        ans = [q["answer"] if i < right_first else len(q["choices"]) for i, q in enumerate(qs)]
        return json.dumps({"nguoi": who, "nhom": group, "bai": sha, "cach_doc": how, "dung": 99, "tong": len(qs),
                           "giay": 600, "tra_loi": ans, **(extra or {})})

    def run_file(self, lines):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "kq.jsonl"
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return hieu_bai.load(p, self.known)

    def test_rescores_and_compares_each_person(self):
        rows, errs = self.run_file([
            self.line("P1", "A", self.att, "chu", 6), self.line("P1", "A", self.rag, "so-do", 9),
            self.line("P2", "B", self.att, "so-do", 5), self.line("P2", "B", self.rag, "chu", 7)])
        self.assertEqual(errs, [])
        out = hieu_bai.report(rows)
        self.assertIn("chữ 6/12", out)  # chấm lại từ tra_loi, không tin trường `dung` = 99
        self.assertIn("hiệu +3", out)
        self.assertIn("hiệu -2", out)
        self.assertIn("gộp: 2 người, trung vị hiệu (sơ đồ − chữ) +0.5; hơn 1, kém 1, bằng 0", out)
        self.assertIn("6 không biết", out)
        self.assertIn("Dưới 20 người", out)

    def test_bad_lines_are_reported_not_scored(self):
        rows, errs = self.run_file(["không phải json", json.dumps({"bai": "000000000000"}),
                                    self.line("P3", "C", self.att, "chu", 3),
                                    self.line("P4", "A", self.att, "chu", 3, {"tra_loi": [1]})])
        self.assertEqual(rows, [])
        self.assertEqual(len(errs), 4)

    def test_retest_is_reported_separately(self):
        rows, _ = self.run_file([self.line("P1", "A", self.att, "chu", 6),
                                 self.line("P1", "A", self.att, "chu", 4, {"lan": 2})])
        self.assertIn("Lần 2: 1 người", hieu_bai.report(rows, 2))


if __name__ == "__main__":
    unittest.main()
