"""Report rendering: an app's view of an agent result -> markdown (print, export), and markdown -> safe HTML.

The browser renders the same views with the same blocks (web/assets/js/app.js `renderBlocks`)."""

from __future__ import annotations

import re
from html import escape
from typing import TYPE_CHECKING, Any

import markdown as md

from .apps import block_kind, humanize

if TYPE_CHECKING:
    from .apps import App


def get(data: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def text(v: Any) -> str:
    if isinstance(v, list):
        return "; ".join(t for t in (text(x) for x in v) if t)
    if isinstance(v, dict):
        return " · ".join(t for t in (text(x) for x in v.values()) if t)
    return "" if v is None else str(v)


def cell(v: Any) -> str:
    return text(v).replace("|", "\\|").replace("\n", " ")


def _columns(block: dict[str, Any], rows: list[Any]) -> list[tuple[str, str]]:
    cols = block.get("columns")
    if isinstance(cols, dict):
        return [(k, str(v)) for k, v in cols.items()]
    keys = list(cols) if cols else list(next((r for r in rows if isinstance(r, dict)), {}))
    return [(k, humanize(k)) for k in keys]


def _table(head: list[str], rows: list[list[Any]]) -> list[str]:
    return ["| " + " | ".join(cell(h) for h in head) + " |", "|" + "---|" * len(head)] + \
        ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]


def view_markdown(view: list[dict[str, Any]], data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for block in view:
        kind = block_kind(block)
        path = block[kind]
        if block.get("title"):
            out += ["", f"## {block['title']}"]
        labels = block.get("labels") or {}
        if kind == "kv":
            pairs = [(labels.get(p) or humanize(p), get(data, p)) for p in path] if isinstance(path, list) else \
                [(labels.get(k) or humanize(k), v) for k, v in (get(data, path) or {}).items()] \
                if isinstance(get(data, path), dict) else []
            out += ["", *_table(["", ""], [[f"**{k}**", v] for k, v in pairs])] if pairs else []
            continue
        value = get(data, path)
        if kind == "text":
            out += ["", text(value)]
            continue
        rows = value if isinstance(value, list) else []
        if not rows:
            out += ["", "—"]
        elif kind in ("list", "chips"):
            out += [""] + [f"- {text(x)}" for x in rows]
        elif kind == "table":
            cols = _columns(block, rows)
            out += ["", *_table([c[1] for c in cols], [[r.get(k) if isinstance(r, dict) else r for k, _ in cols]
                                                          for r in rows])]
        elif kind == "facts":
            out += ["", *_table(["Field", "Value", "Location", "Confidence"],
                                [[r.get("field"), r.get("value"), r.get("location"), r.get("confidence")]
                                 for r in rows if isinstance(r, dict)])]
        else:                                                # cards
            score = block.get("score")
            items = [r for r in rows if isinstance(r, dict)]
            if score:
                items.sort(key=lambda r: -_num(r.get(score)))
            for r in items:
                kicker = f"{text(r.get(block['kicker']))} · " if block.get("kicker") else ""
                head = text(r.get(block["head"])) if block.get("head") else ""
                out += ["", f"### {kicker}{head}" + (f" (score {text(r.get(score))})" if score else "")]
                if block.get("body"):
                    out.append(text(r.get(block["body"])))
                out += [f"- **{humanize(n)}:** {text(r.get(n))}" for n in block.get("notes") or [] if r.get(n)]
    return out


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def to_markdown(app: App, case_id: str, fields: dict[str, str], r: dict[str, Any], version: int) -> str:
    rep = app.report
    shown = [f"**{f.label}** {fields[f.name]}" for f in app.spec.fields
             if f.column and fields.get(f.name)]
    out = [f"# {rep.name} - {text(r.get('title')) or case_id}",
           " · ".join([f"**Case** {case_id}", *shown, f"**Version** v{version}"]) + "  ",
           f"**Verdict:** {text(r.get('verdict'))}" if r.get("verdict") else ""]
    out += view_markdown(rep.view, r)
    reqs = [x for x in r.get("requests") or [] if isinstance(x, dict)]
    if reqs:
        out += ["", "## Documents requested"] + [f"- **{text(x.get('document'))}** - {text(x.get('reason'))}"
                                                 for x in reqs]
    if r.get("questions"):
        out += ["", "## Open questions"] + [f"- {text(q)}" for q in r["questions"]]
    if r.get("reply"):
        out += ["", f"*Agent reply: {text(r['reply'])}*"]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)) + "\n"


def to_html(text_md: str) -> str:
    """Render markdown to HTML, never allowing agent-authored raw HTML or script URLs.

    The report is written by an agent: escape its input before markdown so inline HTML stays text, then drop
    javascript:/data: links, which markdown itself would otherwise pass through.
    """
    html = md.markdown(escape(text_md, quote=False), extensions=["tables", "sane_lists"])
    return re.sub(r'(?i)(href|src)="(?:javascript|data|vbscript):[^"]*"', r'\1="#"', html)
