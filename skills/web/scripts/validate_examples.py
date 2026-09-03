#!/usr/bin/env python3
"""Deterministic preflight checks for categorized web deliverables."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path


REQUIRED = {
    "research-site": {"research-panel", "evidence"},
    "system-demo": {"flow", "next", "failure", "reset", "status"},
    "agentic-demo": {"case-state", "review", "approve", "status"},
}


class Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.tags: set[str] = set()
        self.has_viewport = False
        self.scripts: list[str] = []
        self.in_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "meta" and values.get("name") == "viewport":
            self.has_viewport = True
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_script = False

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.scripts.append(data)


def validate(path: Path, category: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parser = Inspector()
    parser.feed(text)
    errors: list[str] = []
    missing = REQUIRED[category] - set(parser.ids)
    if missing:
        errors.append(f"missing required ids: {', '.join(sorted(missing))}")
    duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate ids: {', '.join(duplicates)}")
    for token in ("html", "head", "body", "main", "script", "style", "title"):
        if token not in parser.tags:
            errors.append(f"missing <{token}>")
    if not parser.has_viewport:
        errors.append("missing viewport metadata")
    if "prefers-reduced-motion" not in text and category != "agentic-demo":
        errors.append("missing reduced-motion treatment")
    if "aria-live" not in text:
        errors.append("missing aria-live feedback")
    node = shutil.which("node")
    if node and parser.scripts:
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as script:
            script.write("\n".join(parser.scripts))
            script.flush()
            checked = subprocess.run([node, "--check", script.name], capture_output=True, text=True, check=False)
        if checked.returncode:
            errors.append(f"JavaScript syntax error: {checked.stderr.strip()}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--category", choices=sorted(REQUIRED), required=True)
    args = parser.parse_args()
    errors = validate(args.path, args.category)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {args.category} preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
