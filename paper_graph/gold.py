"""Đáp án tay của bộ đo (`bench/papers/<tên>/<tên>.gold.json`): các ý một sơ đồ tốt của bài phải có.

Mỗi ý neo về bài như ô của sơ đồ, nên neo của đáp án cũng được kiểm bằng đúng bộ kiểm neo. Bộ chấm (Mốc 2) khớp ô
của sơ đồ với ý của đáp án: hoặc neo của ô rơi vào cùng đoạn với neo của ý, hoặc nhãn/thuật ngữ của ô chứa một
trong `terms` của ý; rồi xét thêm loại ô (`kinds`) và tầng (`tier`). Xem docs/bench.md.
"""
import re
from dataclasses import dataclass, field

from . import model as m
from . import numbers as nums
from .blocks import Blocks
from .check import AnchorChecker, _Diags

TIER = re.compile(r"top|any|under:([A-Za-z0-9_.:-]{1,64})")


@dataclass
class Item:
    id: str
    must: bool
    tier: str
    kinds: list[str]
    what: str
    terms: list[str]
    anchors: list[m.Anchor]


@dataclass
class Relation:
    src: str
    dst: str
    what: str
    ancestor_ok: bool


@dataclass
class Side:
    """Một phía của điểm soi: ô khớp khi một neo của nó rơi vào đoạn của `anchors`, hay `figure` của nó nằm trong
    `figures`."""
    anchors: list[m.Anchor]
    figures: list[str]


@dataclass
class Probe:
    """Điểm soi: thứ độ phủ không đo được. `edge`: sơ đồ có cạnh (loại, mức) từ ô khớp `src` tới ô khớp `dst`.
    `note`: một ô khớp `at` nêu đủ các con số (mỗi nhóm một số) và các từ (mỗi nhóm một từ) cho thấy người dựng đã
    thấy chỗ bài tự lệch."""
    id: str
    type: str
    what: str
    src: Side | None = None
    dst: Side | None = None
    kind: str | None = None
    strengths: list[str] = field(default_factory=list)
    at: Side | None = None
    numbers: list[list[str]] = field(default_factory=list)
    words: list[list[str]] = field(default_factory=list)

    def anchors(self) -> list[m.Anchor]:
        return [a for s in (self.src, self.dst, self.at) if s for a in s.anchors]


@dataclass
class Gold:
    name: str
    sha256: str
    items: dict[str, Item]
    relations: list[Relation]
    probes: list[Probe] = field(default_factory=list)

    @property
    def must(self) -> list[Item]:
        return [i for i in self.items.values() if i.must]


def parse(doc) -> tuple[Gold | None, list[str]]:
    errs: list[str] = []
    if not isinstance(doc, dict) or doc.get("version") != 1:
        return None, ["gold: gốc phải là object có version 1"]
    paper = doc.get("paper") if isinstance(doc.get("paper"), dict) else {}
    sha = paper.get("sha256")
    if not (isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)
            and isinstance(paper.get("name"), str)):
        errs.append("gold: `paper` phải có `name` và `sha256` (64 ký tự hex) của PDF")
    raw_items = doc.get("items") if isinstance(doc.get("items"), list) else []
    raw_relations = doc.get("relations", [])
    if not isinstance(raw_relations, list):
        errs.append("gold: `relations` phải là danh sách")
        raw_relations = []
    items: dict[str, Item] = {}
    for k, r in enumerate(raw_items):
        where = f"items[{k}]"
        if not isinstance(r, dict) or not (isinstance(r.get("id"), str) and m.ID.fullmatch(r["id"])):
            errs.append(f"{where}: thiếu id hợp lệ")
            continue
        iid = r["id"]
        if iid in items:
            errs.append(f"ý {iid}: id trùng")
        tier = r.get("tier")
        kinds = r.get("kinds")
        raw_anchors = r.get("anchors") if isinstance(r.get("anchors"), list) else []
        anchors = [m.Anchor(a.get("page"), a.get("quote"), a.get("block")) for a in raw_anchors
                   if isinstance(a, dict)]
        if not (isinstance(tier, str) and TIER.fullmatch(tier)):
            errs.append(f"ý {iid}: `tier` phải là top, any hay under:<id ý>")
        if not (isinstance(kinds, list) and kinds and all(isinstance(k, str) and k in m.NODE_KINDS for k in kinds)):
            errs.append(f"ý {iid}: `kinds` phải là danh sách loại ô hợp lệ")
        if not isinstance(r.get("must"), bool):
            errs.append(f"ý {iid}: `must` phải là true/false")
        if not anchors or len(anchors) != len(raw_anchors) or any(
                not isinstance(a.page, int) or isinstance(a.page, bool) or not isinstance(a.quote, str)
                or not (a.block is None or (isinstance(a.block, str) and m.ID.fullmatch(a.block))) for a in anchors):
            errs.append(f"ý {iid}: neo phải là danh sách {{page, quote, block?}} hợp lệ, ít nhất một")
        if not isinstance(r.get("terms"), list) or not all(isinstance(t, str) and t for t in r["terms"]):
            errs.append(f"ý {iid}: `terms` phải là danh sách chuỗi")
        items[iid] = Item(iid, r.get("must") is True, tier or "any", kinds or [], str(r.get("what") or ""),
                          list(r.get("terms") or []), anchors)
    for it in items.values():
        mt = TIER.fullmatch(it.tier)
        if mt and mt.group(1) and mt.group(1) not in items:
            errs.append(f"ý {it.id}: `tier` trỏ tới ý {mt.group(1)} không có")
    relations = []
    for k, r in enumerate(raw_relations):
        if not isinstance(r, dict) or not all(isinstance(r.get(x), str) and r[x] in items for x in ("from", "to")):
            errs.append(f"relations[{k}]: from/to phải là id ý có thật")
            continue
        relations.append(Relation(r["from"], r["to"], str(r.get("what") or ""), r.get("ancestor_ok") is True))
    if not any(i.must for i in items.values()):
        errs.append("gold: không có ý nào `must: true`")
    raw_probes = doc.get("probes", [])
    if not isinstance(raw_probes, list):
        errs.append("gold: `probes` phải là danh sách")
        raw_probes = []
    probes = [p for k, r in enumerate(raw_probes) if (p := _probe(r, f"probes[{k}]", errs))]
    if len({p.id for p in probes}) != len(probes):
        errs.append("gold: id điểm soi trùng")
    if errs:
        return None, errs
    return Gold(str(paper.get("name") or ""), str(paper.get("sha256") or ""), items, relations, probes), []


def _anchors(raw) -> list[m.Anchor] | None:
    if not isinstance(raw, list) or not all(isinstance(a, dict) for a in raw):
        return None
    out = [m.Anchor(a.get("page"), a.get("quote"), a.get("block")) for a in raw]
    ok = all(isinstance(a.page, int) and not isinstance(a.page, bool) and isinstance(a.quote, str)
             and (a.block is None or (isinstance(a.block, str) and m.ID.fullmatch(a.block))) for a in out)
    return out if ok else None


def _side(raw, where: str, errs: list[str]) -> Side | None:
    if not isinstance(raw, dict):
        errs.append(f"{where}: phải là object {{anchors?, figures?}}")
        return None
    anchors = _anchors(raw.get("anchors", []))
    figures = raw.get("figures", [])
    if anchors is None:
        errs.append(f"{where}: `anchors` phải là danh sách {{page, quote, block?}}")
        return None
    if not (isinstance(figures, list) and all(isinstance(f, str) and m.ID.fullmatch(f) for f in figures)):
        errs.append(f"{where}: `figures` phải là danh sách id hình")
        return None
    if not anchors and not figures:
        errs.append(f"{where}: cần ít nhất một neo hay một hình")
        return None
    return Side(anchors, list(figures))


def _groups(raw, where: str, errs: list[str], number: bool) -> list[list[str]] | None:
    if not (isinstance(raw, list) and all(isinstance(g, list) and g and all(isinstance(x, str) and x for x in g)
                                          for g in raw)):
        errs.append(f"{where}: phải là danh sách các nhóm (mỗi nhóm một danh sách chuỗi không rỗng)")
        return None
    if number and any(not nums.values_of(x) for g in raw for x in g):
        errs.append(f"{where}: có chuỗi không đọc được thành số")
        return None
    return [list(g) for g in raw]


def _probe(r, where: str, errs: list[str]) -> Probe | None:
    if not isinstance(r, dict) or not (isinstance(r.get("id"), str) and m.ID.fullmatch(r["id"])):
        errs.append(f"{where}: thiếu id hợp lệ")
        return None
    where = f"điểm soi {r['id']}"
    n = len(errs)
    p = Probe(r["id"], r.get("type"), str(r.get("what") or ""))
    if p.type == "edge":
        p.src = _side(r.get("from"), f"{where}.from", errs)
        p.dst = _side(r["to"], f"{where}.to", errs) if "to" in r else None
        p.kind = r.get("kind")
        if p.kind is not None and not (isinstance(p.kind, str) and p.kind in m.EDGE_KINDS):
            errs.append(f"{where}: `kind` phải là một loại cạnh")
        p.strengths = r.get("strength", [])
        if not (isinstance(p.strengths, list) and all(isinstance(x, str) and x in m.STRENGTHS for x in p.strengths)):
            errs.append(f"{where}: `strength` phải là danh sách mức (strong, moderate, weak)")
    elif p.type == "note":
        p.at = _side(r.get("at"), f"{where}.at", errs)
        p.numbers = _groups(r.get("numbers", []), f"{where}.numbers", errs, True) or []
        p.words = _groups(r.get("words", []), f"{where}.words", errs, False) or []
        if not p.numbers and not p.words and len(errs) == n:
            errs.append(f"{where}: `note` cần `numbers` hay `words`")
    else:
        errs.append(f"{where}: `type` phải là edge hay note")
    return p if len(errs) == n else None


def verify_anchors(gold: Gold, blocks: Blocks) -> list[str]:
    """Neo của đáp án phải có thật trong bài, như neo của sơ đồ. Trả các lỗi đã định dạng."""
    if gold.sha256 != blocks.sha256:
        return [f"gold {gold.name}: sha256 khác blocks.json"]
    d, stats = _Diags(), {"anchors": 0, "anchors_ok": 0, "anchors_unverified": 0}
    checker = AnchorChecker(d, blocks, stats)
    for it in gold.items.values():
        checker.check(f"ý {it.id}", it.anchors)
    for p in gold.probes:
        checker.check(f"điểm soi {p.id}", p.anchors())
    figs = [(p.id, f) for p in gold.probes for s in (p.src, p.dst, p.at) if s for f in s.figures]
    bad = [f"điểm soi {pid}: hình {f} không có trong blocks.json" for pid, f in figs if f not in blocks.figures]
    # neo vào trang scan chưa kiểm được (PG210) cũng tính là hỏng: đáp án phải kiểm được hết
    return [f"{x.code} {x.where}: {x.msg} {('→ ' + x.hint) if x.hint else ''}".strip()
            for x in d if x.level == "error" or x.code == "PG210"] + bad
