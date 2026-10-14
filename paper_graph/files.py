"""Đọc file có giới hạn: JSON có trần kích thước, đường dẫn lấy từ nội dung file không được ra khỏi thư mục.

Chốt chặn TM-1 (file cố tình to) và TM-4 (đường dẫn trong sơ đồ trỏ ra ngoài) ở `.agent/threat-model.md`.
"""
import hashlib
import json
import stat
from pathlib import Path

MAX_JSON_BYTES = 50 * 1024 * 1024


class InputError(Exception):
    """Input không dùng được: thông báo đã viết sẵn cho người đọc, không kèm traceback."""


def read_json(path: Path, what: str, limit: int = MAX_JSON_BYTES):
    try:
        size = path.stat().st_size
    except OSError as e:
        raise InputError(f"không đọc được {what} {path}: {e.strerror or e}") from None
    if size > limit:
        raise InputError(f"{what} {path} nặng {size // (1024 * 1024)} MB, quá trần {limit // (1024 * 1024)} MB")
    try:
        with path.open("rb") as f:
            data = f.read(limit + 1)
    except OSError as e:
        raise InputError(f"không đọc được {what} {path}: {e.strerror or e}") from None
    if len(data) > limit:  # file lớn lên giữa lúc stat và lúc đọc
        raise InputError(f"{what} {path} vượt trần {limit // (1024 * 1024)} MB")
    try:
        return json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as e:
        raise InputError(f"{what} {path} không phải UTF-8 (byte {e.start})") from None
    except json.JSONDecodeError as e:
        raise InputError(f"{what} {path} không phải JSON hợp lệ: dòng {e.lineno}, cột {e.colno}: {e.msg}") from None
    except ValueError as e:  # vd. số nguyên quá 4300 chữ số
        raise InputError(f"{what} {path} không đọc được: {e}") from None
    except RecursionError:
        raise InputError(f"{what} {path} lồng quá sâu") from None


def write_json(path: Path, doc) -> None:
    """Ghi nguyên tử: file tạm rồi đổi tên, dừng giữa chừng thì file cũ còn nguyên."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def read_regular(path: Path, what: str, limit: int) -> bytes:
    """Đọc cả file, chỉ khi nó là file thường (FIFO, thiết bị thì `read` chờ mãi) và không quá `limit` byte."""
    try:
        st = path.stat()
    except OSError as e:
        raise InputError(f"không đọc được {what} {path}: {e.strerror or e}") from None
    if not stat.S_ISREG(st.st_mode):
        raise InputError(f"{what} {path} không phải file thường")
    if st.st_size > limit:
        raise InputError(f"{what} {path} nặng {st.st_size // (1024 * 1024)} MB, quá trần {limit // (1024 * 1024)} MB")
    with path.open("rb") as f:
        data = f.read(limit + 1)
    if len(data) > limit:  # file lớn lên giữa lúc stat và lúc đọc
        raise InputError(f"{what} {path} vượt trần {limit // (1024 * 1024)} MB")
    return data


def sha256_file(path: Path) -> str:
    try:
        regular = stat.S_ISREG(path.stat().st_mode)
    except OSError as e:
        raise InputError(f"không đọc được {path}: {e.strerror or e}") from None
    if not regular:
        raise InputError(f"{path} không phải file thường")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sibling(base_file: Path, name: object, suffix: str) -> Path:
    """Tên file do nội dung một file khác chỉ định (vd. `paper.blocks` trong sơ đồ) → đường dẫn thật, chỉ khi nó
    nằm trong thư mục của file đó sau khi đã giải symlink, và có đuôi `suffix`."""
    if not isinstance(name, str) or not name:
        raise InputError("tên file phải là chuỗi không rỗng")
    if "\x00" in name:
        raise InputError("tên file chứa byte NUL")
    p = Path(name)
    if p.is_absolute() or ".." in p.parts or "\\" in name:
        raise InputError(f"tên file phải là đường dẫn tương đối nằm trong thư mục của sơ đồ, không phải {name!r}")
    if not name.endswith(suffix):
        raise InputError(f"tên file phải kết thúc bằng {suffix}")
    try:
        root = base_file.resolve().parent
        target = (root / p).resolve()
    except (OSError, RuntimeError, ValueError) as e:  # vòng symlink, tên quá dài
        raise InputError(f"không giải được đường dẫn {name!r}: {e}") from None
    if not target.is_relative_to(root):
        raise InputError(f"{name!r} trỏ ra ngoài thư mục của sơ đồ (qua symlink)")
    return target
