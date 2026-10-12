"""`*.blocks.json`: các đoạn của một bài báo, kèm trang và toạ độ. Đây là hợp đồng giữa bộ trích và phần còn lại.

Lõi không đọc PDF. Nó chỉ cần danh sách đoạn (id, trang, khung, nhãn bố cục, chữ), nên đổi bộ trích (VietPaper,
docling, OCR khác) không đụng tới bộ kiểm hay trình xem. Cùng nguyên tắc với archctl: bộ quét không biết gì về
luật.

Dạng file (xem docs/format.md):
    {"version": 1,
     "source": {"file": "x.pdf", "sha256": "…", "pages": 15, "extractor": "vietpaper …"},
     "pages":   [{"page": 1, "width": 612.0, "height": 792.0, "text": true}],
     "blocks":  [{"id": "p1-b1", "page": 1, "bbox": [x0, y0, x1, y1], "label": "doc_title", "text": "…"}],
     "figures": [{"id": "p3-f1", "page": 3, "bbox": […], "kind": "image", "caption": "p3-b9"}]}
"""
from dataclasses import dataclass, field

from .model import ID
from .text import squash_index

VERSION = 1
FIGURE_KINDS = {"image", "chart", "table", "formula"}


@dataclass
class Block:
    id: str
    page: int
    bbox: tuple
    label: str
    text: str


@dataclass
class Hit:
    page: int
    blocks: list[str]  # đoạn chứa câu trích; hai đoạn khi câu trích vắt qua chỗ ngắt đoạn, cột hay trang
    snippet: str  # đoạn gốc tương ứng, để in ra


@dataclass
class Blocks:
    sha256: str
    pages: dict[int, dict]
    blocks: dict[str, Block]
    figures: dict[str, dict]
    _page_text: dict[int, tuple] = field(default_factory=dict, repr=False)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def _index(self, page: int):
        """Chữ đã chuẩn hoá của cả trang (các đoạn nối theo thứ tự đọc), vị trí đoạn trong đó, và chuỗi gốc."""
        if page not in self._page_text:
            raw, squashed, where, spans, brk = "", "", [], [], []
            for b in (b for b in self.blocks.values() if b.page == page):
                s, w, k = squash_index(b.text)
                spans.append((len(squashed), len(squashed) + len(s), b.id))
                where += [len(raw) + i for i in w]
                brk += [True] + k[1:] if k else []  # đầu mỗi đoạn luôn là ranh giới
                squashed += s
                raw += b.text + "\n"
            self._page_text[page] = (squashed, where, spans, raw, brk)
        return self._page_text[page]

    def find_all(self, quote_squashed: str, page: int, limit: int = 20) -> list[Hit]:
        """Mọi chỗ câu trích xuất hiện trên trang (tối đa `limit`): cùng một câu có thể có ở cả thân bài lẫn chú
        thích hình, và neo ghi `block` là chỗ thứ hai thì vẫn đúng."""
        squashed, where, spans, raw, brk = self._index(page)
        hits: list[Hit] = []
        at = squashed.find(quote_squashed) if quote_squashed else -1
        while at >= 0 and len(hits) < limit:
            end = at + len(quote_squashed)
            # chỉ nhận khi hai đầu câu trích rơi đúng ranh giới từ hay số của bài: "score of 2" không khớp
            # "score of 28.4", "possible to train" không khớp "impossible to train"
            if brk[at] and (end == len(squashed) or brk[end]):
                ids = [bid for a, z, bid in spans if a < end and z > at]
                hits.append(Hit(page, ids, raw[where[at]: where[end - 1] + 1]))
            at = squashed.find(quote_squashed, at + 1)
        return hits

    def find(self, quote_squashed: str, page: int) -> Hit | None:
        hits = self.find_all(quote_squashed, page, limit=1)
        return hits[0] if hits else None

    def find_anywhere(self, quote_squashed: str) -> list[Hit]:
        return [h for p in sorted(self.pages) if (h := self.find(quote_squashed, p))]

    def closest(self, quote_squashed: str, page: int) -> tuple[float, str]:
        """Đoạn liền dài nhất của câu trích có trên trang (tỉ lệ theo độ dài câu trích) và chữ gốc của nó. Dùng
        để gợi ý khi câu trích sai một hai chữ."""
        from difflib import SequenceMatcher

        squashed, where, _, raw, _ = self._index(page)
        if not quote_squashed or not squashed:
            return 0.0, ""
        m = SequenceMatcher(None, squashed, quote_squashed, autojunk=False).find_longest_match(
            0, len(squashed), 0, len(quote_squashed))
        if m.size == 0:
            return 0.0, ""
        return m.size / len(quote_squashed), raw[where[m.a]: where[m.a + m.size - 1] + 1]


def parse(doc) -> tuple[Blocks | None, list[str]]:
    """Kiểm dạng file blocks. Trả (Blocks, []) hoặc (None, các lỗi). File này do bộ trích sinh nên lỗi ở đây là
    lỗi của bộ trích hay file bị sửa tay, không phải của sơ đồ."""
    errs: list[str] = []
    if not isinstance(doc, dict):
        return None, ["blocks: gốc phải là object"]
    if doc.get("version") != VERSION:
        errs.append(f"blocks: version phải là {VERSION}")
    src = doc.get("source")
    sha = src.get("sha256") if isinstance(src, dict) else None
    if not (isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)):
        errs.append("blocks: thiếu source.sha256 (64 ký tự hex)")
    pages: dict[int, dict] = {}
    for i, p in enumerate(doc.get("pages") if isinstance(doc.get("pages"), list) else []):
        n = p.get("page") if isinstance(p, dict) else None
        if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n in pages:
            errs.append(f"blocks: pages[{i}] thiếu số trang hợp lệ hoặc trùng")
            continue
        pages[n] = p
    if not pages:
        errs.append("blocks: không có trang nào")
    blocks: dict[str, Block] = {}
    for i, b in enumerate(doc.get("blocks") if isinstance(doc.get("blocks"), list) else []):
        ok = (isinstance(b, dict) and _id(b.get("id")) and b["id"] not in blocks
              and _page(b.get("page"), pages) and isinstance(b.get("text"), str) and _bbox(b.get("bbox")))
        if not ok:
            errs.append(f"blocks: blocks[{i}] thiếu id/page/bbox/text hợp lệ, hoặc trùng id, hoặc trang không có")
            continue
        blocks[b["id"]] = Block(b["id"], b["page"], tuple(b["bbox"]), str(b.get("label") or "text"), b["text"])
    figures: dict[str, dict] = {}
    for i, f in enumerate(doc.get("figures") if isinstance(doc.get("figures"), list) else []):
        ok = (isinstance(f, dict) and _id(f.get("id")) and f["id"] not in figures and f["id"] not in blocks
              and _page(f.get("page"), pages) and isinstance(f.get("kind"), str) and f["kind"] in FIGURE_KINDS
              and _bbox(f.get("bbox")) and (f.get("caption") is None or _id(f["caption"])))
        if not ok:
            errs.append(f"blocks: figures[{i}] thiếu id/page/bbox/kind hợp lệ, hoặc trùng id")
            continue
        figures[f["id"]] = f
    if errs:
        return None, errs
    return Blocks(sha, pages, blocks, figures), []


def _id(v) -> bool:
    """id đoạn và hình đi vào chẩn đoán, JSON và DOM như id của sơ đồ (TM-5), nên cùng một luật."""
    return isinstance(v, str) and bool(ID.fullmatch(v))


def _page(v, pages: dict) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v in pages


def _bbox(v) -> bool:
    return (isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                                      for x in v) and v[0] <= v[2] and v[1] <= v[3])
