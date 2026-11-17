#!/usr/bin/env python3
"""Zero-dependency stdlib HTTP file server for bootstrapping target machines.

Supports token auth, streaming file uploads, folder creation, and file/folder
deletion within a single confined root directory. Compatible with Python 3.10+.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import hmac
import json
import os
import pty
import secrets
import select
import shutil
import struct
import subprocess
import sys
import termios
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CHUNK_BYTES = 1024 * 1024
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

UI_FILE = Path(__file__).with_name("bootstrap_ui.html")


def resolve_inside(root: Path, rel: str) -> Path:
    clean = rel.strip().lstrip("/")
    target = (root / clean).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"path outside root: {rel}")
    return target


def ws_accept_key(key: str) -> str:
    digest = hashlib.sha1((key.strip() + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def _recv_exact(sock, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("websocket closed")
        buf.extend(chunk)
    return bytes(buf)


def ws_read_frame(sock) -> tuple[int, bytes]:
    b1, b2 = _recv_exact(sock, 2)
    opcode = b1 & 0x0F
    masked = bool(b2 & 0x80)
    length = b2 & 0x7F
    if length == 126:
        (length,) = struct.unpack("!H", _recv_exact(sock, 2))
    elif length == 127:
        (length,) = struct.unpack("!Q", _recv_exact(sock, 8))
    mask = _recv_exact(sock, 4) if masked else b""
    data = _recv_exact(sock, length)
    if masked:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return opcode, data


def ws_send_frame(sock, opcode: int, data: bytes, lock: threading.Lock) -> None:
    n = len(data)
    if n < 126:
        header = struct.pack("!BB", 0x80 | opcode, n)
    elif n < 65536:
        header = struct.pack("!BBH", 0x80 | opcode, 126, n)
    else:
        header = struct.pack("!BBQ", 0x80 | opcode, 127, n)
    with lock:
        sock.sendall(header + data)


def run_bash_ws(sock, root: Path) -> None:
    shell = "/bin/bash" if Path("/bin/bash").exists() else os.environ.get("SHELL", "/bin/sh")
    master_fd, slave_fd = pty.openpty()
    env = {**os.environ, "TERM": "xterm-256color"}
    proc = subprocess.Popen(
        [shell, "-i"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=str(root),
        env=env,
        start_new_session=True,
        close_fds=True,
    )
    os.close(slave_fd)
    send_lock = threading.Lock()
    stop = threading.Event()

    def pump_pty() -> None:
        try:
            while not stop.is_set():
                r, _, _ = select.select([master_fd], [], [], 0.2)
                if not r:
                    if proc.poll() is not None:
                        break
                    continue
                chunk = os.read(master_fd, 4096)
                if not chunk:
                    break
                ws_send_frame(sock, 0x1, chunk.decode("utf-8", errors="replace").encode("utf-8"), send_lock)
        except OSError:
            pass
        finally:
            try:
                ws_send_frame(sock, 0x8, b"", send_lock)
            except OSError:
                pass

    reader = threading.Thread(target=pump_pty, daemon=True)
    reader.start()
    try:
        while True:
            opcode, payload = ws_read_frame(sock)
            if opcode == 0x8:  # close
                break
            if opcode == 0x9:  # ping -> pong
                ws_send_frame(sock, 0xA, payload, send_lock)
                continue
            if opcode not in (0x1, 0x2):
                continue
            text = payload.decode("utf-8", errors="replace")
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                msg = {"type": "input", "data": text}
            if isinstance(msg, dict) and msg.get("type") == "resize":
                rows = max(1, int(msg.get("rows", 24)))
                cols = max(1, int(msg.get("cols", 80)))
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
            elif isinstance(msg, dict) and msg.get("type") == "input":
                os.write(master_fd, str(msg.get("data", "")).encode("utf-8"))
    except (EOFError, OSError):
        pass
    finally:
        stop.set()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        try:
            os.close(master_fd)
        except OSError:
            pass
        reader.join(timeout=1.0)


def make_handler(root: Path, token: str, allow_root_switch: bool = False) -> type[BaseHTTPRequestHandler]:
    state = {"root": root.resolve()}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            sys.stderr.write(f"[bootstrap] {self.address_string()} - {fmt % args}\n")

        def send_json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authorized(self, qs: dict[str, list[str]] | None = None) -> bool:
            if not token:
                return True
            supplied = self.headers.get("X-Token", "")
            auth = self.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                supplied = supplied or auth[7:].strip()
            if not supplied and qs:
                supplied = qs.get("token", [""])[0]
            return hmac.compare_digest(supplied, token)

        def parse_url(self) -> tuple[str, dict[str, list[str]]]:
            parsed = urllib.parse.urlsplit(self.path)
            return parsed.path, urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

        def do_GET(self) -> None:
            route, qs = self.parse_url()
            if route == "/":
                body = UI_FILE.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if not self.authorized(qs if route == "/ws/bash" else None):
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            if route == "/ws/bash":
                key = self.headers.get("Sec-WebSocket-Key")
                if not key or self.headers.get("Upgrade", "").lower() != "websocket":
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "websocket upgrade required"})
                    return
                self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
                self.send_header("Upgrade", "websocket")
                self.send_header("Connection", "Upgrade")
                self.send_header("Sec-WebSocket-Accept", ws_accept_key(key))
                self.end_headers()
                self.close_connection = True
                run_bash_ws(self.connection, state["root"])
                return
            if route == "/api/list":
                rel = qs.get("path", [""])[0]
                cur_root = state["root"]
                try:
                    folder = resolve_inside(cur_root, rel)
                    if not folder.is_dir():
                        raise ValueError(f"not a folder: {rel}")
                    entries = []
                    for child in folder.iterdir():
                        try:
                            if not child.resolve().is_relative_to(cur_root):
                                continue
                            st = child.stat()
                        except OSError:
                            continue
                        is_dir = child.is_dir()
                        entries.append({
                            "name": child.name,
                            "path": child.relative_to(cur_root).as_posix(),
                            "dir": is_dir,
                            "size": None if is_dir else st.st_size,
                        })
                    entries.sort(key=lambda e: (not e["dir"], e["name"].casefold()))
                    cur = "" if folder == cur_root else folder.relative_to(cur_root).as_posix()
                    self.send_json(HTTPStatus.OK, {
                        "root": str(cur_root),
                        "path": cur,
                        "entries": entries,
                        "allowRootSwitch": allow_root_switch,
                    })
                except ValueError as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if not self.authorized():
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            route, _ = self.parse_url()
            cur_root = state["root"]
            if route == "/api/root":
                if not allow_root_switch:
                    self.send_json(HTTPStatus.FORBIDDEN, {"error": "root switching is disabled (--lock-root)"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                    raw_path = data.get("path", "")
                    if not isinstance(raw_path, str) or not raw_path.strip():
                        raise ValueError("path is required")
                    candidate = Path(raw_path).expanduser().resolve()
                    if not candidate.is_dir():
                        raise ValueError(f"not a folder: {raw_path}")
                    state["root"] = candidate
                    self.send_json(HTTPStatus.OK, {"root": str(candidate)})
                except (ValueError, json.JSONDecodeError) as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            if route == "/api/mkdir":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                    rel = data.get("path", "")
                    if not isinstance(rel, str) or not rel.strip():
                        raise ValueError("path is required")
                    target = resolve_inside(cur_root, rel)
                    if target == cur_root:
                        raise ValueError("cannot create root")
                    if target.exists():
                        self.send_json(HTTPStatus.CONFLICT, {"error": f"already exists: {rel}"})
                        return
                    target.mkdir(parents=True, exist_ok=False)
                    self.send_json(HTTPStatus.CREATED, {"path": target.relative_to(cur_root).as_posix()})
                except (ValueError, json.JSONDecodeError) as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_PUT(self) -> None:
            if not self.authorized():
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            route, qs = self.parse_url()
            if route == "/api/file":
                rel = qs.get("path", [""])[0]
                overwrite = qs.get("overwrite", ["1"])[0] != "0"
                raw_len = self.headers.get("Content-Length")
                if raw_len is None:
                    self.send_json(HTTPStatus.LENGTH_REQUIRED, {"error": "Content-Length required"})
                    return
                try:
                    remaining = int(raw_len)
                    if remaining < 0:
                        raise ValueError("invalid Content-Length")
                    if not rel.strip():
                        raise ValueError("path is required")
                    cur_root = state["root"]
                    target = resolve_inside(cur_root, rel)
                    if target == cur_root or target.is_dir():
                        raise ValueError(f"invalid file path: {rel}")
                    if target.exists() and not overwrite:
                        self.send_json(HTTPStatus.CONFLICT, {"error": f"file exists: {rel}"})
                        return
                    target.parent.mkdir(parents=True, exist_ok=True)
                    tmp = target.with_name(f".upload-{secrets.token_hex(6)}-{target.name}")
                    written = 0
                    try:
                        with tmp.open("wb") as out:
                            while remaining > 0:
                                chunk = self.rfile.read(min(CHUNK_BYTES, remaining))
                                if not chunk:
                                    raise EOFError("unexpected end of upload stream")
                                out.write(chunk)
                                remaining -= len(chunk)
                                written += len(chunk)
                        os.replace(tmp, target)
                    except Exception:
                        tmp.unlink(missing_ok=True)
                        raise
                    self.send_json(HTTPStatus.CREATED, {"path": target.relative_to(cur_root).as_posix(), "bytes": written})
                except (ValueError, EOFError) as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_DELETE(self) -> None:
            if not self.authorized():
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            route, qs = self.parse_url()
            if route == "/api/entry":
                rel = qs.get("path", [""])[0]
                cur_root = state["root"]
                try:
                    target = resolve_inside(cur_root, rel)
                    if target == cur_root:
                        raise ValueError("cannot delete root")
                    if not target.exists():
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": f"not found: {rel}"})
                        return
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                    self.send_json(HTTPStatus.OK, {"deleted": target.relative_to(cur_root).as_posix()})
                except ValueError as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Zero-dependency bootstrap file server")
    parser.add_argument("--root", default="~/", help="Initial root directory (default: ~/)")
    parser.add_argument("--lock-root", action="store_true", help="Disallow switching root directory from the UI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8088, help="Bind port (default: 8088)")
    parser.add_argument("--token", default=os.environ.get("BOOTSTRAP_TOKEN", ""), help="API token (auto-generated if empty)")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = args.token or secrets.token_urlsafe(18)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(root, token, allow_root_switch=not args.lock_root))
    print(f"Bootstrap server listening on http://{args.host}:{args.port}")
    print(f"Root : {root}")
    print(f"Token: {token}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
