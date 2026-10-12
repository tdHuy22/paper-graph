"""Trích các bài của bộ đo ra bench/papers/<tên>/<tên>.blocks.json (không đưa vào git).

Chạy bằng Python của VietPaper, từ gốc repo:
    ../pdf-translator/.venv/bin/python bench/prepare.py [tên…]
Bỏ qua bài đã có blocks khớp sha256 của PDF; PDF khác bản đã ghim thì dừng, vì đáp án neo theo đúng bản đó.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_graph.extract import extract  # noqa: E402
from paper_graph.files import sha256_file, write_json  # noqa: E402


def main(names: list[str]) -> int:
    papers = json.loads((ROOT / "bench" / "papers.json").read_text())["papers"]
    for p in papers:
        if names and p["name"] not in names:
            continue
        pdf = (ROOT / p["pdf"]).resolve()
        if not pdf.is_file():
            print(f"{p['name']}: thiếu {pdf}", file=sys.stderr)
            return 2
        if sha256_file(pdf) != p["sha256"]:
            print(f"{p['name']}: {pdf} khác bản đã ghim (sha256), đáp án không còn khớp", file=sys.stderr)
            return 2
        out = ROOT / "bench" / "papers" / p["name"] / f"{p['name']}.blocks.json"
        if out.is_file() and json.loads(out.read_text())["source"]["sha256"] == p["sha256"]:
            print(f"{p['name']}: đã có {out.relative_to(ROOT)}")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = extract(pdf)
        write_json(out, doc)
        print(f"{p['name']}: {len(doc['pages'])} trang, {len(doc['blocks'])} đoạn → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    code = main(sys.argv[1:])
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)  # bỏ bước dọn dẹp onnxruntime lúc tắt, xem paper_graph.extract.release
