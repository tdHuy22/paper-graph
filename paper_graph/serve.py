"""`paper-graph serve`: trình xem có chế độ sửa, chạy trên máy chủ cục bộ (Mốc 3).

Trang là đúng trang của `view` (cùng CSP theo hash), thêm `connect-src 'self'` để gửi sửa đổi về server này. Mọi
trang web khác đang mở trong trình duyệt cũng gửi được request tới 127.0.0.1, nên (`.agent/threat-model.md`):
- TM-16: POST phải có header `X-PG-Token` khớp token ngẫu nhiên của lần chạy (chỉ nằm trong trang server trả; header
  tự đặt buộc preflight mà server không trả CORS), `Content-Type: application/json`, `Origin` và `Sec-Fetch-Site`
  (nếu có) phải là chính server; trang không được nhúng vào khung (`frame-ancestors 'none'`);
- TM-17: `Host` phải là `127.0.0.1:<cổng>` hay `localhost:<cổng>` ở mọi route (chặn DNS rebinding); chỉ có route cố
  định, không phục vụ file theo đường dẫn;
- TM-19: mỗi sửa đổi đọc lại `graph.json` và đòi `version` (SHA-256 của file) khớp bản trang đang giữ;
- TM-18, TM-20: nội dung sửa đổi kiểm ở `edits.py`.
Mỗi kết nối một luồng (trình duyệt hay mở sẵn kết nối dự phòng; một luồng thì kết nối rảnh chặn cả server), còn đọc
và ghi sơ đồ đi qua một khoá nên các sửa đổi vẫn nối tiếp nhau.
"""
import hashlib
import hmac
import json
import re
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import blocks as blocks_mod
from . import edits, view
from .check import parse_graph
from .files import (MAX_JSON_BYTES, InputError, format_graph, parse_json, read_json, read_regular, sibling,
                    write_atomic)
from .text import safe

MAX_BODY = 64 * 1024
HOST = "127.0.0.1"


class App:
    """Trạng thái của một lần chạy: đường dẫn, token, ảnh đã cắt (cắt một lần lúc mở, sửa chữ không đổi ảnh)."""

    def __init__(self, graph_path: Path, blocks_path: Path | None, pdf: Path | None, images: bool, crops: bool):
        self.graph_path = graph_path
        self.blocks_arg = blocks_path
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        data, self.stats = view.build_data(graph_path, blocks_path, pdf, images, crops)
        self.images = data["images"]
        self.port = 0

    def _read(self) -> tuple[bytes, str]:
        raw = read_regular(self.graph_path, "sơ đồ", MAX_JSON_BYTES)
        return raw, hashlib.sha256(raw).hexdigest()

    def data(self) -> tuple[dict, str]:
        """Dữ liệu trang và `version` của đúng bản trên đĩa đã dựng ra dữ liệu đó (băm trước, dựng sau, rồi kiểm lại)."""
        for _ in range(3):
            _, before = self._read()
            data, _ = view.build_data(self.graph_path, self.blocks_arg, images=False)
            if self._read()[1] == before:
                data["images"] = self.images
                return data, before
        raise InputError("sơ đồ trên đĩa đang đổi liên tục: thử lại sau")

    def page(self) -> str:
        with self.lock:
            data, version = self.data()
        return view.page(data, {"token": self.token, "version": version})

    def _blocks(self, graph) -> blocks_mod.Blocks:
        path = self.blocks_arg or sibling(self.graph_path, graph.blocks_file or "", ".blocks.json")
        bl, errs = blocks_mod.parse(read_json(path, "blocks"))
        if errs:
            raise InputError(f"{path} hỏng")
        return bl

    def _fresh(self, body: dict):
        """Sơ đồ trên đĩa, sau khi kiểm nó vẫn là bản trang đang giữ (TM-19): băm và parse cùng một lần đọc."""
        raw, version = self._read()
        if body.get("version") != version:
            raise Conflict()
        doc = parse_json(raw, "sơ đồ", self.graph_path)
        if not isinstance(doc, dict):
            raise InputError("sơ đồ trên đĩa không đọc được")
        graph, _ = parse_graph(doc)
        if graph is None:
            raise InputError("sơ đồ trên đĩa không đọc được")
        return doc, graph

    def edit(self, body: dict) -> dict:
        with self.lock:
            doc, graph = self._fresh(body)
            new = edits.edit_node(doc, body.get("node"), body.get("set"), self._blocks(graph))
            write_atomic(self.graph_path, format_graph(new).encode("utf-8"))
            return self._reply()

    def move(self, body: dict) -> dict:
        with self.lock:
            _, graph = self._fresh(body)
            lp = edits.layout_path(self.graph_path)
            pins, _ = edits.read_pins(lp, graph, strict=True)
            moves = None if body.get("reset") is True else body.get("pos")
            edits.write_pins(lp, graph, edits.move(pins, graph, body.get("tier"), moves))
            return self._reply()

    def _reply(self) -> dict:
        data, version = self.data()
        return {"version": version, "tiers": data["tiers"], "nodes": data["nodes"], "figures": data["figures"],
                "edges": data["edges"], "note": data["note"]}


class Conflict(Exception):
    pass


class Handler(BaseHTTPRequestHandler):
    server_version = "paper-graph"
    sys_version = ""
    timeout = 15
    app: App  # gán khi tạo server

    # ------------------------------------------------------------------ kiểm chung

    def _host_ok(self) -> bool:  # TM-17
        return self.headers.get("Host", "") in (f"{HOST}:{self.app.port}", f"localhost:{self.app.port}")

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, doc: dict) -> None:
        self._send(code, json.dumps(doc, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _deny(self, code: int, msg: str) -> None:
        self._json(code, {"error": msg})

    # ------------------------------------------------------------------ route

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            return self._deny(403, "Host không hợp lệ")
        if urlsplit(self.path).path != "/":
            return self._deny(404, "không có")
        try:
            html_page = self.app.page()
        except InputError as e:
            return self._deny(500, safe(str(e), 500))
        csp = _header_csp(html_page)
        self._send(200, html_page.encode("utf-8"), "text/html; charset=utf-8", {"Content-Security-Policy": csp})

    def do_POST(self):  # noqa: N802
        if not self._host_ok():
            return self._deny(403, "Host không hợp lệ")
        origin = self.headers.get("Origin")
        if origin is not None and origin != f"http://{self.headers.get('Host')}":  # TM-16
            return self._deny(403, "Origin lạ")
        site = self.headers.get("Sec-Fetch-Site")
        if site is not None and site != "same-origin":
            return self._deny(403, "request từ trang khác")
        try:
            token = self.headers.get("X-PG-Token", "").encode("ascii")
        except UnicodeEncodeError:
            token = b""
        if not hmac.compare_digest(token, self.app.token.encode("ascii")):
            return self._deny(403, "thiếu hay sai token")
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self._deny(415, "cần application/json")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._deny(411, "cần Content-Length")
        if not 0 < length <= MAX_BODY:
            return self._deny(413, "thân request quá lớn")
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            return self._deny(400, "JSON hỏng")
        if not isinstance(body, dict):
            return self._deny(400, "cần object JSON")
        route = {"/api/edit": self.app.edit, "/api/move": self.app.move}.get(urlsplit(self.path).path)
        if route is None:
            return self._deny(404, "không có")
        try:
            return self._json(200, route(body))
        except Conflict:
            return self._deny(409, "sơ đồ trên đĩa đã đổi từ lúc mở trang: tải lại trang rồi sửa tiếp")
        except edits.EditError as e:
            return self._json(422, {"error": safe(str(e), 500), "diags": [safe(x, 500) for x in e.diags]})
        except (InputError, OSError) as e:
            return self._deny(500, safe(str(e), 500))
        except Exception as e:  # noqa: BLE001 - lỗi lạ: trả JSON ngắn thay vì cắt kết nối, không lộ traceback (TM-17)
            self.log_message("lỗi xử lý: %s", type(e).__name__)
            return self._deny(500, "lỗi bên trong server")

    def log_request(self, code="-", size="-"):  # chỉ ghi request hỏng: sửa đổi thành công đã có dòng "Đã lưu" ở trang
        if not str(code).startswith("2"):
            super().log_request(code, size)

    def log_message(self, format, *args):  # noqa: A002 - tên của lớp cha
        sys.stderr.write(safe(f"{self.address_string()} {format % args}", 500) + "\n")


def _header_csp(html_page: str) -> str:
    """CSP của thẻ meta trong trang, thêm `frame-ancestors 'none'` (chỉ có hiệu lực ở header)."""
    meta = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html_page)
    return (meta.group(1) if meta else "default-src 'none'") + "; frame-ancestors 'none'"


def make_server(app: App, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"app": app})
    srv = ThreadingHTTPServer((HOST, port), handler)
    srv.daemon_threads = True
    app.port = srv.server_address[1]
    return srv
