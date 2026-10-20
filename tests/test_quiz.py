"""Bộ câu hỏi hiểu bài (quiz.py): bộ kiểm và trang làm bài."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from paper_graph import quiz
from paper_graph.files import InputError

from .helpers import SHA, blocks

ROOT = Path(__file__).resolve().parents[1]


def q(i, **kw):
    base = {"id": f"q{i}", "kind": "big", "q": "Bài giải quyết vấn đề gì?", "choices": ["a", "b", "c", "d"],
            "answer": 1, "explain": "", "anchors": [{"page": 1, "quote": "processes all tokens at once"}]}
    base.update(kw)
    return base


def doc(questions):
    return {"version": 1, "paper": {"title": "Toy", "sha256": SHA, "blocks": "toy.blocks.json"}, "questions": questions}


class Quiz(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "toy.blocks.json").write_text(json.dumps(blocks()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, data):
        p = self.d / "toy.quiz.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return quiz.load(p)

    def codes(self, data):
        _, diags = self.load(data)
        return {d.code for d in diags if d.level == "error"}

    def test_good_quiz_has_no_errors(self):
        self.assertEqual(self.codes(doc([q(1), q(2), q(3)])), set())

    def test_refusals(self):
        cases = [
            (doc([q(1), q(2)]), "PG101"),  # quá ít câu
            (doc([q(1), q(2), q(3, answer=4)]), "PG101"),  # đáp án ngoài phương án
            (doc([q(1), q(2), q(3, answer=True)]), "PG101"),
            (doc([q(1), q(2), q(3, choices=["a", "a", "b"])]), "PG101"),
            (doc([q(1), q(2), q(3, kind="lạ")]), "PG102"),
            (doc([q(1), q(1), q(3)]), "PG104"),
            (doc([q(1), q(2), q(3, anchors=[])]), "PG201"),
            (doc([q(1), q(2), q(3, anchors=[{"page": 1, "quote": "this sentence is not in the toy paper"}])]),
             "PG201"),
        ]
        for data, code in cases:
            with self.subTest(code=code):
                self.assertIn(code, self.codes(data))

    def test_odd_kind_types_are_errors_not_crashes(self):  # review: `kind` là list làm `in` văng TypeError
        for kind in (["big"], {"a": 1}, 5, None):
            with self.subTest(kind=kind):
                self.assertIn("PG102", self.codes(doc([q(1), q(2), q(3, kind=kind)])))

    def test_longest_answer_pattern_is_flagged(self):  # review: đáp án luôn dài nhất thì đoán theo độ dài cũng trúng
        long = ["ngắn", "đáp án đúng dài hơn hẳn các phương án còn lại", "vừa", "ngắn nữa"]
        _, diags = self.load(doc([q(i, choices=long, answer=1) for i in range(1, 4)]))
        self.assertIn("PG231", {d.code for d in diags if d.level == "warning"})

    def test_quiz_of_another_paper(self):
        data = doc([q(1), q(2), q(3)])
        data["paper"]["sha256"] = "b" * 64
        self.assertIn("PG206", self.codes(data))
        with self.assertRaises(InputError):
            self.load({"version": 2})

    def test_page_escapes_hostile_text(self):  # TM-13, TM-14 như trình xem
        evil = '</script><script>alert(1)</script> '
        qz, diags = self.load(doc([q(1, q="Câu " + evil), q(2, explain=evil), q(3, choices=["a", evil, "c"])]))
        self.assertFalse([d for d in diags if d.level == "error"])
        page = quiz.page(qz)
        self.assertEqual(len(re.findall(r"<script", page)), 2)
        self.assertNotIn(" ", page)
        csp = re.search(r'Content-Security-Policy" content="([^"]+)"', page).group(1)
        self.assertNotIn("unsafe", csp)
        self.assertIn("default-src 'none'", csp)

    def test_quiz_script_never_writes_markup(self):
        js = (ROOT / "paper_graph/viewer/quiz.js").read_text("utf-8")
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(bad, js)

    def test_bench_quizzes_pass(self):
        for name in ("attention", "rag", "prism", "ignored"):
            with self.subTest(name=name):
                _, diags = quiz.load(ROOT / "bench/papers" / name / f"{name}.quiz.json")
                self.assertFalse(diags, diags)  # không lỗi, cả không PG231


if __name__ == "__main__":
    unittest.main()
