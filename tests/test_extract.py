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


if __name__ == "__main__":
    unittest.main()
