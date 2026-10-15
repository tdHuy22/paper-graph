"""Gắn hình, bảng của bài vào ô liên quan (Mốc 3): trình xem hiện chúng trong thẻ của ô, và danh sách hình có đường về ô.

Một ô liên quan tới một hình khi (theo thứ tự ưu tiên, trùng thì giữ lý do đầu):
1. `own`: trường `figure` của ô;
2. `caption`: một câu trích của ô nằm trong đoạn chú thích của hình;
3. `mention`: nhãn, giải thích hay câu trích nhắc "Bảng 2", "Table 2", "Hình 1", "Fig. 1", khớp số ở đầu chú thích;
4. `evidence`: hình trực tiếp (1–3) của ô nối vào bằng cạnh `supports` hay `contradicts`;
5. `child`: hình trực tiếp của ô ở tầng dưới.
Chữ chú thích lấy từ blocks.json (không tin cậy): chỉ là dữ liệu cho trình xem, đi qua cùng chốt chặn TM-13.
"""
import re

from . import blocks as blocks_mod
from . import model as m

MAX_PER_NODE = 6
MAX_CAPTION = 400
_WORDS = r"(Figures?|Figs?\.?|Tables?|Hình|Bảng)"
_NUM = r"\d{1,3}(?!\d)"  # "Figure 1a" là hình 1; "Figure 10" không phải hình 1
_CAPTION = re.compile(r"^\s*" + _WORDS + r"\s*(" + _NUM + ")", re.I)
# "Bảng 2", "Tables 1 and 2", "Hình 1, 2 và 3": dãy số phải kết bằng and/và/& thì mới tính các số sau số đầu,
# để "Table 2, 3 layers" không thành bảng 3
_MENTION = re.compile(r"\b" + _WORDS + r"\s*(" + _NUM + r"(?:(?:\s*,\s*" + _NUM + r")*\s*,?\s*(?:and|và|&)\s*" + _NUM
                      + r")?)", re.I)
_SHOWN = {"figure": "Hình", "table": "Bảng"}
DIRECT = ("own", "caption", "mention")


def _kind(word: str) -> str:
    w = word.lower()
    return "table" if w.startswith(("tab", "bảng")) else "figure"


def _clean(text: str, limit: int) -> str:
    text = " ".join(text.split()).encode("utf-8", "replace").decode("utf-8")  # blocks sửa tay có thể chứa surrogate
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def catalog(bl: blocks_mod.Blocks) -> dict[str, dict]:
    """Mỗi hình trong blocks: loại, trang, nhãn ("Bảng 2" nếu chú thích bắt đầu như vậy), chữ chú thích."""
    out = {}
    for fid, f in bl.figures.items():
        cap = bl.blocks.get(f.get("caption") or "")
        text = cap.text if cap else ""
        mt = _CAPTION.match(text)
        out[fid] = {"kind": f.get("kind", ""), "page": f.get("page"), "caption_block": cap.id if cap else None,
                    "key": (_kind(mt.group(1)), int(mt.group(2))) if mt else None,
                    "label": f"{_SHOWN[_kind(mt.group(1))]} {int(mt.group(2))}" if mt else "",
                    "caption": _clean(text, MAX_CAPTION)}
    return out


def _mentions(n: m.Node) -> set[tuple[str, int]]:
    texts = [n.label, n.explain] + [a.quote for a in n.anchors]
    return {(_kind(w), int(k)) for t in texts for w, nums in _MENTION.findall(t or "")
            for k in re.findall(r"\d+", nums)}


def link(graph: m.Graph, bl: blocks_mod.Blocks, anchor_blocks: dict[str, list[str | None]]) -> tuple[dict, dict]:
    """(hình liên quan của từng ô [{id, why, via}], danh mục hình kèm các ô dùng trực tiếp). `anchor_blocks[id]` là
    đoạn chứa từng câu trích của ô (None khi không tìm được), như trình xem đã tính."""
    figs = catalog(bl)
    by_caption = {f["caption_block"]: fid for fid, f in figs.items() if f["caption_block"]}
    by_key: dict[tuple, list[str]] = {}
    for fid, f in figs.items():
        if f["key"]:
            by_key.setdefault(f["key"], []).append(fid)

    direct: dict[str, list[tuple[str, str]]] = {}
    for n in graph.nodes.values():
        found: list[tuple[str, str]] = []
        if n.figure and n.figure in figs:
            found.append((n.figure, "own"))
        found += [(by_caption[b], "caption") for b in anchor_blocks.get(n.id, []) if b in by_caption]
        found += [(fid, "mention") for key in sorted(_mentions(n)) for fid in by_key.get(key, [])]
        direct[n.id] = found

    related: dict[str, list[dict]] = {}
    children: dict[str, list[str]] = {}
    for n in graph.nodes.values():
        if n.parent:
            children.setdefault(n.parent, []).append(n.id)
    for n in graph.nodes.values():
        cands = [(fid, why, "") for fid, why in direct[n.id]]
        for e in graph.edges:
            if e.dst == n.id and e.kind in ("supports", "contradicts") and e.src in direct:
                cands += [(fid, "evidence", e.src) for fid, _ in direct[e.src]]
        for c in children.get(n.id, []):
            cands += [(fid, "child", c) for fid, _ in direct[c]]
        seen: set[str] = set()
        out = []
        for fid, why, via in cands:
            if fid not in seen:
                seen.add(fid)
                out.append({"id": fid, "why": why, "via": via})
        related[n.id] = out[:MAX_PER_NODE]
    hidden = {fid for nid, found in direct.items() for fid, _ in found}

    used: dict[str, list[str]] = {}  # link ngược: chỉ ô có hình đó trong thẻ (sau khi cắt MAX_PER_NODE)
    for nid, rs in related.items():
        for r in rs:
            if r["why"] in DIRECT:
                used.setdefault(r["id"], []).append(nid)
    shown = {fid: {"kind": f["kind"], "page": f["page"], "label": f["label"], "caption": f["caption"],
                   "nodes": used.get(fid, [])}
             for fid, f in figs.items() if f["kind"] != "formula" or fid in hidden}  # công thức rời: chỉ khi có ô dùng
    return related, shown
