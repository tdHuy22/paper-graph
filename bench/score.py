"""Chấm cả bộ đo: với mỗi bài trong bench/papers.json có sơ đồ ở <thư mục>/<tên>/<tên>.graph.json, chạy check rồi score.

    python3 bench/score.py                          # sơ đồ dựng tay trong bench/papers/
    python3 bench/score.py .tmp/dung-so-do-workspace/iteration-1   # sơ đồ do skill dựng
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_graph import blocks as blocks_mod  # noqa: E402
from paper_graph import gold as gold_mod  # noqa: E402
from paper_graph import score as score_mod  # noqa: E402
from paper_graph.check import check, parse_graph  # noqa: E402
from paper_graph.files import InputError, read_json  # noqa: E402


def main(argv: list[str]) -> int:
    where = Path(argv[0]) if argv else ROOT / "bench" / "papers"
    papers = json.loads((ROOT / "bench" / "papers.json").read_text())["papers"]
    rows, worst = [], 0
    for p in papers:
        name = p["name"]
        gpath = where / name / f"{name}.graph.json"
        if not gpath.is_file():
            rows.append(f"{name:<14} chưa có sơ đồ")
            continue
        try:
            blocks, e1 = blocks_mod.parse(read_json(ROOT / "bench" / "papers" / name / f"{name}.blocks.json", "blocks"))
            gold, e2 = gold_mod.parse(read_json(ROOT / "bench" / "papers" / name / f"{name}.gold.json", "đáp án"))
            graph, diags = parse_graph(read_json(gpath, "sơ đồ"))
        except InputError as e:
            rows.append(f"{name:<14} HỎNG  {e}")
            worst = 2
            continue
        if e1 or e2 or graph is None:
            rows.append(f"{name:<14} HỎNG  {'; '.join((e1 + e2)[:3]) or 'sơ đồ không đọc được'}")
            worst = 2
            continue
        rep = check(graph, blocks, None, diags)
        s = score_mod.score(graph, gold, blocks).summary()
        ok = rep.errors == 0 and s["coverage"] >= 0.8
        worst = max(worst, 0 if ok else 1)
        rows.append(f"{name:<14} {'đạt ' if ok else 'TRƯỢT'}  lỗi {rep.errors}, cảnh báo {rep.warnings}, "
                    f"neo {rep.stats['anchors_ok']}/{rep.stats['anchors']}, {rep.stats['nodes']} ô · "
                    f"phủ {s['covered']}/{s['must']} ({s['coverage']:.0%}), đúng tầng {s['tier']:.0%}, "
                    f"quan hệ {s['relations']:.0%}, tuỳ chọn {s['optional_covered']}/{s['optional']}")
    print("\n".join(rows))
    print("ngưỡng: 0 lỗi check, phủ ≥ 80% ý bắt buộc")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
