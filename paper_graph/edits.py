"""Sửa sơ đồ từ trình xem (Mốc 3): nhãn, thuật ngữ, giải thích, trạng thái của ô; toạ độ ô đã kéo.

Chốt chặn ở `.agent/threat-model.md`:
- TM-18: chỉ nhận vài trường, id phải có thật, ô `locked` không sửa chữ được, bản sửa phải qua `check` 0 lỗi (cùng
  blocks) mới được ghi; sửa chữ xong ô thành `accepted` (người dùng đã đọc), khoá là thao tác riêng;
- TM-20: toạ độ là số hữu hạn trong [0, MAX_COORD]; `bai.layout.json` gắn với SHA-256 của bài, id lạ hay tầng sai
  bị bỏ khi đọc.
Toạ độ ở file riêng để skill dựng lại sơ đồ không phải đụng tới: ô còn id thì còn chỗ.
"""
import copy
import math
from pathlib import Path

from . import blocks as blocks_mod
from . import model as m
from .check import check, parse_graph
from .files import InputError, read_json, write_json

MAX_COORD = 20000
LAYOUT_MAX_BYTES = 1024 * 1024
TEXT_FIELDS = {"label": m.MAX_LABEL, "term": m.MAX_TERM, "explain": m.MAX_EXPLAIN}
EDIT_FIELDS = set(TEXT_FIELDS) | {"status"}


class EditError(Exception):
    """Sửa đổi bị từ chối; `diags` là các lỗi của `check` (chữ đã làm sạch) khi có."""

    def __init__(self, msg: str, diags: list[str] | None = None):
        super().__init__(msg)
        self.diags = diags or []


def _node_id(v) -> str:
    if not isinstance(v, str) or not m.ID.fullmatch(v):
        raise EditError("id ô không hợp lệ")
    return v


def edit_node(doc: dict, node_id, changes, bl: blocks_mod.Blocks) -> dict:
    """Bản sơ đồ mới (JSON thô, giữ nguyên các trường khác) sau khi áp `changes` lên ô `node_id`. Ném EditError khi
    sửa đổi không hợp lệ hay làm sơ đồ có lỗi theo `check`."""
    node_id = _node_id(node_id)
    if not isinstance(changes, dict) or not changes:
        raise EditError("không có gì để sửa")
    extra = set(changes) - EDIT_FIELDS
    if extra:
        raise EditError("chỉ sửa được " + ", ".join(sorted(EDIT_FIELDS)))
    new = copy.deepcopy(doc)
    raw = next((n for n in new.get("nodes", []) if isinstance(n, dict) and n.get("id") == node_id), None)
    if raw is None:
        raise EditError(f"không có ô {node_id}")
    text = {k: v for k, v in changes.items() if k in TEXT_FIELDS}
    status = changes.get("status")
    if status is not None and (not isinstance(status, str) or status not in m.STATUSES):
        raise EditError("trạng thái phải là " + ", ".join(sorted(m.STATUSES)))
    if text and raw.get("status") == "locked":
        raise EditError("ô đã khoá: mở khoá trước khi sửa chữ")
    for k, v in text.items():
        if not isinstance(v, str):
            raise EditError(f"`{k}` phải là chữ")
        v = v.strip()
        if len(v) > TEXT_FIELDS[k]:
            raise EditError(f"`{k}` dài quá {TEXT_FIELDS[k]} ký tự")
        if k == "label" and not v:
            raise EditError("nhãn không được trống")
        if v:
            raw[k] = v
        else:
            raw.pop(k, None)
    if status is not None:
        raw["status"] = status
    elif text:
        raw["status"] = "accepted"
    graph, diags = parse_graph(new)
    if graph is None:
        raise EditError("sơ đồ sau khi sửa không đọc được")
    rep = check(graph, bl, None, diags)
    # PG220 (số không có trong chữ bài) chỉ là cảnh báo với sơ đồ dựng sẵn, nhưng sửa tay không được thêm số mới
    before = _numbers_warnings(doc, bl)
    bad = [d for d in rep.diags if d.level == "error" or (d.code == "PG220" and (d.where, d.msg) not in before)]
    if bad:
        raise EditError("sửa đổi làm sơ đồ có lỗi theo `check`, chưa ghi gì",
                        [f"{d.code} {d.where}: {d.msg}" for d in bad][:10])
    return new


def _numbers_warnings(doc: dict, bl: blocks_mod.Blocks) -> set[tuple[str, str]]:
    graph, diags = parse_graph(doc)
    if graph is None:
        return set()
    return {(d.where, d.msg) for d in check(graph, bl, None, diags).diags if d.code == "PG220"}


# ---------------------------------------------------------------------------------------------------- toạ độ

def layout_path(graph_path: Path) -> Path:
    """`bai.layout.json` cạnh `bai.graph.json` (tên dựng từ chính đường dẫn sơ đồ, không lấy từ nội dung file)."""
    return graph_path.with_name(graph_path.name.removesuffix(".graph.json") + ".layout.json")


def coord(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= MAX_COORD:
        return None
    return round(float(v), 1)


def _tiers(graph: m.Graph) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for n in graph.nodes.values():
        out.setdefault(n.parent or "", set()).add(n.id)
    return out


def read_pins(path: Path, graph: m.Graph, strict: bool = False) -> tuple[dict[str, dict[str, tuple[float, float]]], str]:
    """(toạ độ đã ghim theo tầng, cảnh báo). Không có file thì rỗng. Mục hỏng, id lạ, tầng sai bị bỏ. Cả file hỏng
    (không đọc được, sai dạng, của bài khác) thì bỏ kèm cảnh báo, hay ném EditError khi `strict` (trước khi ghi đè:
    không xoá lặng lẽ các ghim cũ chỉ vì file đang hỏng)."""
    if not path.exists():
        return {}, ""
    problem = ""
    try:
        doc = read_json(path, "toạ độ", LAYOUT_MAX_BYTES)
    except InputError as e:
        doc, problem = None, str(e)
    if not problem and (not isinstance(doc, dict) or not isinstance(doc.get("tiers"), dict)):
        problem = "không đúng dạng"
    elif not problem and doc.get("sha256") != graph.sha256:
        problem = "toạ độ của một bài khác (sha256 lệch)"
    if problem:
        if strict:
            raise EditError(f"{path.name} hỏng ({problem}): sửa hay xoá file đó rồi kéo lại")
        return {}, f"bỏ qua {path.name}: {problem}"
    tiers = _tiers(graph)
    out: dict[str, dict[str, tuple[float, float]]] = {}
    dropped = 0
    for key, pos in doc["tiers"].items():
        if key not in tiers or not isinstance(pos, dict):
            dropped += 1
            continue
        for nid, xy in pos.items():
            x, y = (coord(xy[0]), coord(xy[1])) if isinstance(xy, list) and len(xy) == 2 else (None, None)
            if nid in tiers[key] and x is not None and y is not None:
                out.setdefault(key, {})[nid] = (x, y)
            else:
                dropped += 1
    return out, (f"{path.name}: bỏ {dropped} toạ độ không còn khớp sơ đồ" if dropped else "")


def write_pins(path: Path, graph: m.Graph, pins: dict[str, dict[str, tuple[float, float]]]) -> None:
    tiers = {k: {i: [x, y] for i, (x, y) in sorted(v.items())} for k, v in sorted(pins.items()) if v}
    write_json(path, {"version": 1, "sha256": graph.sha256, "tiers": tiers})


def move(pins: dict, graph: m.Graph, tier, moves) -> dict:
    """Ghim ô theo `moves` {id: [x, y]} trong tầng `tier`; `moves` là None thì bỏ mọi ghim của tầng (dàn lại)."""
    tiers = _tiers(graph)
    if not isinstance(tier, str) or tier not in tiers:
        raise EditError("không có tầng này")
    new = {k: dict(v) for k, v in pins.items()}
    if moves is None:
        new.pop(tier, None)
        return new
    if not isinstance(moves, dict) or not 0 < len(moves) <= len(tiers[tier]):
        raise EditError("cần {id: [x, y]} cho ô trong tầng")
    for nid, xy in moves.items():
        if nid not in tiers[tier]:
            raise EditError("ô không thuộc tầng này")
        x, y = (coord(xy[0]), coord(xy[1])) if isinstance(xy, list) and len(xy) == 2 else (None, None)
        if x is None or y is None:
            raise EditError(f"toạ độ phải là số trong khoảng 0–{MAX_COORD}")
        new.setdefault(tier, {})[nid] = (x, y)
    return new
