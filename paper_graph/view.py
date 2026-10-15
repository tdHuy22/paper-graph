"""`paper-graph view`: xuất sơ đồ thành một file HTML tự chứa, chạy offline (Mốc 3, việc 4.1).

Bố cục tính sẵn bằng Python (`layout.py`); trang chỉ vẽ và xử lý bấm. Chốt chặn ở `.agent/threat-model.md`:
- TM-13: dữ liệu nhúng trong `<script type="application/json">`, thoát `<`, `>`, `&`, U+2028, U+2029 thành `\\uXXXX`
  nên chữ của sơ đồ không đóng được thẻ; JS đọc bằng `JSON.parse` và chỉ ghi chữ bằng `textContent`;
- TM-14: CSP trong `<meta>`: không nguồn nào ngoài (`default-src 'none'`), script và style chỉ chạy khi khớp hash
  SHA-256 của đúng khối nhúng, ảnh chỉ `data:`;
- TM-15: ảnh chỉ lấy từ `figure.render` (PNG do PyMuPDF cắt từ đúng PDF), không đọc ảnh có sẵn trên đĩa.
"""
import base64
import hashlib
import html
import json
import re
from pathlib import Path

from . import blocks as blocks_mod
from . import figlinks
from .check import check, parse_graph
from .files import InputError, read_json, sibling
from .layout import layout_graph
from .text import squash

ASSETS = Path(__file__).resolve().parent / "viewer"
CROP_DPI = 110  # ảnh đoạn gốc: đủ đọc, file không quá nặng
FIGURE_DPI = 150


def _json_for_html(doc) -> str:
    s = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return (s.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


def _anchor_block(a, bl: blocks_mod.Blocks | None) -> str | None:
    """Đoạn chứa câu trích: `block` của neo nếu có thật, không thì đoạn đầu tiên khớp câu trích trên trang đó."""
    if bl is None:
        return None
    if a.block and a.block in bl.blocks:
        return a.block
    if isinstance(a.page, int) and a.page in bl.pages:
        hit = bl.find(squash(a.quote), a.page)
        if hit and hit.blocks:
            return hit.blocks[0]
    return None


def _images(blocks_path: Path, ids: list[str], pdf: Path | None, dpi: int) -> tuple[dict[str, str], list[str]]:
    """Ảnh PNG theo id, và các id không cắt được. Lỗi của riêng một vùng (thông báo mở đầu bằng id: bbox ngoài trang,
    trang hỏng) chỉ bỏ vùng đó; lỗi chung (thiếu PDF, sai SHA-256) vẫn ném ra."""
    from .figure import MAX_IDS, render  # noqa: PLC0415 - cần PyMuPDF

    out: dict[str, str] = {}
    bad: list[str] = []
    for k in range(0, len(ids), MAX_IDS):
        batch = ids[k:k + MAX_IDS]
        try:
            shots = render(blocks_path, batch, pdf, dpi)
        except InputError as e:
            if not str(e).startswith(tuple(f"{i}: " for i in batch)):
                raise
            shots = []
            for i in batch:  # lô hỏng vì một vùng: cắt lại từng vùng
                try:
                    shots += render(blocks_path, [i], pdf, dpi)
                except InputError as e1:
                    if not str(e1).startswith(f"{i}: "):
                        raise
                    bad.append(i)
        for shot in shots:
            data = shot["path"].read_bytes()
            if data.startswith(b"\x89PNG\r\n\x1a\n"):  # TM-15
                out[shot["id"]] = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    return out, bad


def build(graph_path: Path, blocks_path: Path | None = None, pdf: Path | None = None,
          images: bool = True, crops: bool = True) -> tuple[str, dict]:
    """HTML của trình xem và vài số liệu (số ô, số ảnh, ghi chú). Sơ đồ phải qua `check` 0 lỗi."""
    graph, diags = parse_graph(read_json(graph_path, "sơ đồ"))
    if graph is None:
        raise InputError(f"{graph_path} không đọc được như một sơ đồ: chạy check trước")
    if blocks_path is None:
        blocks_path = sibling(graph_path, graph.blocks_file or "", ".blocks.json")
    bl, errs = blocks_mod.parse(read_json(blocks_path, "blocks"))
    if errs:
        raise InputError(f"{blocks_path} hỏng:\n" + "\n".join(errs[:20]))
    rep = check(graph, bl, None, diags)
    if rep.errors:
        raise InputError(f"sơ đồ còn {rep.errors} lỗi theo `check`: sửa trước khi xuất trình xem")

    tiers = layout_graph(graph)
    children: dict[str, int] = {}
    for n in graph.nodes.values():
        if n.parent:
            children[n.parent] = children.get(n.parent, 0) + 1
    nodes = {}
    crop_ids: list[str] = []
    anchor_blocks: dict[str, list[str | None]] = {}
    for n in graph.nodes.values():
        anchors = []
        for a in n.anchors:
            blk = _anchor_block(a, bl)
            anchors.append({"page": a.page, "quote": a.quote, "block": blk})
            if blk and blk not in crop_ids:
                crop_ids.append(blk)
        anchor_blocks[n.id] = [a["block"] for a in anchors]
        nodes[n.id] = {"kind": n.kind, "label": n.label, "term": n.term, "explain": n.explain, "basis": n.basis,
                       "status": n.status, "parent": n.parent or "", "figure": n.figure,
                       "children": children.get(n.id, 0), "anchors": anchors}
    related, figures = figlinks.link(graph, bl, anchor_blocks)
    for nid, figs in related.items():
        nodes[nid]["figures"] = figs
    figure_ids = list(figures)

    pictures: dict[str, str] = {}
    note = ""
    if images:
        try:
            bad: list[str] = []
            for ids, dpi in ((figure_ids, FIGURE_DPI), (crop_ids if crops else [], CROP_DPI)):
                if ids:
                    got, miss = _images(blocks_path, ids, pdf, dpi)
                    pictures.update(got)
                    bad += miss
            if bad:
                note = (f"{len(bad)} hình hay đoạn không cắt được ảnh (vùng hỏng trong blocks.json): "
                        + ", ".join(bad[:10]) + (" …" if len(bad) > 10 else ""))
        except ImportError:
            note = "Không có ảnh: cần chạy bằng Python của VietPaper (PyMuPDF) để cắt hình và đoạn gốc từ PDF."
        except InputError as e:
            note = f"Không có ảnh: {e}"
    data = {"title": graph.title, "sha256": graph.sha256, "tiers": tiers, "nodes": nodes,
            "edges": [{"from": e.src, "to": e.dst, "kind": e.kind, "strength": e.strength, "label": e.label}
                      for e in graph.edges],
            "figures": figures, "images": pictures,
            "note": note or (f"Sơ đồ đã qua kiểm tra: {rep.stats.get('anchors_ok', 0)} câu trích có thật trong bài. "
                             "Câu trích chứng minh câu đó có trong bài, không chứng minh ô diễn giải đúng.")}

    style = (ASSETS / "viewer.css").read_text("utf-8")
    script = (ASSETS / "viewer.js").read_text("utf-8")
    csp = (f"default-src 'none'; script-src {_sha(script)}; style-src {_sha(style)}; img-src data:; "
           "base-uri 'none'; form-action 'none'")
    template = (ASSETS / "template.html").read_text("utf-8")
    values = {"CSP": csp, "TITLE": html.escape(graph.title or "Sơ đồ bài báo", quote=True), "STYLE": style,
              "DATA": _json_for_html(data), "SCRIPT": script}
    # thay một lượt trên template: chữ của sơ đồ có "{{SCRIPT}}" cũng không bị thay lần nữa
    page = re.sub(r"\{\{([A-Z]+)\}\}", lambda mt: values[mt.group(1)], template)
    stats = {"nodes": len(nodes), "tiers": len(tiers), "figures": len(figures), "images": len(pictures), "note": note,
             "bytes": len(page.encode())}
    return page, stats
