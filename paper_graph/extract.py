"""Bộ trích: PDF → `*.blocks.json`, dùng chính bộ gom đoạn của VietPaper (../pdf-translator).

VietPaper đã có bộ gom đoạn theo PP-DocLayoutV3, có bench, có OCR cho bản scan; viết lại là tự làm hỏng thứ đang
chạy tốt. Đổi lại, lệnh này phải chạy bằng Python của VietPaper (cần pymupdf, onnxruntime, rapidocr):

    ../pdf-translator/.venv/bin/python -m paper_graph extract bai.pdf

Phần còn lại của paper-graph chỉ dùng thư viện chuẩn và không biết bộ trích là gì.

Chốt chặn TM-1: trần kích thước file và số trang được kiểm trước khi xử lý trang nào.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from .blocks import VERSION
from .files import InputError, read_regular

MAX_PDF_BYTES = 150 * 1024 * 1024
MAX_PAGES = 400
DEFAULT_VIETPAPER = Path(__file__).resolve().parents[2] / "pdf-translator"
FIGURE_LABELS = {"image": "image", "chart": "chart", "table": "table", "display_formula": "formula"}
FIGURE_TEXT_MAX = 4000  # ký tự chữ giữ lại của mỗi vùng hình/bảng
CAPTION_GAP = 60.0  # pt: chú thích cách hình xa hơn thế thì không coi là chú thích của nó
_TAG = re.compile(r"</?[bi]>")


def load_vietpaper(path: Path):
    path = Path(path).resolve()
    if not (path / "app.py").is_file():
        raise InputError(f"không thấy VietPaper ở {path} (cần {path / 'app.py'}); chỉ đường bằng --vietpaper")
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    try:
        import app  # noqa: PLC0415 - nạp muộn: chỉ lệnh extract cần VietPaper
    except ImportError as e:
        raise InputError(f"không nạp được VietPaper ({e}). Chạy bằng Python của VietPaper: "
                         f"{path / '.venv/bin/python'} -m paper_graph extract …") from None
    if Path(app.__file__).resolve().parent != path:
        raise InputError(f"đã nạp nhầm module `app` ở {app.__file__}, không phải của VietPaper ở {path}")
    return app


def extract(pdf: Path, vietpaper: Path = DEFAULT_VIETPAPER, ocr: bool = False, lang: str = "eng",
            max_pages: int = MAX_PAGES, progress=None, app=None, given: dict | None = None) -> dict:
    """`app`, `given`: khi VietPaper gọi thẳng (đang chạy, đã nạp sẵn module của nó). `given` là khối VietPaper đã
    trích cho từng trang, {số trang đếm từ 0: (khối, có OCR không)}: dùng đúng các khối đó (cả khối OCR bằng VLM, thứ
    không trích lại được) để số thứ tự đoạn `p{n}-b{k}` khớp số hiệu đoạn k-1 của VietPaper, nên bản dịch và vị trí
    đoạn tra thẳng theo id. Gọi kiểu này thì không huỷ phiên model bố cục: server còn dùng."""
    data = read_regular(pdf, "PDF", MAX_PDF_BYTES)
    embedded = app is not None
    app = app if embedded else load_vietpaper(vietpaper)
    import pymupdf  # noqa: PLC0415 - có sẵn trong venv của VietPaper

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:  # PyMuPDF ném nhiều loại lỗi khi file hỏng
        raise InputError(f"{pdf} không mở được như PDF: {e}") from None
    if doc.needs_pass:
        raise InputError(f"{pdf} có mật khẩu")
    if doc.page_count == 0:
        raise InputError(f"{pdf} không có trang nào (file hỏng hay bị cắt cụt?)")
    if doc.page_count > max_pages:
        raise InputError(f"{pdf} có {doc.page_count} trang, quá trần {max_pages} (đổi bằng --max-pages)")

    app_src = Path(app.__file__).read_bytes()
    out = {
        "version": VERSION,
        "source": {"file": pdf.name, "sha256": hashlib.sha256(data).hexdigest(), "pages": doc.page_count,
                   "extractor": f"vietpaper app.py sha256:{hashlib.sha256(app_src).hexdigest()[:12]}",
                   "ocr": bool(ocr)},
        "pages": [], "blocks": [], "figures": [],
    }
    for i, page in enumerate(doc):
        n = i + 1
        if progress:
            progress(n, doc.page_count)
        regions = app.detect_layout(page)  # toạ độ hiển thị (dò trên ảnh render của trang đã xoay)
        content_regions = None if regions is None else [{**g, "bbox": tuple(_content(page, g["bbox"]))}
                                                        for g in regions]
        has_text = app.page_has_text(page) and not app.text_is_garbled(page)
        raw: list[dict] = []
        used_ocr = False
        if given is not None and i in given:
            raw, used_ocr = given[i]
            raw = list(raw or [])
            if used_ocr:  # khối OCR theo toạ độ hiển thị như dòng OCR ở dưới
                raw = [{**b, "bbox": _content(page, b["bbox"])} for b in raw]
            used_ocr = bool(used_ocr and raw)
        elif has_text:  # dòng chữ của get_text theo toạ độ nội dung: so với vùng đã đổi về cùng hệ
            raw = app.extract_blocks(page, regions=content_regions)
        # OCR khi trang không có lớp chữ, hay có mà bộ gom đoạn không lấy được đoạn nào: VietPaper bỏ dòng không nằm
        # ngang, nên trang ngang trong phụ lục (chữ vẽ xoay, rồi /Rotate) ra 0 đoạn; OCR đọc trên ảnh hiển thị, nơi
        # chữ đó nằm ngang. Dòng OCR theo toạ độ hiển thị: so với vùng gốc, rồi đổi khung đoạn.
        if not raw and ocr:
            raw = [{**b, "bbox": _content(page, b["bbox"])}
                   for b in app.lines_to_blocks(page, app.rapid_lines(page, lang), regions)]
            used_ocr = bool(raw)
        size = _content(page, page.rect)
        info = {"page": n, "width": round(size[2] - size[0], 2), "height": round(size[3] - size[1], 2),
                "text": bool(has_text or raw), "layout": regions is not None}
        if page.rotation:
            info["rotation"] = page.rotation  # vẽ lên ảnh của trang thì nhân bbox với page.rotation_matrix
        label = page.get_label()
        if label:
            info["label"] = label
        if used_ocr:
            info["ocr"] = True
        if has_text and not raw and not used_ocr:
            info["unread"] = True  # có lớp chữ mà không ra đoạn nào: `read` báo, đừng để trang rỗng mà im lặng
        out["pages"].append(info)

        blocks, chars = [], None
        for k, b in enumerate(raw, 1):
            if b.get("formulas") and chars is None:
                chars = char_map(app, page)
            text = plain_text(app, b, chars or {})
            if not text.strip():
                continue
            blocks.append({"id": f"p{n}-b{k}", "page": n, "bbox": _box(b["bbox"]),
                           "label": b.get("label") or "text", "text": text})
        out["blocks"] += blocks
        out["figures"] += figures(n, content_regions or [], blocks, page)
    if given is not None:  # verify-blocks không trích lại được khối OCR bằng VLM: ghi rõ nguồn
        out["source"]["extractor"] += " · khối đã trích của VietPaper"
        out["source"]["ocr"] = any(p.get("ocr") for p in out["pages"])
    if not embedded:
        release(app)
    return out


def release(app) -> None:
    """Huỷ phiên ONNX của model bố cục ngay khi xong việc. Để nó sống tới lúc Python tắt thì thỉnh thoảng
    onnxruntime chết ở bước dọn dẹp ("recursive_mutex lock failed", mã -6) dù kết quả đã ghi xong: gặp 1/5 lần
    chạy verify-blocks trên bert.pdf. VietPaper là server chạy mãi nên không gặp. Lần trích sau tự nạp lại (~1 giây)."""
    lock = getattr(app, "_layout_lock", None)
    cache = getattr(app, "_layout", None)
    if lock is not None and isinstance(cache, dict):
        with lock:
            cache.pop("sess", None)


def char_map(app, page) -> dict:
    """Ký tự của trang theo định danh VietPaper dùng cho công thức (toạ độ chân chữ), đọc với đúng cờ như
    `app.text_lines` để toạ độ khớp."""
    import pymupdf  # noqa: PLC0415

    out = {}
    for b in page.get_text("rawdict", flags=pymupdf.TEXT_MEDIABOX_CLIP)["blocks"]:
        for ln in b.get("lines", ()):
            for s in ln["spans"]:
                for c in s["chars"]:
                    out.setdefault(app.char_key(c), c["c"])
    return out


def verify(pdf: Path, stored: dict, vietpaper: Path = DEFAULT_VIETPAPER) -> list[str]:
    """Trích lại PDF rồi so với blocks.json đã có. `check --pdf` chỉ so mã băm ghi trong file, nên blocks.json bị
    sửa tay mà giữ nguyên `source.sha256` vẫn qua; lệnh này bắt được chuyện đó (TM-3). Trả các chỗ khác nhau."""
    from .blocks import parse  # noqa: PLC0415

    _, errs = parse(stored)
    if errs:  # sai dạng thì đã là "khác", khỏi trích lại
        return ["blocks.json không đúng dạng: " + e for e in errs[:20]]
    src = stored["source"]
    fresh = json.loads(json.dumps(extract(pdf, vietpaper, ocr=bool(src.get("ocr")))))
    diffs = []
    if src.get("sha256") != fresh["source"]["sha256"]:
        diffs.append("source.sha256 khác SHA-256 của PDF")
    if src.get("extractor") != fresh["source"]["extractor"]:
        diffs.append(f"blocks.json trích bằng {src.get('extractor')!r}, bản VietPaper hiện tại là "
                     f"{fresh['source']['extractor']!r}: khác nhau có thể chỉ vì VietPaper đã đổi")
    for key in ("pages", "figures"):
        if stored.get(key) != fresh[key]:
            diffs.append(f"`{key}` khác bản trích lại")
    old = {b["id"]: b for b in stored["blocks"]}
    new = {b["id"]: b for b in fresh["blocks"]}
    for bid in sorted(set(old) | set(new), key=str):
        if bid not in new:
            diffs.append(f"đoạn {bid} không có trong bản trích lại")
        elif bid not in old:
            diffs.append(f"đoạn {bid} thiếu trong blocks.json")
        elif old[bid] != new[bid]:
            fields = sorted(set(old[bid]) | set(new[bid]), key=str)
            changed = [k for k in fields if old[bid].get(k) != new[bid].get(k)]
            diffs.append(f"đoạn {bid}: {', '.join('`%s`' % k for k in changed)} khác bản trích lại")
    return diffs


def plain_text(app, b: dict, chars: dict) -> str:
    """Chữ của khối như in trên trang: bỏ thẻ <b>/<i>, công thức {vN} thay bằng đúng các ký tự của nó (vd. `dk` của
    d_k). Lấy ký tự theo danh sách VietPaper ghi cho từng công thức, không cắt theo khung: khung công thức có chỉ
    số chạm sang dòng trên dưới, cắt theo khung thì lẫn chữ của dòng bên cạnh."""
    text = _TAG.sub("", b["text"])
    formulas = b.get("formulas") or []

    def put(mt: re.Match) -> str:
        k = int(mt.group(1)) - 1
        if not 0 <= k < len(formulas):
            return mt.group(0)
        t = "".join(chars.get(tuple(key), "") for key in formulas[k].get("chars", ()))
        return re.sub(r"\s+", "", t) or mt.group(0)

    return app.PLACEHOLDER.sub(put, text)


def figures(n: int, regions: list[dict], blocks: list[dict], page=None) -> list[dict]:
    """Vùng hình, biểu đồ, bảng, công thức đứng riêng của trang, kèm chú thích gần nhất (khối `figure_title` chồng
    theo chiều ngang, cách không quá CAPTION_GAP) và chữ in trong vùng. Chữ trong vùng cần cho bảng: ô toàn số không
    vào blocks (bộ gom đoạn của VietPaper bỏ chúng vì không cần dịch), mà số liệu của bảng là thứ ô "bằng chứng" dẫn."""
    caps = [b for b in blocks if b["label"] == "figure_title"]
    out, taken = [], set()
    for g in regions:
        kind = FIGURE_LABELS.get(g["label"])
        if not kind:
            continue
        box = _box(g["bbox"])
        fig = {"id": f"p{n}-f{len(out) + 1}", "page": n, "bbox": box, "kind": kind}
        if page is not None:  # vùng đã theo toạ độ nội dung, cùng hệ với get_text
            text = " ".join(page.get_text("text", clip=box).split())[:FIGURE_TEXT_MAX]
            if text:
                fig["text"] = text
        if kind != "formula":
            best = None
            for c in caps:
                if c["id"] in taken:
                    continue
                cb = c["bbox"]
                overlap = min(box[2], cb[2]) - max(box[0], cb[0])
                if overlap < 0.3 * min(box[2] - box[0], cb[2] - cb[0]):
                    continue
                gap = max(cb[1] - box[3], box[1] - cb[3])  # chú thích ở dưới hay ở trên
                if gap <= CAPTION_GAP and (best is None or gap < best[0]):
                    best = (gap, c["id"])
            if best:
                fig["caption"] = best[1]
                taken.add(best[1])
        out.append(fig)
    return out


def _box(b) -> list[float]:
    return [round(float(v), 2) for v in b]


def _content(page, bbox) -> list[float]:
    """Toạ độ hiển thị (trang đã xoay: ảnh render, vùng bố cục, dòng OCR) → toạ độ nội dung (trang chưa xoay, như
    `get_text`). Mọi `bbox` trong blocks.json dùng toạ độ nội dung: chú thích "dưới" hình, công thức "sau" đoạn là
    quan hệ theo chiều đọc của nội dung, ở trang ngang (`/Rotate`) cũng vậy. Ai vẽ hay cắt ảnh từ trang thì nhân lại
    `rotation_matrix` (xem `figure.py`)."""
    if not page.rotation:
        return _box(bbox)
    import pymupdf  # noqa: PLC0415 - có sẵn trong venv của VietPaper

    r = pymupdf.Rect(bbox) * page.derotation_matrix
    return _box((r.x0, r.y0, r.x1, r.y1))
