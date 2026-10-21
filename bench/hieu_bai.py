"""Chấm phép đo hiểu bài với người đọc thật (docs/do-hieu-bai.md): đọc file kết quả, in so sánh từng người.

Mỗi dòng của file kết quả là một JSON: dòng người đọc chép từ trang làm bài, thêm hai trường người tổ chức ghi:
    {"nguoi": "P1", "nhom": "A", "bai": "bdfaa68d8984", "cach_doc": "chu", "dung": 9, "tong": 12, "giay": 410,
     "tra_loi": [1, 2, ...]}
Thêm "lan": 2 cho lần làm lại sau 7 ngày (mặc định 1). Chạy từ gốc repo:
    python3 bench/hieu_bai.py ket-qua.jsonl
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAYS = {"chu": "đọc chữ", "so-do": "đọc sơ đồ", "ca-hai": "cả hai"}


def quizzes() -> dict[str, dict]:
    """Bộ câu hỏi của bộ đo, theo 12 ký tự đầu của sha256 (trường `bai` của dòng kết quả)."""
    out = {}
    for p in sorted((ROOT / "bench" / "papers").glob("*/*.quiz.json")):
        d = json.loads(p.read_text("utf-8"))
        out[d["paper"]["sha256"][:12]] = {"name": p.parent.name, "questions": d["questions"]}
    return out


def load(path: Path, known: dict) -> tuple[list[dict], list[str]]:
    rows, errs = [], []
    for i, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            errs.append(f"dòng {i}: không phải JSON")
            continue
        q = known.get(str(r.get("bai")))
        if q is None:
            errs.append(f"dòng {i}: bài {r.get('bai')!r} không có trong bộ đo")
        elif not r.get("nguoi") or r.get("nhom") not in ("A", "B") or r.get("cach_doc") not in WAYS:
            errs.append(f"dòng {i}: thiếu `nguoi`, `nhom` (A, B) hay `cach_doc` lạ")
        elif not isinstance(r.get("tra_loi"), list) or len(r["tra_loi"]) != len(q["questions"]):
            errs.append(f"dòng {i}: `tra_loi` phải có {len(q['questions'])} phần tử")
        else:
            rows.append({**r, "paper": q["name"], "lan": r.get("lan", 1), "questions": q["questions"]})
    return rows, errs


def score(r: dict) -> dict:
    """Đúng, không biết (phương án cuối), và số đúng theo loại câu. Chấm lại từ `tra_loi`, không tin `dung`."""
    kinds: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    right = idk = 0
    for q, a in zip(r["questions"], r["tra_loi"]):
        ok = a == q["answer"]
        right += ok
        idk += a == len(q["choices"])
        kinds[q["kind"]][0] += ok
        kinds[q["kind"]][1] += 1
    return {"dung": right, "khong_biet": idk, "loai": dict(kinds)}


def report(rows: list[dict], lan: int = 1) -> str:
    rows = [r for r in rows if r["lan"] == lan and r["cach_doc"] in ("chu", "so-do")]
    by_person: dict[str, dict] = defaultdict(dict)
    for r in rows:
        by_person[r["nguoi"]][r["cach_doc"]] = {**r, **score(r)}
    lines = [f"Lần {lan}: {len(by_person)} người", ""]
    diffs: dict[str, list[int]] = defaultdict(list)
    for who in sorted(by_person):
        p = by_person[who]
        if "chu" not in p or "so-do" not in p:
            lines.append(f"{who}: thiếu một điều kiện, bỏ khỏi phép so")
            continue
        c, g = p["chu"], p["so-do"]
        d = g["dung"] - c["dung"]
        diffs[c["nhom"]].append(d)
        lines.append(f"{who} (nhóm {c['nhom']}): chữ {c['dung']}/12 ({c['paper']}, {c['khong_biet']} không biết, "
                     f"{c['giay'] // 60} phút) · sơ đồ {g['dung']}/12 ({g['paper']}, {g['khong_biet']} không biết, "
                     f"{g['giay'] // 60} phút) · hiệu {d:+d}")
    lines.append("")
    for name, ds in [("nhóm A", diffs["A"]), ("nhóm B", diffs["B"]), ("gộp", diffs["A"] + diffs["B"])]:
        if ds:
            lines.append(f"{name}: {len(ds)} người, trung vị hiệu (sơ đồ − chữ) {statistics.median(ds):+g}; "
                         f"hơn {sum(d > 0 for d in ds)}, kém {sum(d < 0 for d in ds)}, bằng {sum(d == 0 for d in ds)}")
    kinds: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for p in by_person.values():
        if "chu" in p and "so-do" in p:
            for way in ("chu", "so-do"):
                for k, (a, n) in p[way]["loai"].items():
                    kinds[(k, way)][0] += a
                    kinds[(k, way)][1] += n
    if kinds:
        lines.append("")
        lines.append("Theo loại câu (đúng / số câu, cộng mọi người):")
        for k in sorted({k for k, _ in kinds}):
            c, g = kinds[(k, "chu")], kinds[(k, "so-do")]
            lines.append(f"  {k:9} chữ {c[0]}/{c[1]} · sơ đồ {g[0]}/{g[1]}")
    if sum(len(v) for v in diffs.values()) < 20:
        lines.append("")
        lines.append("Dưới 20 người: báo trung vị và số hơn/kém/bằng, đừng kết luận từ trung bình.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    rows, errs = load(Path(argv[0]), quizzes())
    for e in errs:
        print(e, file=sys.stderr)
    for lan in sorted({r["lan"] for r in rows}):
        print(report(rows, lan))
        print()
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
