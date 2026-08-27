#!/usr/bin/env python3
"""Validate structural invariants of a standalone async agentic demo."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


class DemoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.scripts: list[str] = []
        self._script: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "script" and not values.get("src"):
            self._script = []

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parser = DemoParser()
    parser.feed(text)
    errors: list[str] = []

    duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate IDs: {', '.join(duplicates)}")

    required_concepts = {
        "queue/case list": r"queue|case[-_ ]?(?:list|management)",
        "agent-work control": r"agent[-_ ]?work|playback|simulation",
        "human review": r"review|approve|human",
        "simulated-data notice": r"simulat(?:ed|ion)|mock(?:ed)?|demo data",
        "reduced-motion support": r"prefers-reduced-motion",
    }
    lower = text.lower()
    for label, pattern in required_concepts.items():
        if not re.search(pattern, lower):
            errors.append(f"missing {label}")

    node = shutil.which("node")
    if node and parser.scripts:
        script = "\n".join(parser.scripts)
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
            handle.write(script)
            handle.flush()
            result = subprocess.run(
                [node, "--check", handle.name], capture_output=True, text=True, check=False
            )
        if result.returncode:
            errors.append("inline JavaScript syntax error:\n" + result.stderr.strip())

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    if not args.html.is_file():
        print(f"ERROR: file not found: {args.html}", file=sys.stderr)
        return 2
    errors = validate(args.html)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
