"""Con số trong ô phải có trong chữ bài mà ô neo vào (PG220, chốt chặn TM-7).

Neo chỉ chứng minh câu trích có thật; ô vẫn có thể viết sai con số của chính câu đó (28,4 thành 41,8). Con số là
thứ người đọc sơ đồ tin nhất và kiểm ít nhất, nên mỗi số trong ô phải tìm thấy trong các đoạn được neo, hay trong chữ
của hình, bảng gắn với ô.

Đọc số trong ô (tiếng Việt):
- một số là **một** giá trị, không bao giờ là danh sách: "41,8" là 41,8, không phải 41 và 8;
- nhận kiểu Việt (28,4; 1.234,5; 100.000) và kiểu Anh (28.4; 1,234.5; 100,000);
- số chỉ có một dấu ngăn và đúng ba chữ số sau ("512.000", "0,001") đọc được hai cách, lệch nhau 1000 lần: cách đọc
  hàng nghìn luôn được thử; cách đọc thập phân chỉ khi chữ bài viết đúng dãy đó, để "512.000" không khớp nhờ "512";
- số âm cần số âm trong bài; số dương khớp cả hai dấu (ô viết "giảm 5,1" cho "−5.1" của bài).
Phía bài đọc kiểu Anh, bỏ số trích dẫn ([5], [11, 12]) và số dính tên (P100, GPT-4), nhận số viết bằng chữ (eight),
khoảng (0.1-0.4), phân vị (p95).

Số chỉ tên trong ô không tính: Bảng 2, Hình 1, §3.1, Eq.(4), P100, GPT-4, LLaMA3-8B, 8x7B; và số nguyên ngay sau
"lớp/bước/vòng/nhóm/…" (lớp 5) trừ khi là định lượng ("mỗi lớp 0,3", "mỗi head 64 chiều"). Chỉ số đứng ngay sau từ chỉ
tên mới là tên: "Bảng 1–4", "Bảng 1 và 41 điểm" thì số sau vẫn bị kiểm (dãy tên viết lặp từ: "Bảng 1 tới Bảng 4"), vì
miễn kiểm cả dãy thì số bịa lọt qua ("Bảng 3 và 12 baseline").
"""
import re

_NUM = re.compile(r"(\d+(?:\.\d+)?[eE][-−+]?\d+|\d+(?:[.,]\d+)*)")
_SCI = re.compile(r"\d+(?:\.\d+)?[eE][-+]?\d+")
# Từ đứng trước luôn biến số thành tên: Bảng 2, §3.1
_NAME_WORD = (
    r"(?:§|\b(?:bảng|hình|mục|chương|phụ lục|thuật toán|định lý|bổ đề|công thức|phương trình|dòng|trang|tr\.|cột|"
    r"tables?|tabs?\.|figures?|figs?\.|eqs?\.|eqs?|equations?|sections?|secs?\.|algorithms?|algs?\.|theorems?|"
    r"lemmas?|appendix|appendices|lines?|rows?))")
_STRONG = re.compile(_NAME_WORD + r"\s*\(?\s*$", re.IGNORECASE)
# Từ đứng trước chỉ biến SỐ NGUYÊN thành tên (lớp 5, bước 2), và không khi có "mỗi/each/per" trước nó (định lượng)
_WEAK = re.compile(
    r"(?:(mỗi|từng|each|per)\s+)?\b(?:phần|bước|nhóm|giai đoạn|vòng|lớp|phiên bản|version|stage|phase|round|layer|"
    r"head|group|step)\s*\(?\s*$",
    re.IGNORECASE)
_CITATION = re.compile(r"\[\s*\d+(?:\s*[,–\-]\s*\d+)*\s*\]")
_WORDS = {w: v for v, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
_WORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
               "hundred": 100, "thousand": 1000, "dozen": 12})
_WORD = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.IGNORECASE)
_MINUS = "-−"
# Tên có dấu cách trước số (Qwen 2.5, LLaMA 2, Gemma 3): chữ hoa đầu, không phải từ chức năng, và cặp "tên số" lặp lại
# trong bài. Số đứng sau đúng cặp đó trong ô là tên, không phải đại lượng.
_PAIR = re.compile(r"\b([A-Z][A-Za-z]{2,}|[A-Z]{2,})\s(\d+(?:\.\d+)?)(?![\d.,]*\d)")
_FUNCTION_WORDS = {"In", "On", "At", "The", "Of", "For", "By", "To", "From", "With", "Over", "Under", "About", "Than",
                   "And", "Or", "Only", "All", "Each", "Per", "Up", "Our", "We", "Its", "This", "These", "That", "Are",
                   "Was", "Were", "Has", "Have", "Had", "Into", "Via", "Since", "Until", "After", "Before", "Using"}


def _key(v: float) -> float:
    return round(v, 9)


def _tokens(text: str):
    """(chuỗi số, có phải tên không, âm không, vị trí) cho mọi số trong chữ. Tên: chữ cái dính ngay trước (P100), chữ
    cái hay chữ số dính ngay sau mà không phải đơn vị thuần chữ (8x7B), hay gạch nối nối với một từ (GPT-4)."""
    for mt in _NUM.finditer(text):
        a, z = mt.span()
        before = text[a - 1] if a else " "  # đầu chuỗi coi như sau khoảng trắng ("" in ".," là True)
        if before.isdigit() or before in ".,":
            continue  # phần đuôi của một số đã đọc
        name = before.isalpha() or before == "_"
        negative = False
        if before in _MINUS:
            k = a - 2
            while k >= 0 and (text[k].isalnum() or text[k] in "._"):
                k -= 1
            word = text[k + 1:a - 1]
            if word:  # gạch nối dính vào chữ phía trước: tên (GPT-4) hay khoảng (0.1-0.4), không phải dấu âm
                name = any(c.isalpha() for c in word)
            else:
                negative = True
        elif before == " " and a >= 2 and text[a - 2] in _MINUS and (a < 3 or not text[a - 3].isalnum()):
            negative = True  # "− 5,1"
        tail = re.match(r"[A-Za-zµ%×]*", text[z:]).group(0)
        if tail and z + len(tail) < len(text) and text[z + len(tail)].isdigit():
            name = True  # 8x7B, 3D2
        yield mt.group(1), name, negative, a


def _readings(tok: str) -> list[tuple[float, bool]]:
    """Mọi cách đọc hợp lệ của MỘT số trong ô: (giá trị, cần chữ bài viết đúng dãy này mới tính)."""
    if _SCI.fullmatch(tok.replace("−", "-")):
        return [(_key(float(tok.replace("−", "-"))), False)]
    if tok.isdigit():
        return [(_key(float(tok)), False)]
    out = []
    ambiguous = re.fullmatch(r"\d+[.,]\d{3}", tok) is not None
    if re.fullmatch(r"[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?", tok):  # kiểu Anh, có ngăn hàng nghìn
        out.append((_key(float(tok.replace(",", ""))), False))
    elif re.fullmatch(r"\d+\.\d+", tok):  # kiểu Anh, thập phân
        out.append((_key(float(tok)), ambiguous))
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+(?:,\d+)?", tok):  # kiểu Việt, có ngăn hàng nghìn
        out.append((_key(float(tok.replace(".", "").replace(",", "."))), False))
    elif re.fullmatch(r"\d+,\d+", tok):  # kiểu Việt, thập phân
        out.append((_key(float(tok.replace(",", "."))), ambiguous))
    return out


def _is_name(text: str, at: int, tok: str) -> bool:
    window = text[max(0, at - 40):at]
    if _STRONG.search(window):
        return True
    weak = _WEAK.search(window)
    return bool(weak) and not weak.group(1) and tok.isdigit()


def name_pairs(paper_text: str) -> frozenset[tuple[str, str]]:
    """Các cặp (tên, số) như ("Qwen", "2.5") xuất hiện từ 2 lần trong bài: tên mô hình, phiên bản có dấu cách."""
    seen: dict[tuple[str, str], int] = {}
    for word, num in _PAIR.findall(paper_text):
        # chỉ số kiểu phiên bản (2, 3.1, 2.5): "BLEU 28.4", "Top 50" lặp lại vẫn là đại lượng, PG220 phải kiểm
        if word not in _FUNCTION_WORDS and re.fullmatch(r"(?:[1-9]|1\d|20)(?:\.\d)?", num):
            seen[(word, num)] = seen.get((word, num), 0) + 1
    return frozenset(k for k, c in seen.items() if c >= 2)


def _after_name(text: str, at: int, tok: str, names: frozenset) -> bool:
    mt = re.search(r"([A-Za-z]+)\s$", text[max(0, at - 40):at])
    return bool(mt) and (mt.group(1), tok) in names


def claimed(text: str, names: frozenset = frozenset()) -> list[tuple[str, bool, list[tuple[float, bool]]]]:
    """Các con số ô nêu ra (bỏ số chỉ tên, cả tên có dấu cách trong `names`): (chuỗi, âm không, các cách đọc)."""
    out = []
    for tok, name, negative, at in _tokens(text):
        if name or _is_name(text, at, tok) or _after_name(text, at, tok, names):
            continue
        readings = _readings(tok)
        if readings:
            out.append((tok, negative, readings))
    return out


def present(text: str) -> set[float]:
    """Mọi giá trị số có trong chữ bài (kiểu Anh, có dấu), bỏ số trích dẫn và số dính tên, cộng số viết bằng chữ."""
    text = _CITATION.sub(" ", text)
    vals: set[float] = set()
    for tok, name, negative, _ in _tokens(text):
        if name:
            continue
        sign = -1.0 if negative else 1.0
        t = tok.replace("−", "-")
        if _SCI.fullmatch(t):
            vals.add(_key(sign * float(t)))
            continue
        if t.count(".") > 1:
            continue  # số mục, số phiên bản (3.2.1): không phải đại lượng
        head, _, frac = t.partition(".")
        parts = head.split(",")
        if len(parts) > 1 and parts[0][:1] != "0" and all(len(p) == 3 for p in parts[1:]):
            parts = ["".join(parts)]  # ngăn hàng nghìn
        elif len(parts) > 1:
            frac = ""  # dấu phẩy liệt kê: "1,2" là 1 và 2
        for k, p in enumerate(parts):
            if p.isdigit():
                last = k == len(parts) - 1
                vals.add(_key(sign * float(p + ("." + frac if last and frac.isdigit() else ""))))
    vals.update(float(_WORDS[w.lower()]) for w in _WORD.findall(text))
    vals.update(float(x) for x in re.findall(r"(?<![A-Za-z])p(\d{2})(?!\d)", text))  # phân vị: p95, p99
    return vals


def _literal(tok: str, paper_text: str) -> bool:
    """Chữ bài có đúng dãy chữ số này (dấu ngăn . hay , đều được)?"""
    whole, frac = re.split(r"[.,]", tok)
    return re.search(r"(?<![\d.,])" + whole + r"[.,]" + frac + r"(?![\d])", paper_text) is not None


def values_of(text: str) -> set[float]:
    """Mọi giá trị (cả hai dấu, mọi cách đọc) của các con số mà chữ trong ô nêu ra, bỏ số chỉ tên: để so một ô có
    nhắc tới một con số hay không, bất kể viết kiểu Việt hay kiểu Anh."""
    return {(-v if negative else v) for _, negative, readings in claimed(text) for v, _ in readings}


def missing(node_text: str, paper_text: str, names: frozenset = frozenset()) -> list[str]:
    """Số trong ô mà không cách đọc nào có trong chữ bài. `names`: cặp tên-số của cả bài (`name_pairs`)."""
    have = present(paper_text)
    lost = []
    for tok, negative, readings in claimed(node_text, names):
        ok = False
        for value, needs_literal in readings:
            if needs_literal and not _literal(tok, paper_text):
                continue
            hit = (-value in have) if negative else (value in have or -value in have)
            if hit:
                ok = True
                break
        # năm (WMT 2014) thường dính tên trong bài (newstest2014): chấp nhận nếu đúng dãy chữ số đó có trong bài
        if not ok and re.fullmatch(r"(19|20)\d\d", tok) and re.search(r"(?<!\d)" + tok + r"(?!\d)", paper_text):
            ok = True
        if not ok:
            lost.append(("−" if negative else "") + tok)
    return list(dict.fromkeys(lost))
