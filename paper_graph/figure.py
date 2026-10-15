"""`paper-graph figure`: cắt vùng của một hình, bảng (`pX-fY`) hay đoạn (`pX-bY`) ra ảnh PNG để agent nhìn.

Chữ trích từ biểu đồ chỉ có vạch trục; muốn tả hình dạng đường cong hay đối chiếu cột của bảng có ô gộp thì phải nhìn
ảnh. Chạy bằng Python của VietPaper (cần PyMuPDF). Chốt chặn TM-9..TM-12 ở `.agent/threat-model.md`:
- `id` phải có thật trong blocks; tên ảnh chỉ dựng từ `id` đó; PDF lấy cạnh blocks qua `files.sibling`; thư mục ảnh
  cố định `<tên>.figures/` cạnh blocks, không được là symlink hay trỏ ra ngoài (TM-9);
- PDF có trần kích thước như `extract`, vùng cắt theo khung trang, cạnh dài nhất ≤ MAX_SIDE px, tối đa MAX_IDS id
  mỗi lần (TM-10);
- SHA-256 của PDF phải khớp blocks, để không cắt hình của một bài khác (TM-11);
- ảnh là nội dung bài: người gọi in kèm lời nhắc chữ trong ảnh là dữ liệu (TM-12, `cli.cmd_figure`).
"""
import hashlib
from pathlib import Path

from . import blocks as blocks_mod
from .extract import MAX_PDF_BYTES
from .files import InputError, read_json, read_regular, sibling, write_atomic
from .model import ID

MAX_SIDE = 4000  # px, cạnh dài nhất của ảnh
MAX_IDS = 20
DEFAULT_DPI = 200
PAD = 4.0  # pt quanh vùng cắt, để không mất nét viền và chữ sát mép


def out_dir(blocks_path: Path) -> Path:
    name = blocks_path.name
    stem = name[: -len(".blocks.json")] if name.endswith(".blocks.json") else blocks_path.stem
    return blocks_path.parent / f"{stem}.figures"


def _region(bl: blocks_mod.Blocks, fid: str) -> tuple[int, tuple]:
    if not (isinstance(fid, str) and ID.fullmatch(fid)):
        raise InputError(f"id {fid!r} không hợp lệ: chỉ chữ, số và . _ : -")
    if fid in bl.figures:
        f = bl.figures[fid]
        return f["page"], tuple(f["bbox"])
    if fid in bl.blocks:
        b = bl.blocks[fid]
        return b.page, tuple(b.bbox)
    raise InputError(f"không có hình hay đoạn {fid} trong blocks.json (xem id ở `read`)")


def _safe_dir(blocks_path: Path) -> Path:
    root = blocks_path.resolve().parent
    d = out_dir(blocks_path)
    if d.is_symlink():
        raise InputError(f"{d} là symlink: không ghi ảnh qua symlink")
    d.mkdir(exist_ok=True)
    real = d.resolve()
    if not real.is_dir() or not real.is_relative_to(root) or real == root:
        raise InputError(f"{d} không nằm trong thư mục của blocks.json")
    return real


def render(blocks_path: Path, ids: list[str], pdf: Path | None = None, dpi: int = DEFAULT_DPI) -> list[dict]:
    """Cắt từng vùng ra `<tên>.figures/<id>.png`. Trả [{id, path, page, width, height}]."""
    if not ids:
        raise InputError("cần ít nhất một id")
    if len(ids) > MAX_IDS:
        raise InputError(f"{len(ids)} id, quá trần {MAX_IDS} mỗi lần")
    if not 36 <= dpi <= 600:
        raise InputError("--dpi phải trong khoảng 36–600")
    doc = read_json(blocks_path, "blocks")
    bl, errs = blocks_mod.parse(doc)
    if errs:
        raise InputError(f"{blocks_path} hỏng:\n" + "\n".join(errs[:20]))
    regions = [(fid, *_region(bl, fid)) for fid in dict.fromkeys(ids)]
    folded: dict[str, str] = {}
    for fid, *_ in regions:  # ổ đĩa không phân biệt hoa thường (APFS mặc định): p1-f1.png và P1-F1.png là một file
        if folded.setdefault(fid.casefold(), fid) != fid:
            raise InputError(f"{folded[fid.casefold()]} và {fid} chỉ khác hoa thường, sẽ ghi chung một file ảnh")
    if pdf is None:
        src = doc.get("source") if isinstance(doc.get("source"), dict) else {}
        pdf = sibling(blocks_path, src.get("file"), ".pdf")
    data = read_regular(pdf, "PDF", MAX_PDF_BYTES)
    if hashlib.sha256(data).hexdigest() != bl.sha256:
        raise InputError(f"{pdf} không phải bản đã trích ra {blocks_path.name} (sha256 khác): cắt ảnh sẽ ra hình của "
                         "bài khác")
    dest = _safe_dir(blocks_path)

    import pymupdf  # noqa: PLC0415 - có sẵn trong venv của VietPaper

    try:
        pdoc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:  # noqa: BLE001 - PyMuPDF ném nhiều loại lỗi cho PDF hỏng
        raise InputError(f"không mở được {pdf} như PDF: {e}") from None
    if pdoc.needs_pass:
        pdoc.close()
        raise InputError(f"{pdf} cần mật khẩu")
    out = []
    with pdoc:
        for fid, page_no, bbox in regions:
            if not 1 <= page_no <= pdoc.page_count:
                raise InputError(f"{fid}: trang {page_no} không có trong PDF")
            if pdoc[page_no - 1].rotation != bl.pages[page_no].get("rotation", 0):
                raise InputError(f"{fid}: trang {page_no} xoay {pdoc[page_no - 1].rotation}° mà blocks.json không ghi: "
                                 "blocks trích bằng bản cũ (toạ độ khác), chạy lại extract")
            try:
                page = pdoc[page_no - 1]
                x0, y0, x1, y1 = bbox
                rect = pymupdf.Rect(x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD)
                if page.rotation:  # blocks.json theo toạ độ nội dung (trang chưa xoay); ảnh render theo trang đã xoay
                    rect = rect * page.rotation_matrix
                rect = rect & page.rect  # cắt theo khung trang
                if rect.is_empty or rect.width < 1 or rect.height < 1:
                    raise InputError(f"{fid}: vùng {bbox} nằm ngoài trang {page_no}")
                zoom = min(dpi / 72, MAX_SIDE / max(rect.width, rect.height))
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False)
            except (ValueError, RuntimeError) as e:  # trang hỏng, tài liệu bị khoá giữa chừng
                raise InputError(f"{fid}: không render được trang {page_no}: {e}") from None
            path = dest / f"{fid}.png"
            write_atomic(path, pix.tobytes("png"))
            out.append({"id": fid, "path": path, "page": page_no, "width": pix.width, "height": pix.height})
    return out
