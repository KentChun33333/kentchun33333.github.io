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

HTML_UI = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bootstrap File Server</title>
<style>
  :root { --bg: #f6f7f9; --card: #fff; --ink: #181a1f; --muted: #656d76; --line: #d8dee4; --accent: #0969da; --danger: #cf222e; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); }
  .wrap { max-width: 900px; margin: 28px auto; padding: 0 16px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; margin-bottom: 14px; }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .between { justify-content: space-between; }
  h1 { margin: 0; font-size: 18px; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; }
  .muted { color: var(--muted); }
  input[type=text], input[type=password] { padding: 7px 10px; border: 1px solid var(--line); border-radius: 6px; font: inherit; }
  button { padding: 7px 12px; border: 1px solid var(--line); border-radius: 6px; background: #fff; color: var(--ink); cursor: pointer; font: inherit; }
  button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  button.danger { color: var(--danger); border-color: #f0b8bd; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--line); }
  th { font-size: 12px; color: var(--muted); font-weight: 600; }
  .name-btn { border: 0; background: none; padding: 0; color: var(--accent); font-weight: 500; text-align: left; }
  .progress { width: 100%; height: 8px; background: #eaeef2; border-radius: 99px; overflow: hidden; margin-top: 8px; display: none; }
  .progress > i { display: block; height: 100%; width: 0%; background: var(--accent); transition: width .1s; }
  .status { margin-top: 8px; font-size: 13px; }
  .err { color: var(--danger); }
  .term { background: #14171c; color: #e6edf3; border-radius: 8px; padding: 10px 12px; height: 280px; overflow: auto; margin: 10px 0 8px; white-space: pre-wrap; word-break: break-word; font: 12.5px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }
  .term-bar { display: flex; gap: 8px; }
  .term-bar input { flex: 1; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="row between">
      <div>
        <h1>Bootstrap File Server</h1>
        <div class="muted mono" id="rootPath"></div>
      </div>
      <div class="row">
        <input id="tokenInput" type="password" placeholder="API Token" size="24">
        <button id="saveTokenBtn">Connect</button>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="row between">
      <div class="row">
        <strong>Path:</strong>
        <span class="mono" id="cwdLabel">/</span>
        <button id="upBtn">.. Up</button>
        <button id="refreshBtn">Refresh</button>
      </div>
      <div class="row">
        <input id="mkdirInput" type="text" placeholder="New folder name">
        <button id="mkdirBtn">Create Folder</button>
      </div>
    </div>
    <div class="row" style="margin-top: 12px;">
      <input id="fileInput" type="file" multiple>
      <label class="row muted"><input id="overwriteChk" type="checkbox" checked> Overwrite existing</label>
      <button class="primary" id="uploadBtn">Upload Selected</button>
    </div>
    <div class="progress" id="progWrap"><i id="progBar"></i></div>
    <div class="status" id="status"></div>
    <table>
      <thead><tr><th>Name</th><th>Type</th><th>Size</th><th>Actions</th></tr></thead>
      <tbody id="listBody"></tbody>
    </table>
  </div>

  <div class="card">
    <div class="row between">
      <div class="row">
        <strong>Bash Terminal</strong>
        <span class="muted mono" id="termState">disconnected</span>
      </div>
      <div class="row">
        <button id="termConnBtn" class="primary">Connect Bash</button>
        <button id="termCtrlCBtn" disabled>Ctrl+C</button>
        <button id="termClearBtn">Clear</button>
      </div>
    </div>
    <pre class="term" id="termOut"></pre>
    <div class="term-bar">
      <input id="termIn" type="text" placeholder="Type bash command and press Enter (e.g. ls -la, conda --version)" disabled>
      <button id="termSendBtn" disabled>Run</button>
    </div>
  </div>
</div>
<script>
(() => {
  const $ = id => document.getElementById(id);
  let cwd = '';
  const urlToken = new URLSearchParams(location.search).get('token') || '';
  let token = urlToken || sessionStorage.getItem('bootstrap_token') || '';
  if (urlToken) sessionStorage.setItem('bootstrap_token', token);
  $('tokenInput').value = token;
  const currentToken = () => {
    const v = $('tokenInput').value.trim();
    if (v !== token) {
      token = v;
      sessionStorage.setItem('bootstrap_token', token);
    }
    return token;
  };

  const setStatus = (msg, isErr = false) => {
    const el = $('status');
    el.textContent = msg;
    el.className = isErr ? 'status err' : 'status muted';
  };
  const headers = () => {
    const t = currentToken();
    return t ? { 'X-Token': t } : {};
  };
  const joinPath = (dir, name) => (dir ? `${dir}/${name}` : name);
  const fmtSize = n => (n == null ? '—' : n < 1024 ? `${n} B` : n < 1048576 ? `${(n/1024).toFixed(1)} KB` : `${(n/1048576).toFixed(1)} MB`);

  async function api(url, opts = {}) {
    const res = await fetch(url, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  async function load(dir = cwd) {
    try {
      const data = await api(`/api/list?path=${encodeURIComponent(dir)}`);
      cwd = data.path;
      $('rootPath').textContent = `root: ${data.root}`;
      $('cwdLabel').textContent = cwd ? `/${cwd}` : '/';
      $('upBtn').disabled = !cwd;
      const body = $('listBody');
      body.innerHTML = '';
      for (const e of data.entries) {
        const tr = document.createElement('tr');
        const tdName = document.createElement('td');
        if (e.dir) {
          const b = document.createElement('button');
          b.className = 'name-btn mono';
          b.textContent = `${e.name}/`;
          b.onclick = () => load(e.path);
          tdName.appendChild(b);
        } else {
          const s = document.createElement('span');
          s.className = 'mono';
          s.textContent = e.name;
          tdName.appendChild(s);
        }
        const tdType = document.createElement('td');
        tdType.textContent = e.dir ? 'folder' : 'file';
        const tdSize = document.createElement('td');
        tdSize.className = 'mono';
        tdSize.textContent = fmtSize(e.size);
        const tdAct = document.createElement('td');
        const del = document.createElement('button');
        del.className = 'danger';
        del.textContent = e.dir ? 'Delete Folder' : 'Delete';
        del.onclick = async () => {
          if (!confirm(`Delete ${e.dir ? 'folder' : 'file'} "${e.path}"?`)) return;
          try {
            await api(`/api/entry?path=${encodeURIComponent(e.path)}`, { method: 'DELETE' });
            setStatus(`Deleted ${e.path}`);
            load(cwd);
          } catch (err) { setStatus(err.message, true); }
        };
        tdAct.appendChild(del);
        tr.append(tdName, tdType, tdSize, tdAct);
        body.appendChild(tr);
      }
      if (!data.entries.length) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="4" class="muted">Empty folder</td>';
        body.appendChild(tr);
      }
    } catch (err) {
      setStatus(err.message, true);
    }
  }

  function uploadOne(file, relPath, overwrite) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', `/api/file?path=${encodeURIComponent(relPath)}&overwrite=${overwrite ? '1' : '0'}`);
      if (token) xhr.setRequestHeader('X-Token', token);
      xhr.upload.onprogress = ev => {
        if (ev.lengthComputable) $('progBar').style.width = `${Math.round((ev.loaded / ev.total) * 100)}%`;
      };
      xhr.onload = () => {
        const data = (() => { try { return JSON.parse(xhr.responseText); } catch { return {}; } })();
        if (xhr.status >= 200 && xhr.status < 300) resolve(data);
        else reject(new Error(data.error || xhr.statusText));
      };
      xhr.onerror = () => reject(new Error('Network error during upload'));
      xhr.send(file);
    });
  }

  $('saveTokenBtn').onclick = () => {
    currentToken();
    setStatus('Token saved');
    load(cwd);
  };
  $('tokenInput').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); $('saveTokenBtn').click(); } });
  $('upBtn').onclick = () => load(cwd.split('/').slice(0, -1).join('/'));
  $('refreshBtn').onclick = () => load(cwd);
  $('mkdirBtn').onclick = async () => {
    const name = $('mkdirInput').value.trim();
    if (!name) return;
    try {
      await api('/api/mkdir', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: joinPath(cwd, name) }) });
      $('mkdirInput').value = '';
      setStatus(`Created folder ${name}`);
      load(cwd);
    } catch (err) { setStatus(err.message, true); }
  };
  $('uploadBtn').onclick = async () => {
    const files = [...$('fileInput').files];
    if (!files.length) return setStatus('Select at least one file', true);
    const overwrite = $('overwriteChk').checked;
    $('progWrap').style.display = 'block';
    try {
      for (const f of files) {
        $('progBar').style.width = '0%';
        setStatus(`Uploading ${f.name}...`);
        await uploadOne(f, joinPath(cwd, f.name), overwrite);
      }
      $('fileInput').value = '';
      setStatus(`Uploaded ${files.length} file(s)`);
      load(cwd);
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      setTimeout(() => { $('progWrap').style.display = 'none'; }, 500);
    }
  };
  load('');

  let ws = null;
  const stripAnsi = s => s.replace(/\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, '');
  const appendTerm = txt => {
    const out = $('termOut');
    out.textContent += stripAnsi(txt).replace(/\r\n/g, '\n').replace(/\r/g, '');
    out.scrollTop = out.scrollHeight;
  };
  const setTermConnected = on => {
    $('termState').textContent = on ? 'connected' : 'disconnected';
    $('termConnBtn').textContent = on ? 'Disconnect' : 'Connect Bash';
    $('termIn').disabled = !on;
    $('termSendBtn').disabled = !on;
    $('termCtrlCBtn').disabled = !on;
    if (on) $('termIn').focus();
  };
  const sendTerm = data => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'input', data }));
  };
  $('termConnBtn').onclick = () => {
    if (ws && ws.readyState <= WebSocket.OPEN) { ws.close(); return; }
    const t = currentToken();
    if (!t) { appendTerm('\n[enter API token above first]\n'); $('tokenInput').focus(); return; }
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/bash?token=${encodeURIComponent(t)}`);
    ws.onopen = () => {
      setTermConnected(true);
      ws.send(JSON.stringify({ type: 'resize', cols: 110, rows: 28 }));
    };
    ws.onmessage = ev => appendTerm(ev.data);
    ws.onclose = ev => {
      setTermConnected(false);
      appendTerm(ev.wasClean ? '\n[disconnected]\n' : '\n[connection closed — check API token]\n');
    };
    ws.onerror = () => appendTerm('\n[websocket error — check API token]\n');
  };
  const runCmd = () => {
    const v = $('termIn').value;
    sendTerm(v + '\n');
    $('termIn').value = '';
  };
  $('termSendBtn').onclick = runCmd;
  $('termIn').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); runCmd(); } });
  $('termCtrlCBtn').onclick = () => sendTerm('\x03');
  $('termClearBtn').onclick = () => { $('termOut').textContent = ''; };
})();
</script>
</body>
</html>
"""


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


def make_handler(root: Path, token: str) -> type[BaseHTTPRequestHandler]:
    root = root.resolve()

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
                body = HTML_UI.encode("utf-8")
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
                run_bash_ws(self.connection, root)
                return
            if route == "/api/list":
                rel = qs.get("path", [""])[0]
                try:
                    folder = resolve_inside(root, rel)
                    if not folder.is_dir():
                        raise ValueError(f"not a folder: {rel}")
                    entries = []
                    for child in folder.iterdir():
                        try:
                            if not child.resolve().is_relative_to(root):
                                continue
                            st = child.stat()
                        except OSError:
                            continue
                        is_dir = child.is_dir()
                        entries.append({
                            "name": child.name,
                            "path": child.relative_to(root).as_posix(),
                            "dir": is_dir,
                            "size": None if is_dir else st.st_size,
                        })
                    entries.sort(key=lambda e: (not e["dir"], e["name"].casefold()))
                    cur = "" if folder == root else folder.relative_to(root).as_posix()
                    self.send_json(HTTPStatus.OK, {"root": str(root), "path": cur, "entries": entries})
                except ValueError as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if not self.authorized():
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            route, _ = self.parse_url()
            if route == "/api/mkdir":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                    rel = data.get("path", "")
                    if not isinstance(rel, str) or not rel.strip():
                        raise ValueError("path is required")
                    target = resolve_inside(root, rel)
                    if target == root:
                        raise ValueError("cannot create root")
                    if target.exists():
                        self.send_json(HTTPStatus.CONFLICT, {"error": f"already exists: {rel}"})
                        return
                    target.mkdir(parents=True, exist_ok=False)
                    self.send_json(HTTPStatus.CREATED, {"path": target.relative_to(root).as_posix()})
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
                    target = resolve_inside(root, rel)
                    if target == root or target.is_dir():
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
                    self.send_json(HTTPStatus.CREATED, {"path": target.relative_to(root).as_posix(), "bytes": written})
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
                try:
                    target = resolve_inside(root, rel)
                    if target == root:
                        raise ValueError("cannot delete root")
                    if not target.exists():
                        self.send_json(HTTPStatus.NOT_FOUND, {"error": f"not found: {rel}"})
                        return
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                    self.send_json(HTTPStatus.OK, {"deleted": target.relative_to(root).as_posix()})
                except ValueError as e:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Zero-dependency bootstrap file server")
    parser.add_argument("--root", default="~/", help="Confined root directory (default: current directory)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8088, help="Bind port (default: 8088)")
    parser.add_argument("--token", default=os.environ.get("BOOTSTRAP_TOKEN", ""), help="API token (auto-generated if empty)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = args.token or secrets.token_urlsafe(18)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(root, token))
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
