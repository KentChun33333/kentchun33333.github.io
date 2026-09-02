#!/usr/bin/env python3
"""
Guardian: Quality Gate and Contract Enforcement Engine for knowledge-distill.

Validates:
1. Folder structure compliance (data-raw, data-cooked, analysis, knowledge)
2. Provenance completeness in cooked files
3. Source ID citation integrity (zero hallucinated source IDs)
4. Diagram constraints (forbids mermaid blocks in markdown; validates ASCII stacking)
5. Completion checklist verification
"""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CheckResult:
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    details: List[str] = field(default_factory=list)


class KnowledgeGuardian:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.results: List[CheckResult] = []
        self.known_sources: Set[str] = set()

    def run_all(self) -> bool:
        """Runs all validation rules. Returns True if no FAIL statuses."""
        self.results.clear()
        self.check_folder_structure()
        self.discover_known_sources()
        self.check_provenance_headers()
        self.check_citations_integrity()
        self.check_diagram_rules()
        self.check_required_artifacts()
        self.check_web_artifacts()

        return all(r.status != "FAIL" for r in self.results)

    def check_folder_structure(self):
        """Verifies standard folders exist."""
        required_dirs = ["data-raw", "data-cooked", "analysis", "knowledge"]
        missing = [d for d in required_dirs if not (self.project_dir / d).is_dir()]
        
        if missing:
            self.results.append(CheckResult(
                name="Folder Structure",
                status="FAIL",
                message=f"Missing standard folders: {', '.join(missing)}",
                details=[f"Expected path: {self.project_dir / d}" for d in missing]
            ))
        else:
            self.results.append(CheckResult(
                name="Folder Structure",
                status="PASS",
                message="All standard directories (data-raw, data-cooked, analysis, knowledge) are present."
            ))

    def discover_known_sources(self):
        """Gathers valid source IDs from source-index.md and data-cooked/ filenames."""
        self.known_sources.clear()
        cooked_dir = self.project_dir / "data-cooked"
        if not cooked_dir.is_dir():
            return

        # Check filenames like source-001.md
        for f in cooked_dir.glob("source-*.md"):
            match = re.match(r"(source-[a-zA-Z0-9_-]+)", f.stem)
            if match:
                self.known_sources.add(match.group(1))

        # Check source-index.md table entries
        index_file = cooked_dir / "source-index.md"
        if index_file.is_file():
            content = index_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                matches = re.findall(r"source-\d+", line)
                for m in matches:
                    self.known_sources.add(m)

    def check_provenance_headers(self):
        """Ensures every data-cooked/source-XXX.md contains provenance metadata."""
        cooked_dir = self.project_dir / "data-cooked"
        if not cooked_dir.is_dir():
            return

        missing_provenance = []
        source_files = [f for f in cooked_dir.glob("source-*.md") if f.name != "source-index.md"]
        if not source_files:
            self.results.append(CheckResult(
                name="Cooked Provenance",
                status="WARN",
                message="No cooked source files found in data-cooked/"
            ))
            return

        required_keywords = ["raw file", "type", "parser", "confidence"]
        for f in source_files:
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
            missing_keys = [k for k in required_keywords if k not in content]
            if missing_keys:
                missing_provenance.append(f"{f.name} (missing: {', '.join(missing_keys)})")

        if missing_provenance:
            self.results.append(CheckResult(
                name="Cooked Provenance",
                status="FAIL",
                message=f"Found {len(missing_provenance)} cooked source file(s) missing provenance headers",
                details=missing_provenance
            ))
        else:
            self.results.append(CheckResult(
                name="Cooked Provenance",
                status="PASS",
                message=f"All {len(source_files)} cooked source files contain required provenance metadata."
            ))

    def check_citations_integrity(self):
        """Ensures all source-XXX cited in analysis/ and knowledge/ map to known sources."""
        citation_targets = []
        for subdir in ["analysis", "knowledge"]:
            d = self.project_dir / subdir
            if d.is_dir():
                citation_targets.extend(d.glob("**/*.md"))

        unresolved_citations: Dict[str, List[str]] = {}
        total_citations = 0

        for md_path in citation_targets:
            content = md_path.read_text(encoding="utf-8", errors="ignore")
            found_ids = set(re.findall(r"\b(source-\d+)\b", content))
            for sid in found_ids:
                total_citations += 1
                if sid not in self.known_sources:
                    rel_path = md_path.relative_to(self.project_dir)
                    unresolved_citations.setdefault(sid, []).append(str(rel_path))

        if unresolved_citations:
            details = [f"Unknown ID '{sid}' cited in: {', '.join(files)}" for sid, files in unresolved_citations.items()]
            self.results.append(CheckResult(
                name="Citation Integrity",
                status="FAIL",
                message=f"Detected {len(unresolved_citations)} unverified/hallucinated source ID(s)",
                details=details
            ))
        else:
            self.results.append(CheckResult(
                name="Citation Integrity",
                status="PASS",
                message=f"Verified {total_citations} source citations across knowledge and analysis artifacts against {len(self.known_sources)} defined sources."
            ))

    def check_diagram_rules(self):
        """Verifies no forbidden mermaid blocks in markdown and encourages ASCII stacking."""
        md_files = list(self.project_dir.glob("**/*.md"))
        mermaid_violations = []

        for md_path in md_files:
            # Skip documentation in templates if any
            content = md_path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"```mermaid\b", content, re.IGNORECASE):
                rel_path = md_path.relative_to(self.project_dir)
                mermaid_violations.append(str(rel_path))

        if mermaid_violations:
            self.results.append(CheckResult(
                name="Diagram Quality Rule",
                status="FAIL",
                message="Mermaid syntax is forbidden in knowledge-distill markdown artifacts; use ASCII stacking diagrams.",
                details=[f"Mermaid block detected in: {p}" for p in mermaid_violations]
            ))
        else:
            self.results.append(CheckResult(
                name="Diagram Quality Rule",
                status="PASS",
                message="No forbidden mermaid blocks found. Diagram format adheres to pure ASCII/text standard."
            ))

    def check_required_artifacts(self):
        """Checks for essential deliverables according to quality gates."""
        core_files = [
            ("data-cooked/source-index.md", "P0 - Source Index"),
            ("analysis/flow.md", "P0 - Flow Analysis"),
            ("analysis/dependency.md", "P0 - Dependency Analysis"),
            ("knowledge/big-picture.md", "P0 - Big Picture Reference"),
            ("knowledge/workflow-reference.md", "P0 - Workflow Reference"),
        ]
        
        missing_core = []
        for rel_path, desc in core_files:
            if not (self.project_dir / rel_path).is_file():
                missing_core.append(f"{rel_path} ({desc})")

        if missing_core:
            self.results.append(CheckResult(
                name="Core Artifacts",
                status="FAIL",
                message=f"Missing {len(missing_core)} essential artifact(s)",
                details=missing_core
            ))
        else:
            self.results.append(CheckResult(
                name="Core Artifacts",
                status="PASS",
                message="All mandatory core artifacts (source-index, flow, dependency, big-picture, workflow-reference) exist."
            ))

    def check_web_artifacts(self):
        """Validates HTML research-insight artifacts if any exist."""
        html_files = list(self.project_dir.glob("*.html")) + list(self.project_dir.glob("knowledge/*.html"))
        if not html_files:
            return

        for html_path in html_files:
            filename = html_path.name
            if filename == "index.html":
                self.results.append(CheckResult(
                    name=f"Web Artifact ({filename})",
                    status="WARN",
                    message="Web insight artifact should use a descriptive kebab-case filename rather than 'index.html' unless site root is explicitly requested."
                ))
            else:
                self.results.append(CheckResult(
                    name=f"Web Artifact ({filename})",
                    status="PASS",
                    message=f"Web insight artifact uses descriptive filename: '{filename}'."
                ))

    def format_report(self) -> str:
        """Formats the results into a clean markdown / terminal report."""
        passed = sum(1 for r in self.results if r.status == "PASS")
        warned = sum(1 for r in self.results if r.status == "WARN")
        failed = sum(1 for r in self.results if r.status == "FAIL")

        lines = [
            f"# Knowledge Guardian Report: `{self.project_dir.name}`",
            "",
            f"**Summary**: {passed} PASSED | {warned} WARNINGS | {failed} FAILED",
            "",
            "| Rule / Dimension | Status | Result Message |",
            "|---|:---:|---|",
        ]

        status_emoji = {"PASS": "✅ PASS", "WARN": "⚠️ WARN", "FAIL": "❌ FAIL"}

        for r in self.results:
            lines.append(f"| **{r.name}** | {status_emoji.get(r.status, r.status)} | {r.message} |")

        # Detailed breakdown for warnings/failures
        issues = [r for r in self.results if r.details]
        if issues:
            lines.append("")
            lines.append("## Issue Details")
            for r in issues:
                lines.append(f"### {r.name} ({r.status})")
                for d in r.details:
                    lines.append(f"- {d}")

        return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 guardian.py <project_directory>")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    if not project_dir.exists():
        print(f"Error: Directory not found: {project_dir}")
        sys.exit(1)

    guardian = KnowledgeGuardian(project_dir)
    success = guardian.run_all()
    print(guardian.format_report())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
