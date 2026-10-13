"""Chuẩn hoá chữ để so câu trích, và làm sạch chữ không tin cậy trước khi in ra terminal.

Hai việc này ở chung một chỗ vì cùng một nguyên tắc: chữ lấy từ PDF hay từ sơ đồ do model sinh là dữ liệu
lạ. So khớp thì phải bỏ qua khác biệt hình thức (hoa thường, dấu câu, xuống dòng, gạch nối cuối dòng, chữ ghép
"ﬁ"); in ra thì không được để nó điều khiển terminal (TM-2 trong `.agent/threat-model.md`).
"""
import re
import unicodedata


_MINUS = set("-\u2212\u2013\u2010\u2011")  # gạch nối, dấu trừ, gạch ngắn: thành "-" khi đứng trước chữ số
_REL = set("<>≤≥=≠≈±+")  # dấu so sánh và dấu của số: gắn với con số đứng sau
_KEEP = _REL | set("%×∞")


def squash_index(s: str) -> tuple[str, list[int], list[bool]]:
    """Chuẩn hoá để so câu trích: trả chuỗi đã chuẩn hoá, vị trí trong chuỗi gốc của từng ký tự (để in lại đúng
    đoạn gốc khi báo lỗi), và `brk[k]`: trước ký tự thứ k có ranh giới từ hay ranh giới số không.

    Bỏ: hoa thường, dấu thanh và dấu phụ (tách NFKD từng ký tự, nên "é" liền và "e" + dấu rời như nhau; chữ ghép
    "ﬁ" và chữ toán 𝑥 về chữ thường), khoảng trắng, xuống dòng, dấu câu, gạch nối cuối dòng. Cùng ý với `squash` của
    skill paper-anatomy.

    Giữ những gì đổi nghĩa con số, vì neo là thứ chứng minh số liệu của ô "kết quả":
    - `.` giữa hai chữ số (28.4 khác 284); `,` ngăn hàng nghìn (100,000);
    - dấu âm trước chữ số, kể cả cách bởi khoảng trắng (−3.2, "a − 3" như "a −3", 1e-5 khác 1e5, 2-3 khác 23;
      dấu mũ ⁻ về "-" nhờ NFKD);
    - `< > ≤ ≥ = ≠ ≈ ± + % × ∞`;
    - hai nhóm chữ số cách nhau bởi thứ bị bỏ thì chèn `|` ("[1, 2]" khác "12").
    Dấu so sánh hay dấu của số dính với con số sau nó, % dính với con số trước nó: không có ranh giới ở giữa, nên
    câu trích không thể bắt đầu bằng "3.2" khi bài viết "−3.2", hay dừng ở "80.5" khi bài viết "80.5%"."""
    chars = [(ch, i) for i, c in enumerate(s) for ch in unicodedata.normalize("NFKD", c).casefold()]
    n = len(chars)
    out: list[str] = []
    where: list[int] = []
    brk: list[bool] = []
    last = -2  # chỉ số trong `chars` của ký tự giữ lại gần nhất

    def blank(a: int, b: int) -> bool:
        return all(chars[t][0].isspace() for t in range(a, b))

    def emit(ch: str, j: int, i: int) -> None:
        nonlocal last
        gap = not out or j > last + 1
        if gap and out and blank(last + 1, j) and (
                (ch.isdigit() and out[-1] in _REL | {"-"}) or (ch == "%" and out[-1].isdigit())):
            gap = False
        if gap and out and ch.isdigit() and out[-1].isdigit():
            out.append("|")
            where.append(i)
            brk.append(True)
        out.append(ch)
        where.append(i)
        brk.append(gap)
        last = j

    for j, (ch, i) in enumerate(chars):
        nxt = chars[j + 1][0] if j + 1 < n else ""
        prev_digit = bool(out) and out[-1].isdigit() and last == j - 1
        if ch.isalnum():
            emit(ch, j, i)
        elif ch == ".":
            if prev_digit and nxt.isdigit():
                emit(ch, j, i)
        elif ch == ",":
            group = "".join(c for c, _ in chars[j + 1:j + 5])
            if prev_digit and len(group) >= 3 and group[:3].isdigit() and not group[3:4].isdigit():
                emit(ch, j, i)
        elif ch in _MINUS:
            k = j + 1
            while k < n and chars[k][0].isspace():
                k += 1
            if k < n and chars[k][0].isdigit():
                emit("-", j, i)
        elif ch in _KEEP:
            emit(ch, j, i)
    return "".join(out), where, brk


def squash_map(s: str) -> tuple[str, list[int]]:
    t, where, _ = squash_index(s)
    return t, where


def squash(s: str) -> str:
    return squash_index(s)[0]


def word_count(s: str) -> int:
    return len(re.findall(r"\w+", s))


# Ký tự điều khiển C0, DEL, C1, và ký tự định hướng Unicode (đảo chiều chữ, cách ly hướng, đánh dấu hướng)
# U+2028/2029 (ngăn dòng, ngăn đoạn Unicode): có công cụ hiện chúng thành xuống dòng, đủ để giả một dòng `[id]` mới
_UNSAFE = re.compile("[\x00-\x1f\x7f-\x9f؜‎‏‪-‮⁦-⁩\u2028\u2029]")


def safe(s: object, limit: int = 160) -> str:
    """Chuỗi không tin cậy → một dòng in được: ký tự điều khiển và ký tự định hướng thành dạng thoát nhìn thấy
    được (`\\x1b`, `\\u202e`), cắt bớt khi quá dài. Mọi chuỗi lấy từ PDF hay sơ đồ phải đi qua đây trước khi in."""
    s = str(s)
    if len(s) > limit:
        s = s[: limit - 1] + "…"

    def esc(m: re.Match) -> str:
        o = ord(m.group())
        return f"\\x{o:02x}" if o < 0x100 else f"\\u{o:04x}"

    return _UNSAFE.sub(esc, s)
