"""Bộ câu hỏi đo hiểu bài (Mốc 5, việc 6.2): `<tên>.quiz.json`, bộ kiểm, và trang làm bài HTML tự chứa.

Dùng để so hai cách đọc cùng một bài (đọc chữ, đọc qua sơ đồ): người đọc làm bài sau khi đọc, trang tự chấm, đo thời
gian và cho một dòng kết quả để chép lại. Quy trình đo ở `docs/do-hieu-bai.md`.

Mỗi câu neo về câu trích nguyên văn (kiểm như neo của sơ đồ), để đáp án đúng có chỗ dựa trong bài, không do người
soạn nhớ nhầm. Trang làm bài nhúng dữ liệu và dựng chữ như trình xem (TM-13, TM-14): JSON đã thoát ký tự, chỉ
`textContent`, CSP theo hash. Đáp án nằm trong trang: đây là bài tự kiểm, không phải bài thi.
"""
import collections
import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import blocks as blocks_mod
from . import model as m
from .check import AnchorChecker, Diag, _anchors, _Diags, _id, _text, _unknown
from .files import InputError, read_json, sibling
from .view import ASSETS, _json_for_html, _sha

KINDS = {"big": "bức tranh lớn", "mechanism": "cơ chế", "evidence": "bằng chứng", "limit": "giới hạn",
         "detail": "chi tiết"}
FIELDS = {"id", "kind", "q", "choices", "answer", "explain", "anchors"}
MIN_Q, MAX_Q = 3, 12


@dataclass
class Question:
    id: str
    kind: str
    q: str
    choices: list[str]
    answer: int
    explain: str
    anchors: list[m.Anchor] = field(default_factory=list)


@dataclass
class Quiz:
    title: str
    sha256: str
    blocks_file: str
    questions: list[Question]


def parse(doc) -> tuple[Quiz | None, list[Diag]]:
    d = _Diags()
    if not isinstance(doc, dict) or doc.get("version") != 1:
        d.err("PG101", "bộ câu hỏi", "gốc phải là object có `version: 1`")
        return None, d
    paper = doc.get("paper") if isinstance(doc.get("paper"), dict) else {}
    title = _text(d, "paper", "title", paper.get("title"), 300, True)
    sha = paper.get("sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        d.err("PG101", "paper", "`sha256` phải là SHA-256 của PDF (64 ký tự hex thường)")
        sha = ""
    bfile = paper.get("blocks") if isinstance(paper.get("blocks"), str) else ""
    raw = doc.get("questions") if isinstance(doc.get("questions"), list) else []
    if not MIN_Q <= len(raw) <= MAX_Q:
        d.err("PG101", "bộ câu hỏi", f"cần {MIN_Q}–{MAX_Q} câu, có {len(raw)}")
    qs: list[Question] = []
    seen: set[str] = set()
    for i, r in enumerate(raw[:MAX_Q]):
        where = f"questions[{i}]"
        if not isinstance(r, dict):
            d.err("PG101", where, "câu hỏi phải là object")
            continue
        qid = _id(d, where, r.get("id"))
        if qid is None:
            continue
        where = f"câu {qid}"
        if qid in seen:
            d.err("PG104", where, "id trùng")
            continue
        seen.add(qid)
        _unknown(d, where, r, FIELDS)
        kind = r.get("kind")
        if not isinstance(kind, str) or kind not in KINDS:  # list hay object làm `in` văng TypeError
            d.err("PG102", where, "`kind` phải là " + ", ".join(KINDS))
        choices = r.get("choices")
        if (not isinstance(choices, list) or not 3 <= len(choices) <= 5
                or not all(isinstance(c, str) and c.strip() for c in choices)):
            d.err("PG101", where, "`choices` phải là 3–5 phương án chữ, không rỗng")
            choices = []
        choices = [_text(d, where, "choices", c, 200, True) for c in choices]
        if len(set(choices)) != len(choices):
            d.err("PG101", where, "hai phương án trùng nhau")
        answer = r.get("answer")
        if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer < max(len(choices), 1):
            d.err("PG101", where, "`answer` phải là số thứ tự (từ 0) của phương án đúng")
            answer = 0
        anchors = _anchors(d, where, r.get("anchors"))
        if not anchors:
            d.err("PG201", where, "mỗi câu cần ít nhất một câu trích chứng minh đáp án")
        qs.append(Question(qid, kind if isinstance(kind, str) and kind in KINDS else "detail", _text(d, where, "q", r.get("q"), 300, True),
                           choices, answer, _text(d, where, "explain", r.get("explain"), 600, False), anchors))
    return Quiz(title, sha, bfile, qs), d


def check(quiz: Quiz, bl: blocks_mod.Blocks | None, diags: list[Diag]) -> list[Diag]:
    d = _Diags(diags)
    if bl is not None and quiz.sha256 and quiz.sha256 != bl.sha256:
        d.err("PG206", "paper", "sha256 của bộ câu hỏi khác blocks.json: câu hỏi của một bài khác")
        bl = None
    checker = AnchorChecker(d, bl, collections.defaultdict(int))
    for q in quiz.questions:
        checker.check(f"câu {q.id}", q.anchors)
    # đáp án đúng hay là phương án dài nhất thì người chưa đọc cũng đoán trúng: phép đo mất sức phân biệt
    longest = [q.id for q in quiz.questions if q.choices and len(q.choices[q.answer]) == max(len(c) for c in q.choices)]
    if quiz.questions and len(longest) * 2 > len(quiz.questions):
        d.warn("PG231", "bộ câu hỏi", f"đáp án đúng là phương án dài nhất ở {len(longest)}/{len(quiz.questions)} câu "
               f"({', '.join(longest)}): đoán theo độ dài cũng trúng",
               "viết phương án nhiễu dài và cụ thể ngang đáp án đúng")
    return d


def load(path: Path, blocks_path: Path | None = None) -> tuple[Quiz, list[Diag]]:
    quiz, diags = parse(read_json(path, "bộ câu hỏi"))
    if quiz is None:
        raise InputError(f"{path}: " + "; ".join(x.msg for x in diags))
    if blocks_path is None:
        blocks_path = sibling(path, quiz.blocks_file or "", ".blocks.json")
    bl, errs = blocks_mod.parse(read_json(blocks_path, "blocks"))
    if errs:
        raise InputError(f"{blocks_path} hỏng:\n" + "\n".join(errs[:20]))
    return quiz, check(quiz, bl, diags)


def page(quiz: Quiz) -> str:
    """Trang làm bài tự chứa. Bộ câu hỏi phải qua bộ kiểm trước (người gọi lo)."""
    data = {"title": quiz.title, "sha256": quiz.sha256, "kinds": KINDS,
            "questions": [{"id": q.id, "kind": q.kind, "q": q.q, "choices": q.choices, "answer": q.answer,
                           "explain": q.explain, "anchors": [{"page": a.page, "quote": a.quote} for a in q.anchors]}
                          for q in quiz.questions]}
    style = (ASSETS / "quiz.css").read_text("utf-8")
    script = (ASSETS / "quiz.js").read_text("utf-8")
    csp = (f"default-src 'none'; script-src {_sha(script)}; style-src {_sha(style)}; base-uri 'none'; "
           "form-action 'none'")
    template = (ASSETS / "quiz.html").read_text("utf-8")
    values = {"CSP": csp, "TITLE": html.escape(quiz.title or "Câu hỏi", quote=True), "STYLE": style,
              "DATA": _json_for_html(data), "SCRIPT": script}
    return re.sub(r"\{\{([A-Z]+)\}\}", lambda mt: values[mt.group(1)], template)
