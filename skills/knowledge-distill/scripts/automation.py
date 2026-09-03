#!/usr/bin/env python3
"""
Automation: Scaffolding, Diagram Generation, and Manifest Builder for knowledge-distill.

Capabilities:
1. Source Scaffolding: Ingests raw inputs, generates source-index.md and cooked stubs with provenance.
2. ASCII Contract Diagram Generator: Produces aligned 3-column stacking flow diagrams.
3. Knowledge Manifest Builder: Compiles knowledge/manifest.json for downstream agent consumption.
"""

import json
import hashlib
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


PARSER_STRATEGY_MAP = {
    ".pdf": "pdf-text-extract (fallback OCR if scanned)",
    ".png": "vision-description-ocr",
    ".jpg": "vision-description-ocr",
    ".jpeg": "vision-description-ocr",
    ".csv": "csv-profile-markdown-table",
    ".xlsx": "xlsx-sheet-summary-tables",
    ".docx": "docx-to-markdown",
    ".sql": "sql-schema-structural-summary",
    ".py": "python-ast-interface-extract",
    ".ts": "typescript-interface-extract",
    ".js": "javascript-module-extract",
    ".json": "json-schema-summary",
    ".md": "markdown-normalization",
    ".txt": "text-normalization",
}


def scaffold_sources(raw_dir: Path, project_dir: Path) -> int:
    """Scans raw_dir, assigns IDs, creates data-cooked/source-index.md and source-XXX.md stubs."""
    raw_dir = Path(raw_dir).resolve()
    project_dir = Path(project_dir).resolve()
    cooked_dir = project_dir / "data-cooked"
    analysis_dir = project_dir / "analysis"
    knowledge_dir = project_dir / "knowledge"

    cooked_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    raw_files = [f for f in sorted(raw_dir.rglob("*")) if f.is_file() and not f.name.startswith(".")]
    today_str = date.today().isoformat()

    index_rows = [
        "# Source Index",
        "",
        "| Source ID | Raw Path | Type | Size | Parse Strategy | Notes |",
        "|---|---|---:|---:|---|---|",
    ]

    count = 0
    for idx, fpath in enumerate(raw_files, start=1):
        source_id = f"source-{idx:03d}"
        rel_raw = fpath.relative_to(project_dir) if project_dir in fpath.parents else fpath.name
        ext = fpath.suffix.lower()
        strategy = PARSER_STRATEGY_MAP.get(ext, "plain-text-normalization")
        size_kb = max(1, round(fpath.stat().st_size / 1024))
        type_label = ext.lstrip(".").upper() or "TEXT"

        index_rows.append(
            f"| {source_id} | `{rel_raw}` | {type_label} | {size_kb} KB | {strategy} | Pending cook |"
        )

        # Create cooked stub if it doesn't already exist
        cooked_stub = cooked_dir / f"{source_id}.md"
        if not cooked_stub.exists():
            stub_content = f"""# Cooked Source: {source_id}

- Raw file: `{rel_raw}`
- Type: {type_label}
- Parser: {strategy}
- Parsed at: {today_str}
- Confidence: high
- Notes: Initial extracted draft.

---

## 1. Summary

<!-- Insert extracted content, structural outline, and key definitions here -->

"""
            cooked_stub.write_text(stub_content, encoding="utf-8")
        count += 1

    (cooked_dir / "source-index.md").write_text("\n".join(index_rows) + "\n", encoding="utf-8")
    return count


def generate_ascii_diagram(
    steps: List[Dict[str, str]],
    input_w: int = 26,
    module_w: int = 26,
    output_w: int = 34
) -> str:
    """Formats steps into standard 3-column stacking flow diagram."""
    col1_title = "[Input Data Contract]"
    col2_title = "[Core Module]"
    col3_title = "[Output Data Contract]"

    sep1 = "=" * len(col1_title)
    sep2 = "=" * len(col2_title)
    sep3 = "=" * len(col3_title)

    lines = [
        f"{col1_title:<{input_w}}       {col2_title:^{module_w}}       {col3_title}",
        f"{sep1:<{input_w}}       {sep2:^{module_w}}       {sep3}",
    ]

    for step in steps:
        inp = step.get("input", "")
        mod = step.get("module", "")
        out = step.get("output", "")
        src = step.get("source", "")

        # Main step line
        lines.append(f"{inp:<{input_w}}  -->  {mod:^{module_w}}  -->  {out}")
        # Secondary provenance line if present
        if src:
            src_str = f"({src if 'Source:' in src else 'Source: ' + src})"
            lines.append(f"{'':<{input_w}}       {'':^{module_w}}       {src_str}")
        lines.append("")

    return "```text\n" + "\n".join(lines).rstrip() + "\n```"


def build_knowledge_manifest(project_dir: Path) -> Dict[str, Any]:
    """Scans knowledge/ and compiles a machine-readable manifest.json for agent consumers."""
    project_dir = Path(project_dir).resolve()
    knowledge_dir = project_dir / "knowledge"
    cooked_dir = project_dir / "data-cooked"

    manifest: Dict[str, Any] = {
        "schema_version": 2,
        "project_name": project_dir.name,
        "entrypoint": "knowledge/big-picture.md" if (knowledge_dir / "big-picture.md").exists() else "knowledge/read-order.md",
        "artifacts": [],
        "sources": [],
        "total_knowledge_files": 0,
        "task_contract": None,
        "deliverables": [],
    }

    task_contract = project_dir / "task-config.resolved.json"
    if task_contract.exists():
        try:
            contract = json.loads(task_contract.read_text(encoding="utf-8"))
            manifest["task_contract"] = str(task_contract.relative_to(project_dir))
            manifest["input_fingerprint"] = contract.get("input_fingerprint")
            manifest["objective"] = contract.get("objective")
            manifest["audience"] = contract.get("audience")
            manifest["deliverables"] = contract.get("deliverables", [])
        except (OSError, json.JSONDecodeError):
            manifest["task_contract"] = "invalid"

    if cooked_dir.is_dir():
        for sf in sorted(cooked_dir.glob("source-*.md")):
            manifest["sources"].append(sf.stem)

    if knowledge_dir.is_dir():
        for kf in sorted(knowledge_dir.glob("**/*.md")):
            rel = str(kf.relative_to(project_dir))
            content = kf.read_text(encoding="utf-8", errors="ignore")
            word_count = len(content.split())
            citations = sorted(list(set(re.findall(r"\b(source-\d+)\b", content))))

            # Extract first heading
            heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = heading_match.group(1) if heading_match else kf.stem

            manifest["artifacts"].append({
                "path": rel,
                "title": title,
                "approx_words": word_count,
                "citations": citations,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            })

        manifest["total_knowledge_files"] = len(manifest["artifacts"])

    out_file = knowledge_dir / "manifest.json"
    out_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 automation.py <scaffold|diagram|manifest> [options]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "scaffold":
        if len(sys.argv) < 4:
            print("Usage: python3 automation.py scaffold <raw_dir> <project_dir>")
            sys.exit(1)
        raw_p = Path(sys.argv[2])
        proj_p = Path(sys.argv[3])
        n = scaffold_sources(raw_p, proj_p)
        print(f"[Automation] Scaffolding complete: indexed {n} raw files into {proj_p / 'data-cooked'}")

    elif cmd == "manifest":
        if len(sys.argv) < 3:
            print("Usage: python3 automation.py manifest <project_dir>")
            sys.exit(1)
        proj_p = Path(sys.argv[2])
        m = build_knowledge_manifest(proj_p)
        print(f"[Automation] Manifest created at {proj_p / 'knowledge/manifest.json'} with {m['total_knowledge_files']} artifacts.")

    elif cmd == "diagram":
        # Interactive / demo CLI mode
        sample_steps = [
            {"input": "Cart ID, User ID", "module": "Checkout Initialization", "output": "Session Token (15m lease)", "source": "source-001"},
            {"input": "Cart Items, Session Token", "module": "Inventory Reservation", "output": "Inventory Holds Created", "source": "source-001, source-004"},
            {"input": "Payment Method, Token", "module": "Payment Processing", "output": "Gateway Transaction ID", "source": "source-001, source-002"},
        ]
        diag = generate_ascii_diagram(sample_steps)
        print(diag)


if __name__ == "__main__":
    main()
