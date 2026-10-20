"""The TER report: the report agent's JSON -> markdown (print, export) and HTML."""

from __future__ import annotations

import re
from html import escape
from typing import Any

import markdown as md


def _t(v: Any) -> str:
    if isinstance(v, list):
        return "; ".join(_t(x) for x in v)
    if isinstance(v, dict):
        return " · ".join(_t(x) for x in v.values() if x)
    return "" if v is None else str(v).replace("|", "\\|").replace("\n", " ")


def to_markdown(case: dict[str, Any], r: dict[str, Any], version: int) -> str:
    trig, bg, rec = r.get("trigger") or {}, r.get("background") or {}, r.get("recommendation") or {}
    out = [f"# Trigger Event Report - {_t(r.get('title')) or case['customer'] or case['id']}",
           f"**Case** {case['id']} · **CIF** {case['cif']} · **Version** v{version} · CONFIDENTIAL  ",
           f"*{_t(r.get('typology'))}*" if r.get("typology") else "",
           "", "## Executive narrative", _t(r.get("executive_narrative")),
           "", "## Trigger", "| | |", "|---|---|",
           f"| Trigger type | {_t(trig.get('type'))} |", f"| Trigger event | {_t(trig.get('event'))} |",
           f"| Primary discrepancy | {_t(trig.get('primary_discrepancy'))} |",
           f"| Context gap | {_t(trig.get('context_gap'))} |",
           "", "## Background", "| | |", "|---|---|"]
    for k, label in (("entity", "Entity"), ("nature_of_business", "Nature of business"), ("accounts", "Accounts"),
                     ("owners_directors", "Directors / UBO"), ("expected_activity", "Expected activity"),
                     ("major_counterparty", "Major counterparty")):
        out.append(f"| {label} | {_t(bg.get(k))} |")
    out += ["", "## Review", "### KYC review", _t(r.get("kyc_review")), "", "### Transaction review"]
    tx = r.get("transactions") or []
    if tx:
        out += ["| Date | From | To | Amount | Review result |", "|---|---|---|---|---|"]
        out += [f"| {_t(t.get('date'))} | {_t(t.get('from'))} | {_t(t.get('to'))} | {_t(t.get('amount'))} | "
                f"{_t(t.get('result'))} |" for t in tx if isinstance(t, dict)]
    out += ["", "## Justification and key risks"]
    for k in sorted((x for x in r.get("key_risks") or [] if isinstance(x, dict)),
                    key=lambda x: -float(x.get("score") or 0)):
        out += [f"### {_t(k.get('id'))} · {_t(k.get('title'))} (score {_t(k.get('score'))})", _t(k.get("reason")),
                f"- **Evidence:** {_t(k.get('evidence'))}" if k.get("evidence") else "",
                f"- **Gap:** {_t(k.get('gap'))}" if k.get("gap") else "", ""]
    out += ["## Recommended next step", f"**{_t(rec.get('next_step'))}** - {_t(rec.get('scope'))}",
            "", _t(rec.get("rationale"))]
    if r.get("document_requests"):
        out += ["", "## Documents to request from the client"]
        out += [f"- **{_t(d.get('document'))}** - {_t(d.get('reason'))}" for d in r["document_requests"]
                if isinstance(d, dict)]
    if r.get("open_questions"):
        out += ["", "## Open questions"] + [f"- {_t(q)}" for q in r["open_questions"]]
    if r.get("changes"):
        out += ["", f"*Changes in this version: {_t(r['changes'])}*"]
    return "\n".join(out).replace("\n\n\n", "\n\n") + "\n"


def to_html(text: str) -> str:
    """Render markdown to HTML, never allowing agent-authored raw HTML or script URLs.

    The report is written by an external agent: escape its input before markdown so inline HTML stays text,
    then drop javascript:/data: links, which markdown itself would otherwise pass through.
    """
    html = md.markdown(escape(text, quote=False), extensions=["tables", "sane_lists"])
    return re.sub(r'(?i)(href|src)="(?:javascript|data|vbscript):[^"]*"', r'\1="#"', html)
