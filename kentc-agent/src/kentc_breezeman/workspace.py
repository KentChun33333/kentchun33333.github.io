"""The workspace as the browser sees it: a folder tree, uploads and text previews, all confined to the workspace.

The agent's state folder (.kentc-agent/) is not part of the tree and not writable through uploads.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from kentc_agent.config import STATE_DIR

HIDDEN = {STATE_DIR, ".git", "__pycache__", ".DS_Store"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
PREVIEW_BYTES = 256 * 1024
_UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f/\\]")


def inside(workspace: Path, rel: str) -> Path:
    """`rel` resolved inside the workspace, outside the hidden folders; ValueError otherwise."""
    path = (workspace / rel).resolve()
    if not path.is_relative_to(workspace):
        raise ValueError(f"path outside the workspace: {rel}")
    parts = path.relative_to(workspace).parts
    if any(p in HIDDEN for p in parts):
        raise ValueError(f"path not available: {rel}")
    return path


def relative(workspace: Path, path: Path) -> str:
    return path.relative_to(workspace).as_posix()


def list_dir(workspace: Path, rel: str = "") -> list[dict[str, Any]]:
    """Direct children of a folder: folders first, then files, by name."""
    folder = inside(workspace, rel)
    if not folder.is_dir():
        raise ValueError(f"not a folder: {rel}")
    entries = []
    for child in folder.iterdir():
        if child.name in HIDDEN:
            continue
        try:
            real = child.resolve()
            if not real.is_relative_to(workspace):
                continue
            st = child.stat()
        except OSError:
            continue
        is_dir = child.is_dir()
        entries.append({"name": child.name, "path": relative(workspace, child), "dir": is_dir,
                        "size": None if is_dir else st.st_size, "mtime": st.st_mtime})
    entries.sort(key=lambda e: (not e["dir"], e["name"].casefold()))
    return entries


def safe_name(filename: str) -> str:
    name = _UNSAFE_NAME.sub("_", Path(filename.replace("\\", "/")).name).strip()
    if name in ("", ".", "..") or name in HIDDEN:
        raise ValueError(f"invalid file name: {filename!r}")
    return name


def free_path(folder: Path, name: str) -> Path:
    """`name` in `folder`, or `stem (n).suffix` when taken: uploads never overwrite."""
    path = folder / name
    stem, suffix = path.stem, path.suffix
    n = 1
    while path.exists():
        path = folder / f"{stem} ({n}){suffix}"
        n += 1
    return path


def save_upload(workspace: Path, rel_dir: str, filename: str, data: bytes) -> str:
    """Write one uploaded file into a workspace folder; -> its workspace-relative path."""
    folder = inside(workspace, rel_dir)
    if not folder.is_dir():
        raise ValueError(f"not a folder: {rel_dir}")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"{filename}: larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    name = safe_name(filename)
    while True:
        path = free_path(folder, name)
        try:
            with path.open("xb") as stream:       # exclusive: a concurrent upload of the same name gets the next one
                stream.write(data)
            return relative(workspace, path)
        except FileExistsError:
            continue


def preview(workspace: Path, rel: str) -> dict[str, Any]:
    """The start of a file as text, or only its metadata when it is binary."""
    path = inside(workspace, rel)
    if not path.is_file():
        raise ValueError(f"not a file: {rel}")
    size = path.stat().st_size
    with path.open("rb") as stream:
        head = stream.read(PREVIEW_BYTES)
    binary = b"\x00" in head[:8192]
    text = None
    if not binary:
        try:
            text = head.decode("utf-8")
        except UnicodeDecodeError as e:
            # a multi-byte character cut at the preview boundary is fine; anything else is not text
            if size > PREVIEW_BYTES and e.start >= len(head) - 3:
                text = head[:e.start].decode("utf-8")
            else:
                binary = True
    return {"path": relative(workspace, path), "name": path.name, "size": size, "binary": binary,
            "text": text, "truncated": size > PREVIEW_BYTES, "ext": os.path.splitext(path.name)[1].lower()}
