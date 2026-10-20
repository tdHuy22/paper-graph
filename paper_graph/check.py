"""Bộ kiểm sơ đồ: dạng file, neo về bài gốc, và giới hạn của từng tầng.

Ba nhóm mã lỗi:
    PG1xx  dạng file: thiếu trường, sai kiểu, id trùng, cạnh treo, vòng tầng
    PG2xx  neo: câu trích có thật ở đúng trang của đúng bài, đủ dài để không khớp bừa
    PG3xx  tầng: không quá 9 ô, không ô lẻ loi, tuyên bố có bằng chứng, bảng kết quả có ô nói tới

Neo đạt nghĩa là câu trích có thật ở trang đã ghi. Nó không chứng minh ô diễn giải đúng câu đó: phần ấy cần
người đọc, hay bước review ở Mốc 2.
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

from . import figlinks
from . import model as m
from .blocks import Blocks
from .numbers import missing as missing_numbers
from .text import safe, squash, word_count

MAX_PER_TIER = 9
MIN_QUOTE_WORDS = 4
MIN_QUOTE_CHARS = 20  # sau chuẩn hoá: "the model" không đủ làm neo
LONG_QUOTE_WORDS = 40
LONG_LABEL = 60
MAX_DEPTH = 3
# Trần số phần tử (TM-1): sơ đồ đúng luật (9 ô mỗi tầng, 3 tầng) có tối đa 819 ô. Vượt trần thì phần thừa bị bỏ
# qua và báo PG111, để một file hàng chục nghìn ô không giữ máy hàng giờ.
MAX_NODES = 2000
MAX_EDGES = 5000
MAX_GROUPS = 500
MAX_ANCHORS = 10  # mỗi ô hay cạnh
MAX_CLOSEST = 50  # số neo hỏng được tìm gợi ý (trang khác có câu trích, đoạn gần giống nhất): hai bước đắt nhất


@dataclass
class Diag:
    level: str  # "error" | "warning"
    code: str
    where: str
    msg: str
    hint: str = ""


@dataclass
class Report:
    diags: list[Diag]
    stats: dict

    @property
    def errors(self) -> int:
        return sum(d.level == "error" for d in self.diags)

    @property
    def warnings(self) -> int:
        return sum(d.level == "warning" for d in self.diags)

    def ok(self, strict: bool = False) -> bool:
        return self.errors == 0 and (not strict or self.warnings == 0)

    def to_json(self, strict: bool = False) -> dict:
        return {"ok": self.ok(strict), "errors": self.errors, "warnings": self.warnings, "stats": self.stats,
                "diagnostics": [asdict(d) for d in self.diags]}


class _Diags(list):
    """Chẩn đoán được làm sạch ngay khi tạo (TM-2), nên cả bản chữ lẫn bản `--json` đều không mang ký tự điều
    khiển hay ký tự đảo chiều từ input ra terminal."""

    def err(self, code, where, msg, hint=""):
        self.append(Diag("error", code, safe(where, 200), safe(msg, 1000), safe(hint, 1000)))

    def warn(self, code, where, msg, hint=""):
        self.append(Diag("warning", code, safe(where, 200), safe(msg, 1000), safe(hint, 1000)))


# ---------------------------------------------------------------------------------------------------- dạng file

def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _one_of(v, allowed: set) -> bool:
    """`v in allowed` mà không văng TypeError khi model ghi list hay object vào trường liệt kê."""
    return isinstance(v, str) and v in allowed


def _capped(d: _Diags, where: str, name: str, items: list, limit: int) -> list:
    if len(items) > limit:
        d.err("PG111", where, f"{len(items)} {name}, quá trần {limit}: phần thừa bị bỏ qua")
        return items[:limit]
    return items


def _text(d: _Diags, where: str, name: str, v, limit: int, required: bool) -> str:
    if v is None and not required:
        return ""
    if not isinstance(v, str) or (required and not v.strip()):
        d.err("PG101", where, f"`{name}` phải là chuỗi{' không rỗng' if required else ''}")
        return ""
    if len(v) > limit:
        d.err("PG101", where, f"`{name}` dài {len(v)} ký tự, quá {limit}")
        return v[:limit]
    try:
        v.encode("utf-8")
    except UnicodeEncodeError:  # "\ud800" trong JSON: không ghi ra UTF-8 được, trình xem và VietPaper sẽ vỡ
        d.err("PG101", where, f"`{name}` có ký tự Unicode hỏng (surrogate lẻ)")
        return v.encode("utf-8", "replace").decode("utf-8")
    return v


def _unknown(d: _Diags, where: str, raw: dict, allowed: set) -> None:
    extra = sorted(set(raw) - allowed)
    if extra:
        d.warn("PG110", where, "trường lạ: " + ", ".join(safe(k, 40) for k in extra),
               "trường đúng: " + ", ".join(sorted(allowed)))


def _anchors(d: _Diags, where: str, raw) -> list[m.Anchor]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        d.err("PG101", where, "`anchors` phải là danh sách")
        return []
    out = []
    for k, a in enumerate(_capped(d, where, "neo", raw, MAX_ANCHORS), 1):
        w = f"{where} · neo {k}"
        if not isinstance(a, dict):
            d.err("PG101", w, "neo phải là object {page, quote, block?}")
            continue
        _unknown(d, w, a, m.ANCHOR_FIELDS)
        page, quote, block = a.get("page"), a.get("quote"), a.get("block")
        if not _is_int(page) or page < 1:
            d.err("PG101", w, "`page` phải là số trang PDF, đếm từ 1")
            continue
        quote = _text(d, w, "quote", quote, m.MAX_QUOTE, True)
        if not quote:
            continue
        if block is not None and not (isinstance(block, str) and m.ID.fullmatch(block)):
            d.err("PG103", w, "`block` phải là id đoạn trong blocks.json")
            block = None
        out.append(m.Anchor(page, quote, block))
    return out


def _id(d: _Diags, where: str, v, name: str = "id") -> str | None:
    if isinstance(v, str) and m.ID.fullmatch(v):
        return v
    d.err("PG103", where, f"`{name}` phải khớp [A-Za-z0-9_.:-], 1–64 ký tự, không phải {safe(repr(v), 50)}")
    return None


def parse_graph(doc) -> tuple[m.Graph | None, list[Diag]]:
    d = _Diags()
    if not isinstance(doc, dict):
        d.err("PG101", "sơ đồ", "gốc phải là object")
        return None, d
    _unknown(d, "sơ đồ", doc, {"version", "paper", "nodes", "edges", "groups"})
    if doc.get("version") != m.VERSION:
        d.err("PG109", "sơ đồ", f"`version` phải là {m.VERSION}")
    paper = doc.get("paper")
    if not isinstance(paper, dict):
        d.err("PG101", "paper", "thiếu object `paper` {title, sha256, blocks}")
        paper = {}
    _unknown(d, "paper", paper, {"title", "sha256", "blocks"})
    title = _text(d, "paper", "title", paper.get("title"), 300, True)
    sha = paper.get("sha256")
    if not (isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)):
        d.err("PG101", "paper", "`sha256` phải là SHA-256 của PDF gốc (64 ký tự hex thường)")
        sha = ""
    blocks_file = paper.get("blocks")
    if blocks_file is not None and not isinstance(blocks_file, str):
        d.err("PG101", "paper", "`blocks` phải là tên file")
        blocks_file = None

    nodes: dict[str, m.Node] = {}
    raw_nodes = doc.get("nodes")
    if not isinstance(raw_nodes, list):
        d.err("PG101", "sơ đồ", "`nodes` phải là danh sách")
        raw_nodes = []
    for i, r in enumerate(_capped(d, "sơ đồ", "ô", raw_nodes, MAX_NODES)):
        where = f"nodes[{i}]"
        if not isinstance(r, dict):
            d.err("PG101", where, "ô phải là object")
            continue
        nid = _id(d, where, r.get("id"))
        if nid is None:
            continue
        where = f"ô {nid}"
        if nid in nodes:
            d.err("PG104", where, "id trùng với một ô khác")
            continue
        _unknown(d, where, r, m.NODE_FIELDS)
        parent = r.get("parent")
        if parent is not None:
            parent = _id(d, where, parent, "parent")
        kind = r.get("kind")
        if not _one_of(kind, m.NODE_KINDS):
            d.err("PG102", where, f"`kind` {safe(repr(kind), 30)} không có", "dùng: " + ", ".join(sorted(m.NODE_KINDS)))
            kind = "context"
        basis = r.get("basis", "paper")
        if not _one_of(basis, m.BASES):
            d.err("PG102", where, "`basis` phải là paper hoặc inference")
            basis = "paper"
        status = r.get("status", "draft")
        if not _one_of(status, m.STATUSES):
            d.err("PG102", where, "`status` phải là draft, accepted hoặc locked")
            status = "draft"
        figure = r.get("figure")
        if figure is not None:
            figure = _id(d, where, figure, "figure")
        nodes[nid] = m.Node(
            nid, parent, kind,
            _text(d, where, "label", r.get("label"), m.MAX_LABEL, True),
            _text(d, where, "term", r.get("term"), m.MAX_TERM, False),
            _text(d, where, "explain", r.get("explain"), m.MAX_EXPLAIN, False),
            _anchors(d, where, r.get("anchors")), basis, figure, status)

    edges: list[m.Edge] = []
    raw_edges = doc.get("edges", [])
    if not isinstance(raw_edges, list):
        d.err("PG101", "sơ đồ", "`edges` phải là danh sách")
        raw_edges = []
    for i, r in enumerate(_capped(d, "sơ đồ", "cạnh", raw_edges, MAX_EDGES)):
        where = f"edges[{i}]"
        if not isinstance(r, dict):
            d.err("PG101", where, "cạnh phải là object")
            continue
        src, dst = _id(d, where, r.get("from"), "from"), _id(d, where, r.get("to"), "to")
        if src is None or dst is None:
            continue
        where = f"cạnh {src}→{dst}"
        _unknown(d, where, r, m.EDGE_FIELDS)
        kind = r.get("kind")
        if not _one_of(kind, m.EDGE_KINDS):
            d.err("PG102", where, f"`kind` {safe(repr(kind), 30)} không có", "dùng: " + ", ".join(sorted(m.EDGE_KINDS)))
            kind = "relates"
        strength = r.get("strength")
        if kind in ("supports", "contradicts") and not _one_of(strength, m.STRENGTHS):
            d.err("PG102", where, f"cạnh {kind} cần `strength`: strong, moderate hoặc weak")
            strength = None
        elif strength is not None and not _one_of(strength, m.STRENGTHS):
            d.err("PG102", where, "`strength` phải là strong, moderate hoặc weak")
            strength = None
        edges.append(m.Edge(src, dst, kind, _text(d, where, "label", r.get("label"), m.MAX_EDGE_LABEL, False),
                            strength, _anchors(d, where, r.get("anchors"))))

    groups: list[m.Group] = []
    raw_groups = doc.get("groups", [])
    if not isinstance(raw_groups, list):
        d.err("PG101", "sơ đồ", "`groups` phải là danh sách")
        raw_groups = []
    seen_groups: set[str] = set()
    for i, r in enumerate(_capped(d, "sơ đồ", "nhóm", raw_groups, MAX_GROUPS)):
        where = f"groups[{i}]"
        if not isinstance(r, dict):
            d.err("PG101", where, "nhóm phải là object")
            continue
        gid = _id(d, where, r.get("id"))
        if gid is None:
            continue
        where = f"nhóm {gid}"
        if gid in seen_groups or gid in nodes:
            d.err("PG104", where, "id trùng với một ô hay nhóm khác")
            continue
        seen_groups.add(gid)
        _unknown(d, where, r, m.GROUP_FIELDS)
        parent = r.get("parent")
        if parent is not None:
            parent = _id(d, where, parent, "parent")
        members = r.get("members")
        if not isinstance(members, list) or not members:
            d.err("PG101", where, "`members` phải là danh sách id ô, ít nhất một")
            members = []
        members = [x for x in (_id(d, where, x, "members") for x in _capped(d, where, "thành viên", members,
                                                                           MAX_NODES)) if x]
        groups.append(m.Group(gid, parent, _text(d, where, "label", r.get("label"), m.MAX_LABEL, True), members))

    return m.Graph(title, sha, blocks_file, nodes, edges, groups), d


# ---------------------------------------------------------------------------------------------------- kiểm

def check(graph: m.Graph, blocks: Blocks | None, pdf_sha256: str | None = None,
          parse_diags: list[Diag] | None = None, base: m.Graph | None = None) -> Report:
    d = _Diags(parse_diags or [])
    nodes = graph.nodes

    # Tầng: parent phải là ô có thật, không vòng
    for n in nodes.values():
        if n.parent is not None and n.parent not in nodes:
            d.err("PG105", f"ô {n.id}", f"`parent` {n.parent} không phải ô nào")
            n.parent = None
    # Vòng: đi ngược lên từ mỗi ô, mỗi ô chỉ đi qua một lần (O(n)); gặp lại một ô của chính lượt đang đi là vòng,
    # cắt vòng ở đó rồi kiểm tiếp.
    done: set[str] = set()
    for n in nodes.values():
        path: dict[str, int] = {}
        cur = n
        while cur.id not in done and cur.id not in path:
            path[cur.id] = len(path)
            if cur.parent is None:
                break
            cur = nodes[cur.parent]
        if cur.id in path and cur.parent is not None and cur.id not in done:
            ring = list(path)[path[cur.id]:]
            d.err("PG105", f"ô {cur.id}", "chuỗi `parent` khép thành vòng: " + " → ".join(ring + [cur.id]))
            cur.parent = None
        done.update(path)
    depth: dict[str, int] = {}
    for n in nodes.values():
        chain, cur = [], n
        while cur.id not in depth and cur.parent is not None:
            chain.append(cur)
            cur = nodes[cur.parent]
        top = depth.setdefault(cur.id, 0)  # chưa có trong depth thì cur là ô tầng đầu
        for k, x in enumerate(reversed(chain), 1):
            depth[x.id] = top + k

    tiers: dict[str | None, list[m.Node]] = defaultdict(list)
    for n in nodes.values():
        tiers[n.parent].append(n)

    # Cạnh
    linked: Counter = Counter()
    for e in graph.edges:
        where = f"cạnh {e.src}→{e.dst}"
        missing = [x for x in (e.src, e.dst) if x not in nodes]
        if missing:
            d.err("PG106", where, "trỏ tới ô không có: " + ", ".join(missing))
            continue
        if nodes[e.src].parent != nodes[e.dst].parent:
            d.err("PG107", where, "nối hai ô khác tầng", "cạnh chỉ nối các ô cùng `parent`")
            continue
        if e.src == e.dst:
            d.err("PG106", where, "cạnh tự nối vào chính nó")
            continue
        linked[e.src] += 1
        linked[e.dst] += 1
        if e.kind in ("supports", "contradicts") and (nodes[e.src].kind != "evidence" or nodes[e.dst].kind != "claim"):
            d.warn("PG306", where, f"cạnh {e.kind} nên đi từ ô evidence tới ô claim")

    # Nhóm
    in_group: dict[str, str] = {}
    for g in graph.groups:
        if g.parent is not None and g.parent not in nodes:
            d.err("PG108", f"nhóm {g.id}", f"`parent` {g.parent} không phải ô nào")
        for x in g.members:
            if x not in nodes:
                d.err("PG108", f"nhóm {g.id}", f"thành viên {x} không phải ô nào")
            elif nodes[x].parent != g.parent:
                d.err("PG108", f"nhóm {g.id}", f"thành viên {x} khác tầng với nhóm")
            elif x in in_group:
                d.err("PG108", f"nhóm {g.id}", f"ô {x} đã thuộc nhóm {in_group[x]}", "nhóm không lồng nhau")
            else:
                in_group[x] = g.id

    # Tầng: số ô, ô lẻ loi, độ sâu
    if not tiers.get(None):
        d.err("PG301", "sơ đồ", "tầng đầu không có ô nào (mọi ô đều có `parent`)")
    for parent, members in tiers.items():
        name = "tầng đầu" if parent is None else f"tầng dưới của {parent}"
        if len(members) > MAX_PER_TIER:
            d.err("PG300", name, f"{len(members)} ô, quá {MAX_PER_TIER}",
                  "gom bớt vào một ô rồi đưa chi tiết xuống tầng dưới của ô đó")
        if parent is not None and len(members) == 1:
            d.warn("PG302", name, "chỉ có một ô: mở ra không thêm được gì", "gộp vào ô cha, hoặc tách thành vài bước")
        if len(members) >= 2:
            for n in members:
                if not linked[n.id] and n.id not in in_group:
                    d.warn("PG303", f"ô {n.id}", f"đứng lẻ trong {name}, không cạnh nào nối tới")
    for n in nodes.values():
        if depth.get(n.id, 0) >= MAX_DEPTH:
            d.warn("PG308", f"ô {n.id}", f"nằm ở tầng thứ {depth[n.id] + 1}; quá {MAX_DEPTH} tầng thì khó lần lại")
        if len(n.label) > LONG_LABEL:
            d.warn("PG304", f"ô {n.id}", f"nhãn dài {len(n.label)} ký tự; trên {LONG_LABEL} thì ô khó đọc",
                   "để chi tiết vào `explain`")

    # Tuyên bố và bằng chứng
    backed = {e.dst for e in graph.edges if e.kind in ("supports", "contradicts") and e.dst in nodes}
    used = {e.src for e in graph.edges if e.kind in ("supports", "contradicts") and e.src in nodes}
    for n in nodes.values():
        if n.kind == "claim" and n.id not in backed:
            d.warn("PG305", f"ô {n.id}", "tuyên bố chưa có bằng chứng nào chống đỡ trong sơ đồ")
        if n.kind == "evidence" and n.id not in used:
            d.warn("PG307", f"ô {n.id}", "bằng chứng không nối tới tuyên bố nào")

    # Neo
    stats = {"nodes": len(nodes), "tiers": len(tiers), "depth": 1 + max(depth.values(), default=0),
             "anchors": 0, "anchors_ok": 0, "anchors_unverified": 0}
    sha_ok = True
    if blocks is not None and graph.sha256 and blocks.sha256 != graph.sha256:
        d.err("PG206", "paper", "SHA-256 của sơ đồ khác SHA-256 của blocks.json: hai file không cùng một bài",
              f"sơ đồ {graph.sha256[:12]}…, blocks {blocks.sha256[:12]}…")
        sha_ok = False
    if pdf_sha256 is not None and graph.sha256 and pdf_sha256 != graph.sha256:
        d.err("PG206", "paper", "SHA-256 của sơ đồ khác SHA-256 của PDF đưa vào `--pdf`")
        sha_ok = False
    if blocks is None:
        d.err("PG211", "paper", "không có blocks.json nên không kiểm được neo",
              "ghi `paper.blocks` trong sơ đồ hoặc truyền --blocks")
    elif not sha_ok:
        blocks = None  # blocks của bài khác: đối chiếu neo hay hình với nó chỉ sinh lỗi giả

    anchors = AnchorChecker(d, blocks, stats)
    sources: dict[str, str] = {}  # chữ bài mà mỗi ô dựa vào: đoạn được neo, chú thích và chữ của hình
    hits: dict[str, list[str]] = {}  # đoạn chứa câu trích của từng ô, để gắn hình theo chú thích (PG309)
    for n in nodes.values():
        where = f"ô {n.id}"
        if not n.anchors:
            if n.basis == "paper":
                d.err("PG200", where, "ô dựa trên bài (`basis: paper`) mà không có neo nào",
                      "thêm neo, hoặc ghi `basis: inference` nếu đó là suy luận của người dựng")
            else:
                d.warn("PG208", where, "ô suy luận không neo vào tiền đề nào trong bài")
        if n.figure is not None and blocks is not None and n.figure not in blocks.figures:
            d.err("PG207", where, f"hình {n.figure} không có trong blocks.json")
        hit = anchors.check(where, n.anchors)
        hits[n.id] = sorted(hit)
        sources[n.id] = _sources(n, hit, blocks)
        if blocks is not None:
            _numbers(d, where, f"{n.label}\n{n.term}\n{n.explain}", sources[n.id])
    for e in graph.edges:
        hit = anchors.check(f"cạnh {e.src}→{e.dst}", e.anchors)
        if blocks is not None and e.label:
            # nhãn cạnh nói về quan hệ giữa hai ô: số của nó phải có trong chữ bài của một trong hai đầu
            own = "\n".join(blocks.blocks[b].text for b in hit)
            _numbers(d, f"cạnh {e.src}→{e.dst}", e.label,
                     "\n".join([own, sources.get(e.src, ""), sources.get(e.dst, "")]))
    if blocks is not None:
        for g in graph.groups:
            # nhãn nhóm tóm các thành viên trong ngữ cảnh ô cha ("Encoder · lặp 6 lần" dựa vào ô method)
            ctx = [sources.get(x, "") for x in g.members] + [sources.get(g.parent, "") if g.parent else ""]
            _numbers(d, f"nhóm {g.id}", g.label, "\n".join(ctx))
        if nodes:  # sơ đồ rỗng đã có PG301; báo thêm mọi bảng của bài chỉ là nhiễu
            _unlinked_figures(d, graph, blocks, hits)
    if base is not None:
        _against_base(d, graph, base)

    return Report(list(d), stats)


_REFERENCE_TITLES = {squash(t) for t in ("References", "Bibliography", "Tài liệu tham khảo")}


def _main_text_end(blocks: Blocks) -> tuple[int, float] | None:
    """(trang, toạ độ y) nơi tài liệu tham khảo bắt đầu; None khi bài không có. Phụ lục nằm sau đó."""
    starts = [(b.page, b.bbox[1]) for b in blocks.blocks.values()
              if b.label == "reference_content"
              or (b.label == "paragraph_title" and squash(b.text.lstrip("0123456789. ")) in _REFERENCE_TITLES)]
    return min(starts) if starts else None


def _unlinked_figures(d: _Diags, graph: m.Graph, blocks: Blocks, hits: dict[str, list[str]]) -> None:
    """PG309: bảng, biểu đồ ở phần chính của bài (trước tài liệu tham khảo) mà không ô nào nói tới trực tiếp (trường
    `figure`, câu trích ở chú thích, hay nhắc "Bảng 3" trong ô). Bảng kết quả bị bỏ sót là chỗ sơ đồ thiếu thông tin
    mà các luật khác không thấy: mọi neo vẫn đúng, chỉ là cả một phần bằng chứng của bài vắng mặt. Chỉ xét vùng có
    chú thích đánh số ("Table 3", "Figure 2"): vùng không chú thích hay chú thích "(b) …" thường là mảnh của một hình
    nhiều phần, báo nó chỉ thêm nhiễu."""
    end = _main_text_end(blocks)
    _, shown = figlinks.link(graph, blocks, hits)
    for fid, f in sorted(blocks.figures.items(), key=lambda kv: (kv[1]["page"], kv[1]["bbox"][1], kv[0])):
        info = shown.get(fid, {})
        if f["kind"] not in ("table", "chart") or not info.get("label") or info.get("nodes"):
            continue
        if end is not None and (f["page"], f["bbox"][1]) >= end:
            continue
        d.warn("PG309", f"hình {fid}", f"{info['label']} (tr.{f['page']}) thuộc phần chính của bài mà không ô nào nói "
               f"tới: «{safe(info['caption'], 90)}»",
               "đưa kết quả của nó vào ô liên quan (trường `figure`, neo câu chú thích, hay nhắc tên bảng trong giải "
               "thích); bảng chỉ ghi thiết lập, ví dụ thì có thể để cảnh báo này lại")


def _sources(n: m.Node, hit: set[str], blocks: Blocks | None) -> str:
    if blocks is None:
        return ""
    texts = [blocks.blocks[b].text for b in sorted(hit)]
    fig = blocks.figures.get(n.figure) if n.figure else None
    if fig:
        texts.append(fig.get("text") or "")
        if fig.get("caption") in blocks.blocks:
            texts.append(blocks.blocks[fig["caption"]].text)
    return "\n".join(texts)


def _numbers(d: _Diags, where: str, text: str, source: str) -> None:
    """PG220 (TM-7): số trong chữ của ô (nhãn, thuật ngữ, giải thích), nhãn cạnh hay nhãn nhóm phải có trong chữ bài
    mà nó dựa vào. Ô không có neo hợp lệ thì mọi số của nó đều bị báo."""
    lost = missing_numbers(text, source)
    if lost:
        d.warn("PG220", where, "số không có trong chữ bài mà nó dựa vào: " + ", ".join(lost),
               "thêm neo vào câu có số đó, hay viết đúng số như trong bài")


def _against_base(d: _Diags, graph: m.Graph, base: m.Graph) -> None:
    """PG401/PG402 (TM-8): ô người dùng đã khoá phải còn nguyên khi dựng lại; ô đã duyệt bị đổi thì báo."""
    for old in base.nodes.values():
        if old.status not in ("locked", "accepted"):
            continue
        new = graph.nodes.get(old.id)
        if new is None:
            changed = ["bị xoá"]
        else:
            changed = [f for f in ("parent", "kind", "label", "term", "explain", "anchors", "basis", "figure", "status")
                       if getattr(old, f) != getattr(new, f)]
        if old.status == "locked" and new is not None:
            changed += _links_changed(old.id, graph, base)
        if not changed:
            continue
        what = ", ".join(changed)
        if old.status == "locked":
            d.err("PG401", f"ô {old.id}", f"ô bạn đã khoá bị đổi khi dựng lại: {what}",
                  "giữ nguyên ô locked; muốn đổi thì người dùng mở khoá trước")
        else:
            d.warn("PG402", f"ô {old.id}", f"ô đã duyệt (accepted) bị đổi: {what}", "nêu lý do trong báo cáo dựng")


def _links_changed(nid: str, graph: m.Graph, base: m.Graph) -> list[str]:
    """Cạnh giữa hai ô cùng locked và nhóm chứa ô locked cũng thuộc phần người dùng đã khoá."""
    locked = {x.id for x in base.nodes.values() if x.status == "locked"}

    def edges(g: m.Graph) -> list:  # danh sách có thứ tự, giữ cả cạnh trùng cặp ô
        return sorted(repr((e.src, e.dst, e.kind, e.label, e.strength, e.anchors)) for e in g.edges
                      if nid in (e.src, e.dst) and e.src in locked and e.dst in locked)

    def groups(g: m.Graph) -> dict:
        return {x.id: (x.label, x.parent, sorted(x.members)) for x in g.groups if nid in x.members}

    out = []
    if edges(base) != edges(graph):
        out.append("cạnh nối với ô locked khác")
    if groups(base) != groups(graph):
        out.append("nhóm")
    return out


class AnchorChecker:
    """Kiểm từng neo với blocks.json; `blocks` None nghĩa là không kiểm được (thiếu file, hay file của bài khác)."""

    def __init__(self, d: _Diags, blocks: Blocks | None, stats: dict):
        self.d, self.blocks, self.stats = d, blocks, stats
        self.closest_left = MAX_CLOSEST

    def check(self, where: str, anchors: list[m.Anchor]) -> set[str]:
        """Kiểm các neo của một ô hay cạnh; trả id các đoạn mà neo hợp lệ rơi vào."""
        d, blocks, stats = self.d, self.blocks, self.stats
        found: set[str] = set()
        for k, a in enumerate(anchors, 1):
            w = f"{where} · neo {k}"
            stats["anchors"] += 1
            q = squash(a.quote)
            words = word_count(a.quote)
            if words < MIN_QUOTE_WORDS or len(q) < MIN_QUOTE_CHARS:
                d.err("PG202", w, f"câu trích quá ngắn ({words} từ): khớp ở đâu cũng được nên không chứng minh gì",
                      f"chép ít nhất {MIN_QUOTE_WORDS} từ liền nhau, đủ riêng để chỉ có ở đúng chỗ đó")
                continue
            if words > LONG_QUOTE_WORDS:
                d.warn("PG203", w, f"câu trích dài {words} từ; neo chỉ cần 4–15 từ")
            if blocks is None:
                stats["anchors_unverified"] += 1
                continue
            if a.page not in blocks.pages:
                d.err("PG204", w, f"tr.{a.page} không có; bài có {blocks.page_count} trang")
                continue
            if a.block is not None and a.block not in blocks.blocks:
                d.err("PG205", w, f"đoạn {a.block} không có trong blocks.json")
                continue
            if blocks.pages[a.page].get("text") is False:
                d.warn("PG210", w, f"tr.{a.page} là ảnh scan chưa có chữ: không kiểm được câu trích",
                       "chạy lại `extract` với --ocr")
                stats["anchors_unverified"] += 1
                continue
            hits = blocks.find_all(q, a.page)
            if not hits:
                self._not_found(w, a, q)
                continue
            if a.block is not None and not any(a.block in h.blocks for h in hits):
                d.err("PG205", w, f"câu trích không nằm trong đoạn {a.block}",
                      f"nằm trong {', '.join(sorted({b for h in hits for b in h.blocks}))}")
                continue
            stats["anchors_ok"] += 1
            found.update(b for h in hits for b in h.blocks)
        return found

    def _not_found(self, w: str, a: m.Anchor, q: str) -> None:
        if self.closest_left <= 0:
            self.d.err("PG201", w, f"câu trích không có ở tr.{a.page} «{safe(a.quote, 90)}»",
                       f"đã quá {MAX_CLOSEST} neo hỏng, không tìm gợi ý cho các neo sau")
            return
        self.closest_left -= 1
        elsewhere = self.blocks.find_anywhere(q)
        if elsewhere:
            h = elsewhere[0]
            self.d.err("PG201", w, f"câu trích không có ở tr.{a.page} «{safe(a.quote, 90)}»",
                       f"có ở tr.{h.page} (đoạn {', '.join(h.blocks)})")
            return
        hint = "không có ở trang nào: chép lại nguyên văn từ chữ trong blocks.json"
        ratio, near = self.blocks.closest(q, a.page)
        if ratio >= 0.5:
            hint = f"gần nhất trên tr.{a.page}: «{safe(near, 90)}» (khớp {round(ratio * 100)}%)"
        self.d.err("PG201", w, f"câu trích không có trong bài «{safe(a.quote, 90)}»", hint)


# ---------------------------------------------------------------------------------------------------- in ra

def render(report: Report, title: str) -> str:
    s = report.stats
    head = (f"sơ đồ «{safe(title, 80)}» · {s['nodes']} ô, {s['tiers']} tầng, sâu {s['depth']} · "
            f"neo: {s['anchors_ok']}/{s['anchors']} có thật")
    if s["anchors_unverified"]:
        head += f", {s['anchors_unverified']} chưa kiểm được"
    lines = [head, ""]
    order = sorted(report.diags, key=lambda x: (x.level != "error", x.code))
    for x in order:
        mark = "✗ LỖI" if x.level == "error" else "⚠ CẢNH BÁO"
        lines.append(f"{mark} {x.code}  {safe(x.where, 80)}")
        lines.append(f"  {safe(x.msg, 400)}")
        if x.hint:
            lines.append(f"  → {safe(x.hint, 400)}")
    if order:
        lines.append("")
    lines.append(f"kết quả: {report.errors} lỗi, {report.warnings} cảnh báo")
    return "\n".join(lines)
