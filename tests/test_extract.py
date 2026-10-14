"""Bộ trích qua VietPaper. Chỉ chạy được bằng Python của VietPaper (cần pymupdf):
    ../pdf-translator/.venv/bin/python -m unittest tests.test_extract
"""
import json
import tempfile
import unittest
from pathlib import Path

from paper_graph import blocks as blocks_mod
from paper_graph import extract as ex
from paper_graph.files import InputError

try:
    ex.load_vietpaper(ex.DEFAULT_VIETPAPER)
    import pymupdf
except (InputError, ImportError):  # không phải Python của VietPaper: bỏ qua cả file
    pymupdf = None


def make_pdf(path: Path, pages: int, text: str = "") -> None:
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page()
        if text:
            page.insert_textbox(pymupdf.Rect(72, 72, 540, 400), text, fontsize=11)
    doc.save(path)


@unittest.skipIf(pymupdf is None, "cần Python của VietPaper: ../pdf-translator/.venv/bin/python")
class Extract(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_page_cap_checked_before_any_page(self):  # TM-1
        pdf = self.dir / "many.pdf"
        make_pdf(pdf, 5)
        seen = []
        with self.assertRaises(InputError) as cm:
            ex.extract(pdf, max_pages=3, progress=lambda n, t: seen.append(n))
        self.assertIn("5 trang", str(cm.exception))
        self.assertEqual(seen, [])

    def test_size_cap(self):  # TM-1
        pdf = self.dir / "a.pdf"
        make_pdf(pdf, 1)
        old = ex.MAX_PDF_BYTES
        ex.MAX_PDF_BYTES = 10
        try:
            with self.assertRaises(InputError):
                ex.extract(pdf)
        finally:
            ex.MAX_PDF_BYTES = old

    def test_not_a_pdf(self):
        p = self.dir / "x.pdf"
        p.write_bytes(b"this is not a pdf at all")
        with self.assertRaises(InputError):
            ex.extract(p)

    def test_text_page_becomes_blocks_and_passes_parse(self):
        pdf = self.dir / "t.pdf"
        words = "Recurrent widgets process tokens one at a time, which precludes parallelization within a sequence."
        make_pdf(pdf, 2, words)
        doc = ex.extract(pdf)
        b, errs = blocks_mod.parse(doc)
        self.assertEqual(errs, [])
        self.assertEqual(b.page_count, 2)
        self.assertTrue(b.find("whichprecludesparallelization", 1))
        self.assertTrue(all(blk.id.startswith(f"p{blk.page}-b") for blk in b.blocks.values()))

    def test_verify_catches_tampered_blocks(self):  # TM-3
        pdf = self.dir / "t.pdf"
        make_pdf(pdf, 1, "Recurrent widgets process tokens one at a time, which precludes parallelization.")
        doc = json.loads(json.dumps(ex.extract(pdf)))
        self.assertEqual(ex.verify(pdf, doc), [])
        doc["blocks"][0]["text"] += " We also prove the widget is optimal."
        self.assertEqual(ex.verify(pdf, doc), [f"đoạn {doc['blocks'][0]['id']}: `text` khác bản trích lại"])

    def test_verify_reports_structure_and_every_kind_of_change(self):  # review 2: V3, V7
        pdf = self.dir / "t.pdf"
        make_pdf(pdf, 2, "Recurrent widgets process tokens one at a time, which precludes parallelization.")
        base = json.loads(json.dumps(ex.extract(pdf)))
        cases = {
            "pages": lambda d: d["pages"][0].update(width=1.0),
            "extra field": lambda d: d["blocks"][0].update(extra=1),
            "bbox": lambda d: d["blocks"][0].update(bbox=[0, 0, 1, 1]),
            "dropped block": lambda d: d["blocks"].pop(),
            "added block": lambda d: d["blocks"].append(dict(d["blocks"][0], id="p9-b1")),
            "sha": lambda d: d["source"].update(sha256="0" * 64),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                d = json.loads(json.dumps(base))
                fn(d)
                self.assertNotEqual(ex.verify(pdf, d), [], name)
        for broken in ([], {"version": 1, "blocks": 5}, dict(base, blocks=[dict(base["blocks"][0], id=["x"])])):
            out = ex.verify(pdf, broken)
            self.assertTrue(out and out[0].startswith("blocks.json không đúng dạng"), out)

    def test_pdf_without_pages_is_refused(self):  # review 2: V6
        pdf = self.dir / "empty.pdf"
        pdf.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
        with self.assertRaises(InputError):
            ex.extract(pdf)

    def test_blank_page_marked_without_text(self):
        pdf = self.dir / "blank.pdf"
        make_pdf(pdf, 1)
        doc = ex.extract(pdf)
        self.assertIs(doc["pages"][0]["text"], False)



def rotated_pdf(path: Path) -> None:
    """Một trang xoay 90° (trang ngang trong phụ lục): một đoạn văn, một "bảng" chữ trong khung, chú thích dưới bảng
    theo chiều của nội dung."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(pymupdf.Rect(72, 72, 540, 200), "Body paragraph of the rotated appendix page. " * 4,
                        fontsize=11)
    page.draw_rect(pymupdf.Rect(300, 500, 520, 700))
    page.insert_text((320, 560), "TABLE CELL 42.7", fontsize=12)
    page.insert_text((300, 716), "Table 9: rotated table caption.", fontsize=10)
    page.set_rotation(90)
    doc.save(path)


@unittest.skipIf(pymupdf is None, "cần Python của VietPaper: ../pdf-translator/.venv/bin/python")
class RotatedPages(unittest.TestCase):
    """Trang có /Rotate: mọi bbox của blocks.json theo toạ độ nội dung (trang chưa xoay), cùng hệ với get_text."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pdf = Path(self._tmp.name) / "rot.pdf"
        rotated_pdf(self.pdf)

    def tearDown(self):
        self._tmp.cleanup()

    def test_figure_text_and_caption_on_a_rotated_page(self):
        page = pymupdf.open(self.pdf)[0]
        cap = {"id": "p1-b2", "label": "figure_title", "bbox": [300, 705, 520, 720], "text": "Table 9: …"}
        # vùng bố cục như extract đưa vào sau khi đổi từ toạ độ hiển thị về toạ độ nội dung
        shown = pymupdf.Rect(300, 500, 520, 700) * page.rotation_matrix
        region = {"label": "table", "bbox": ex._content(page, shown)}
        self.assertEqual(region["bbox"], [300.0, 500.0, 520.0, 700.0])
        fig = ex.figures(1, [region], [cap], page)[0]
        self.assertEqual(fig.get("text"), "TABLE CELL 42.7")  # trước khi sửa: không có chữ (cắt nhầm vùng)
        self.assertEqual(fig.get("caption"), "p1-b2")

    def test_extract_reports_content_coordinates_and_rotation(self):
        doc = ex.extract(self.pdf)
        info = doc["pages"][0]
        self.assertEqual((info["width"], info["height"], info.get("rotation")), (612.0, 792.0, 90))
        page = pymupdf.open(self.pdf)[0]
        words = page.get_text("words")  # toạ độ nội dung
        body = next(b for b in doc["blocks"] if b["text"].startswith("Body paragraph"))
        x0, y0, x1, y1 = body["bbox"]
        self.assertTrue(any(x0 - 1 <= w[0] and w[2] <= x1 + 1 and y0 - 1 <= w[1] and w[3] <= y1 + 1
                            for w in words if w[4] == "Body"))
        self.assertLessEqual(x1, 612 + 1)  # theo khổ nội dung 612×792, không phải khổ hiển thị 792×612
        bl, errs = blocks_mod.parse(doc)
        self.assertEqual(errs, [])

    def landscape_pdf(self) -> Path:
        """Trang ngang như thật: chữ vẽ xoay sẵn trong nội dung rồi /Rotate, nên khi hiển thị chữ nằm ngang."""
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        for k in range(4):  # đủ chữ để VietPaper coi là trang có lớp chữ (≥ 50 ký tự), không phải trang scan
            page.insert_text((200 + 30 * k, 700), f"Wide appendix table row {k} with values 12.5 and 13.7",
                             fontsize=11, rotate=90)
        page.set_rotation(90)
        pdf = self.pdf.with_name("landscape.pdf")
        doc.save(pdf)
        return pdf

    def test_landscape_page_without_blocks_is_flagged_and_read_says_so(self):
        # VietPaper bỏ dòng không nằm ngang: trang ngang thật ra 0 đoạn. Hành vi hiện tại, đánh dấu để không im lặng.
        from paper_graph import reader
        doc = ex.extract(self.landscape_pdf())
        info = doc["pages"][0]
        self.assertEqual(doc["blocks"], [])
        self.assertTrue(info["text"])
        self.assertTrue(info.get("unread"))
        bl, _ = blocks_mod.parse(doc)
        self.assertIn("KHÔNG TRÍCH ĐƯỢC ĐOẠN NÀO", reader.render(bl, "x", "t", [1]))

    def test_landscape_page_falls_back_to_ocr_when_asked(self):
        # OCR thật nặng: thay hai hàm OCR của VietPaper, chỉ kiểm đường đi và đổi toạ độ hiển thị → nội dung
        from unittest import mock
        app = ex.load_vietpaper(ex.DEFAULT_VIETPAPER)
        shown = (100.0, 300.0, 400.0, 320.0)  # dòng OCR trên ảnh hiển thị (trang đã xoay)
        fake = [{"bbox": shown, "label": "text", "text": "Wide appendix table row"}]
        with mock.patch.object(app, "rapid_lines", return_value=[]), \
                mock.patch.object(app, "lines_to_blocks", return_value=fake) as l2b:
            doc = ex.extract(self.landscape_pdf(), ocr=True)
        self.assertTrue(l2b.called)
        info = doc["pages"][0]
        self.assertTrue(info.get("ocr"))
        self.assertNotIn("unread", info)
        page = pymupdf.open(self.landscape_pdf())[0]
        want = pymupdf.Rect(shown) * page.derotation_matrix
        self.assertEqual(doc["blocks"][0]["bbox"], [round(v, 2) for v in (want.x0, want.y0, want.x1, want.y1)])


if __name__ == "__main__":
    unittest.main()
