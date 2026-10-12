"""Chốt chặn trong .agent/threat-model.md: TM-1 (file to), TM-2 (ký tự điều khiển terminal), TM-4 (đường dẫn)."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from paper_graph import cli, files
from paper_graph.check import check, parse_graph, render
from paper_graph.files import InputError
from paper_graph.text import safe, squash

from .helpers import blocks, graph, node


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Workdir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "toy.blocks.json").write_text(json.dumps(blocks()))

    def tearDown(self):
        self._tmp.cleanup()

    def write_graph(self, g, name="toy.graph.json"):
        p = self.dir / name
        p.write_text(json.dumps(g, ensure_ascii=False))
        return p


class TerminalInjection(unittest.TestCase):  # TM-2
    def test_safe_escapes_control_and_bidi(self):
        self.assertEqual(safe("ok\x1b[2Kfake ✓\r‮evil\x9b"), "ok\\x1b[2Kfake ✓\\x0d\\u202eevil\\x9b")

    def test_safe_truncates(self):
        self.assertEqual(len(safe("x" * 500, 50)), 50)

    def test_rendered_report_has_no_raw_control_chars(self):
        g = graph()
        g["paper"]["title"] = "T\x1b]0;pwned\x07"
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "\x1b[1A\x1b[2K✓ all good ‮ and more words"}]
        b, _ = __import__("paper_graph.blocks", fromlist=["parse"]).parse(blocks())
        parsed, diags = parse_graph(g)
        text = render(check(parsed, b, None, diags), parsed.title)
        self.assertNotRegex(text, "[\x00-\x09\x0b-\x1f\x7f-\x9f‪-‮⁦-⁩]")
        self.assertIn("\\x1b", text)


class DiagSanitizing(unittest.TestCase):  # TM-2: lớp làm sạch ở _Diags, độc lập với từng thông điệp
    def test_diags_escape_on_creation(self):
        from paper_graph.check import _Diags

        d = _Diags()
        d.err("PG999", "w\x1b[2K", "m\u202e", "h\x9b")
        d.warn("PG998", "w", "\x07m", "")
        dumped = json.dumps([vars(x) for x in d], ensure_ascii=False)
        self.assertNotRegex(dumped, "[\x00-\x1f\x7f-\x9f\u202a-\u202e]")


class PathEscape(Workdir):  # TM-4
    def test_rejects_parent_absolute_and_wrong_suffix(self):
        base = self.dir / "toy.graph.json"
        for bad in ["../toy.blocks.json", "/etc/passwd", "sub/../../x.blocks.json", "toy.json", "", None, 3]:
            with self.assertRaises(InputError, msg=repr(bad)):
                files.sibling(base, bad, ".blocks.json")

    def test_rejects_symlink_out_of_directory(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        target = Path(outside.name) / "secret.blocks.json"
        target.write_text("{}")
        os.symlink(target, self.dir / "link.blocks.json")
        with self.assertRaises(InputError):
            files.sibling(self.dir / "toy.graph.json", "link.blocks.json", ".blocks.json")

    def test_symlink_loop_is_an_input_error(self):
        os.symlink(self.dir / "loop2.blocks.json", self.dir / "loop1.blocks.json")
        os.symlink(self.dir / "loop1.blocks.json", self.dir / "loop2.blocks.json")
        with self.assertRaises(InputError):
            files.sibling(self.dir / "toy.graph.json", "loop1.blocks.json", ".blocks.json")

    def test_accepts_plain_sibling(self):
        p = files.sibling(self.dir / "toy.graph.json", "toy.blocks.json", ".blocks.json")
        self.assertEqual(p, (self.dir / "toy.blocks.json").resolve())

    def test_cli_refuses_graph_pointing_outside(self):
        g = graph()
        g["paper"]["blocks"] = "../../etc/hosts.blocks.json"
        code, out, err = run_cli("check", str(self.write_graph(g)))
        self.assertEqual(code, 2)
        self.assertIn("tương đối", err)


class Limits(Workdir):  # TM-1
    def test_json_over_limit(self):
        p = self.dir / "big.json"
        p.write_text("[" + "0," * 1000 + "0]")
        with self.assertRaises(InputError):
            files.read_json(p, "x", limit=100)

    def test_deep_nesting(self):
        p = self.dir / "deep.json"
        p.write_text("[" * 100000 + "]" * 100000)
        with self.assertRaises(InputError):
            files.read_json(p, "x")

    def test_not_json_or_not_utf8(self):
        p = self.dir / "bad.json"
        p.write_bytes(b"\xff\xfe{")
        with self.assertRaises(InputError):
            files.read_json(p, "x")
        p.write_text("{nope")
        with self.assertRaises(InputError):
            files.read_json(p, "x")


class BrokenInputs(Workdir):  # review: traceback thay vì mã 2
    def test_huge_integer(self):
        p = self.dir / "big.graph.json"
        p.write_text('{"version": ' + "9" * 5000 + "}")
        code, _, err = run_cli("check", str(p))
        self.assertEqual(code, 2)
        self.assertIn("không đọc được", err)

    def test_nul_in_blocks_name(self):
        g = graph()
        g["paper"]["blocks"] = "toy\x00.blocks.json"
        code, _, err = run_cli("check", str(self.write_graph(g)))
        self.assertEqual(code, 2)
        self.assertIn("NUL", err)

    def test_extract_checks_output_dir_before_extracting(self):  # review 2: V6
        code, _, err = run_cli("extract", str(self.dir / "any.pdf"), "-o", str(self.dir / "nodir" / "x.blocks.json"))
        self.assertEqual(code, 2)
        self.assertIn("không ghi được", err)
        (self.dir / "d.blocks.json").mkdir()
        self.assertEqual(run_cli("extract", str(self.dir / "any.pdf"), "-o", str(self.dir / "d.blocks.json"))[0], 2)

    def test_missing_pdf(self):
        code, _, err = run_cli("check", "--pdf", str(self.dir / "none.pdf"), str(self.write_graph(graph())))
        self.assertEqual(code, 2)
        self.assertIn("none.pdf", err)

    def test_blocks_with_wrong_types_or_bad_ids(self):
        for mutate in (lambda b: b["blocks"][0].update(page=[1]),
                       lambda b: b["figures"][0].update(kind=["chart"]),
                       lambda b: b["blocks"][0].update(id="p1-b1\u202e")):
            b = blocks()
            mutate(b)
            (self.dir / "toy.blocks.json").write_text(json.dumps(b))
            code, _, err = run_cli("check", str(self.write_graph(graph())))
            self.assertEqual(code, 2, err)
            self.assertIn("hỏng", err)

    def test_json_output_has_no_raw_control_chars(self):  # TM-2 cho --json
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "evil \u202e quote \x1b[2K with \x9b more words"}]
        code, out, _ = run_cli("check", "--json", str(self.write_graph(g)))
        self.assertEqual(code, 1)
        self.assertNotRegex(out, "[\x00-\x09\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")
        self.assertIn("\\u202e", out)


class Cli(Workdir):
    def test_ok_and_exit_codes(self):
        code, out, _ = run_cli("check", str(self.write_graph(graph())))
        self.assertEqual(code, 0, out)
        self.assertIn("5/5 có thật", out)

    def test_error_exit_and_json(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "a sentence that is not in the paper"}]
        code, out, _ = run_cli("check", "--json", str(self.write_graph(g)))
        self.assertEqual(code, 1)
        res = json.loads(out)
        self.assertEqual((res["ok"], res["errors"]), (False, 1))
        self.assertEqual(res["diagnostics"][0]["code"], "PG201")

    def test_strict_fails_on_warning(self):
        g = graph()
        node(g, "idea").update(anchors=[], basis="inference")
        p = self.write_graph(g)
        self.assertEqual(run_cli("check", str(p))[0], 0)
        self.assertEqual(run_cli("check", "--strict", str(p))[0], 1)

    def test_pdf_flag_hashes_file(self):
        pdf = self.dir / "toy.pdf"
        pdf.write_bytes(b"%PDF-1.4 not the same paper")
        self.assertEqual(run_cli("check", "--pdf", str(pdf), str(self.write_graph(graph())))[0], 1)

    def test_missing_graph_file(self):
        code, _, err = run_cli("check", str(self.dir / "none.graph.json"))
        self.assertEqual(code, 2)
        self.assertIn("không đọc được", err)

    def test_broken_blocks_file(self):
        (self.dir / "toy.blocks.json").write_text(json.dumps({"version": 1}))
        code, _, err = run_cli("check", str(self.write_graph(graph())))
        self.assertEqual(code, 2)
        self.assertIn("hỏng", err)


class Squash(unittest.TestCase):
    def test_squash_equivalences(self):
        self.assertEqual(squash("ﬁne-tuning"), squash("fine tuning"))
        self.assertEqual(squash("trans-\nlation"), squash("translation"))
        self.assertEqual(squash("café"), squash("café"))
        self.assertEqual(squash("Self-Attention!"), "selfattention")


if __name__ == "__main__":
    unittest.main()
