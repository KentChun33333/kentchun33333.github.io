import base64
import http.client
import importlib.util
import json
import os
import socket
import struct
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_server.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_server", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


@pytest.fixture
def server_url(tmp_path):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), MOD.make_handler(tmp_path, "secret-tok"))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        host, port = srv.server_address
        yield host, port, tmp_path
    finally:
        srv.shutdown()
        srv.server_close()


def req(host, port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    res = conn.getresponse()
    raw = res.read()
    conn.close()
    return res.status, raw


def test_token_auth_and_ui(server_url):
    host, port, _ = server_url
    status, _ = req(host, port, "GET", "/")
    assert status == 200
    status, _ = req(host, port, "GET", "/api/list")
    assert status == 401
    status, _ = req(host, port, "GET", "/api/list", headers={"X-Token": "wrong"})
    assert status == 401
    status, raw = req(host, port, "GET", "/api/list", headers={"X-Token": "secret-tok"})
    assert status == 200
    assert json.loads(raw)["entries"] == []


def test_mkdir_upload_list_and_delete(server_url):
    host, port, root = server_url
    auth = {"X-Token": "secret-tok"}

    # Create folder
    status, _ = req(host, port, "POST", "/api/mkdir", body=json.dumps({"path": "envs/conda"}), headers=auth)
    assert status == 201
    assert (root / "envs" / "conda").is_dir()

    # Upload file (streaming PUT)
    payload = b"TOKEN=abc\nPORT=8000\n"
    status, raw = req(
        host, port, "PUT", "/api/file?path=envs/.env",
        body=payload,
        headers={**auth, "Content-Length": str(len(payload))},
    )
    assert status == 201
    assert json.loads(raw)["bytes"] == len(payload)
    assert (root / "envs" / ".env").read_bytes() == payload

    # Overwrite=0 returns 409
    status, _ = req(
        host, port, "PUT", "/api/file?path=envs/.env&overwrite=0",
        body=b"new",
        headers={**auth, "Content-Length": "3"},
    )
    assert status == 409

    # List directory
    status, raw = req(host, port, "GET", "/api/list?path=envs", headers=auth)
    assert status == 200
    entries = json.loads(raw)["entries"]
    assert [(e["name"], e["dir"]) for e in entries] == [("conda", True), (".env", False)]

    # Delete file
    status, _ = req(host, port, "DELETE", "/api/entry?path=envs/.env", headers=auth)
    assert status == 200
    assert not (root / "envs" / ".env").exists()

    # Delete folder
    status, _ = req(host, port, "DELETE", "/api/entry?path=envs", headers=auth)
    assert status == 200
    assert not (root / "envs").exists()


def test_path_traversal_and_root_delete_blocked(server_url):
    host, port, _ = server_url
    auth = {"X-Token": "secret-tok"}

    assert req(host, port, "GET", "/api/list?path=..", headers=auth)[0] == 400
    assert req(host, port, "POST", "/api/mkdir", body=json.dumps({"path": "../evil"}), headers=auth)[0] == 400
    assert req(host, port, "PUT", "/api/file?path=../evil.txt", body=b"x", headers={**auth, "Content-Length": "1"})[0] == 400
    assert req(host, port, "DELETE", "/api/entry?path=", headers=auth)[0] == 400
    assert req(host, port, "DELETE", "/api/entry?path=..", headers=auth)[0] == 400


def _ws_send_masked_text(sock: socket.socket, text: str) -> None:
    data = text.encode("utf-8")
    mask = os.urandom(4)
    n = len(data)
    header = struct.pack("!BB", 0x81, 0x80 | n) if n < 126 else struct.pack("!BBH", 0x81, 0x80 | 126, n)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    sock.sendall(header + mask + masked)


def test_bash_websocket_requires_auth_and_runs_commands(server_url):
    host, port, _ = server_url
    assert req(host, port, "GET", "/ws/bash?token=wrong")[0] == 401

    sock = socket.create_connection((host, port), timeout=5)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET /ws/bash?token=secret-tok HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(handshake.encode("ascii"))
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += sock.recv(1024)
        assert b"101 Switching Protocols" in resp

        _ws_send_masked_text(sock, json.dumps({"type": "input", "data": "echo WS_BASH_OK\n"}))
        collected = ""
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and "WS_BASH_OK" not in collected:
            opcode, payload = MOD.ws_read_frame(sock)
            if opcode == 0x1:
                collected += payload.decode("utf-8", errors="replace")
        assert "WS_BASH_OK" in collected
    finally:
        sock.close()
