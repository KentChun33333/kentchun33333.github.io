"""Persistent user-level global memory store (`<workspace>/memory/`) with YAML frontmatter and INDEX.md."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

MEMORY_TYPES = ("fact", "pattern", "sim")
MEMORY_STATUSES = ("active", "provisional", "superseded", "archived")
MEMORY_CONFIDENCES = ("verified", "provisional")
TRACK_DIRS = ("facts", "patterns", "sim")
DEFAULT_SUBDIRS = ("facts/user", "facts/project", "patterns", "sim", "proposals", "archive")

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def today_iso() -> str:
    """Return today's ISO date string (YYYY-MM-DD)."""
    return date.today().isoformat()


def memory_hint(root_workspace: Path) -> str:
    """Return a concise instructions snippet pointing sub-agents to root `memory/INDEX.md`."""
    index_path = (Path(root_workspace).resolve() / "memory" / "INDEX.md")
    return (
        "## Global Memory\n"
        f"Shared cross-session memory index lives at `{index_path}`. "
        "When user preferences, project architecture, verified patterns, or past SIM lessons are relevant, "
        "inspect it with `read` first, then `read` or `bash` (`grep`) only the needed notes under "
        f"`{index_path.parent}`."
    )


def slugify_id(text: str, prefix: str = "") -> str:
    """Normalize a string into a safe lowercase hyphenated identifier."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:64] or "note"
    if prefix and not slug.startswith(f"{prefix}-"):
        slug = f"{prefix}-{slug}"[:72].strip("-")
    return slug


def validate_rel_path(memory_root: Path, rel_path: str) -> Path:
    """Resolve `rel_path` inside `memory_root`, rejecting traversal or non-markdown paths."""
    clean = rel_path.strip().lstrip("/")
    if not clean or "\\" in clean or not clean.endswith(".md"):
        raise ValueError(f"invalid memory relative path: {rel_path!r}")
    root = memory_root.resolve()
    target = (root / clean).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError(f"memory path escapes root: {rel_path!r}")
    return target


@dataclass
class MemoryNode:
    """Structured memory note backed by YAML frontmatter + Markdown body."""

    id: str
    type: str
    summary: str
    rel_path: str
    body: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = "active"
    confidence: str = "verified"
    verified_count: int = 1
    valid_from: str = field(default_factory=today_iso)
    valid_until: str | None = None
    superseded_by: str | None = None
    models_tested: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=today_iso)

    def __post_init__(self) -> None:
        if self.type not in MEMORY_TYPES:
            raise ValueError(f"invalid memory type: {self.type!r}")
        if self.status not in MEMORY_STATUSES:
            raise ValueError(f"invalid memory status: {self.status!r}")
        if self.confidence not in MEMORY_CONFIDENCES:
            raise ValueError(f"invalid memory confidence: {self.confidence!r}")
        self.summary = " ".join(self.summary.split())[:160]
        if not self.summary:
            raise ValueError("memory summary cannot be empty")
        if not self.id or not _SLUG_RE.match(self.id):
            self.id = slugify_id(self.id or Path(self.rel_path).stem, prefix=self.type)

    def frontmatter_dict(self) -> dict[str, Any]:
        """Serialize frontmatter fields in a stable order."""
        return {
            "id": self.id,
            "type": self.type,
            "summary": self.summary,
            "tags": list(self.tags),
            "status": self.status,
            "confidence": self.confidence,
            "verified_count": int(self.verified_count),
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "superseded_by": self.superseded_by,
            "models_tested": list(self.models_tested),
            "related": list(self.related),
            "updated_at": self.updated_at,
        }

    def to_markdown(self) -> str:
        """Render the node as YAML frontmatter followed by Markdown body."""
        header = yaml.safe_dump(self.frontmatter_dict(), sort_keys=False, allow_unicode=True).strip()
        body = self.body.strip()
        return f"---\n{header}\n---\n\n{body}\n" if body else f"---\n{header}\n---\n"


def parse_memory_markdown(raw: str, rel_path: str) -> MemoryNode:
    """Parse a Markdown file with YAML frontmatter into a `MemoryNode`."""
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(f"missing YAML frontmatter in {rel_path}")
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict):
        raise ValueError(f"invalid YAML frontmatter in {rel_path}")
    body = match.group(2).strip()
    return MemoryNode(
        id=str(meta.get("id") or Path(rel_path).stem),
        type=str(meta["type"]),
        summary=str(meta["summary"]),
        rel_path=rel_path,
        body=body,
        tags=[str(t) for t in (meta.get("tags") or [])],
        status=str(meta.get("status") or "active"),
        confidence=str(meta.get("confidence") or "verified"),
        verified_count=int(meta.get("verified_count") or 1),
        valid_from=str(meta.get("valid_from") or today_iso()),
        valid_until=str(meta["valid_until"]) if meta.get("valid_until") else None,
        superseded_by=str(meta["superseded_by"]) if meta.get("superseded_by") else None,
        models_tested=[str(m) for m in (meta.get("models_tested") or [])],
        related=[str(r) for r in (meta.get("related") or [])],
        updated_at=str(meta.get("updated_at") or today_iso()),
    )


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


class MemoryStore:
    """Manages `<init_workspace>/memory/` nodes, `.dream_state.json`, and `INDEX.md`."""

    def __init__(self, memory_root: Path) -> None:
        self.root = Path(memory_root).resolve()
        self.index_path = self.root / "INDEX.md"
        self.state_path = self.root / ".dream_state.json"

    def ensure_layout(self) -> None:
        """Create the standard directory layout under `<init_workspace>/memory/`."""
        for sub in DEFAULT_SUBDIRS:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def read_node(self, rel_path: str) -> MemoryNode:
        """Read and parse a single memory node by relative path."""
        target = validate_rel_path(self.root, rel_path)
        return parse_memory_markdown(target.read_text(encoding="utf-8"), rel_path)

    def write_node(self, node: MemoryNode) -> Path:
        """Atomically write a `MemoryNode` to disk."""
        target = validate_rel_path(self.root, node.rel_path)
        _atomic_write(target, node.to_markdown())
        return target

    def list_nodes(self, *, statuses: set[str] | None = None, tracks: tuple[str, ...] = TRACK_DIRS) -> list[MemoryNode]:
        """List valid memory nodes across `tracks`, optionally filtered by status."""
        nodes: list[MemoryNode] = []
        for track in tracks:
            base = self.root / track
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*.md")):
                rel = path.relative_to(self.root).as_posix()
                try:
                    node = parse_memory_markdown(path.read_text(encoding="utf-8"), rel)
                except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
                    continue
                if statuses is None or node.status in statuses:
                    nodes.append(node)
        return nodes

    def archive_node(self, rel_path: str) -> str:
        """Move a node into `archive/<rel_path>` and mark its status as `archived`."""
        node = self.read_node(rel_path)
        src = validate_rel_path(self.root, rel_path)
        clean_rel = rel_path.strip().lstrip("/")
        if clean_rel.startswith("archive/"):
            return clean_rel
        arch_rel = f"archive/{clean_rel}"
        node.status = "archived"
        node.rel_path = arch_rel
        node.updated_at = today_iso()
        self.write_node(node)
        if src.is_file():
            src.unlink()
        return arch_rel

    def rebuild_index(self, *, last_dreamed: str | None = None) -> Path:
        """Deterministically regenerate `INDEX.md` from active and provisional nodes."""
        self.ensure_layout()
        nodes = self.list_nodes(statuses={"active", "provisional"})
        by_type: dict[str, list[MemoryNode]] = {t: [] for t in MEMORY_TYPES}
        for node in nodes:
            by_type.setdefault(node.type, []).append(node)

        stamp = last_dreamed or today_iso()
        lines = [
            "# Global Memory Index",
            f"> Last dreamed: {stamp} | Active/Provisional nodes: {len(nodes)}",
            "",
        ]
        sections = (
            ("fact", "Facts"),
            ("pattern", "Patterns"),
            ("sim", "SIM (Strategy & Pitfalls)"),
        )
        for kind, title in sections:
            lines.append(f"## {title}")
            items = sorted(by_type.get(kind, []), key=lambda n: (n.status != "active", n.id))
            if not items:
                lines.append("- *(none)*")
            else:
                for node in items:
                    badge = f"{node.status}, {node.confidence}"
                    if node.type == "pattern":
                        badge += f", verified_count: {node.verified_count}"
                    lines.append(
                        f"- [{node.id}]({node.rel_path}) — {node.summary} "
                        f"({badge}, updated: {node.updated_at})"
                    )
            lines.append("")

        _atomic_write(self.index_path, "\n".join(lines).rstrip() + "\n")
        return self.index_path

    def read_dream_state(self) -> dict[str, Any]:
        """Load `.dream_state.json` with safe defaults."""
        default: dict[str, Any] = {
            "sessions": {},
            "schedule": {
                "enabled": False,
                "interval_min": 60.0,
                "last_run": None,
                "next_run": None,
                "last_summary": None,
                "last_error": None,
            },
        }
        if not self.state_path.is_file():
            return default
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(data, dict):
            return default
        sessions = data.get("sessions") if isinstance(data.get("sessions"), dict) else {}
        sched = dict(default["schedule"])
        if isinstance(data.get("schedule"), dict):
            sched.update(data["schedule"])
        return {"sessions": sessions, "schedule": sched}

    def write_dream_state(self, state: dict[str, Any]) -> None:
        """Atomically persist `.dream_state.json`."""
        self.ensure_layout()
        _atomic_write(self.state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
