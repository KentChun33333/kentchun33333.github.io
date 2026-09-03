#!/usr/bin/env python3
"""
Unit tests for knowledge-distill code engine (guardian, evaluator, automation).
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
import sys
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from automation import build_knowledge_manifest, generate_ascii_diagram, scaffold_sources
from evaluator import KnowledgeEvaluator
from guardian import KnowledgeGuardian


class TestKnowledgeDistillEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_mock_project(self):
        """Builds a compliant sample project structure."""
        raw_dir = self.test_dir / "data-raw"
        cooked_dir = self.test_dir / "data-cooked"
        analysis_dir = self.test_dir / "analysis"
        knowledge_dir = self.test_dir / "knowledge"

        for d in [raw_dir, cooked_dir, analysis_dir, knowledge_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Raw file
        (raw_dir / "spec.pdf").write_text("Dummy binary content")

        # Source index
        (cooked_dir / "source-index.md").write_text(
            "# Source Index\n\n| Source ID | Raw Path | Type | Size | Parse Strategy | Notes |\n|---|---|---|---|---|---|\n| source-001 | data-raw/spec.pdf | PDF | 10 KB | pdf-text-extract | High |\n"
        )

        # Cooked source
        (cooked_dir / "source-001.md").write_text(
            "# Cooked Source: source-001\n\n- Raw file: `data-raw/spec.pdf`\n- Type: PDF\n- Parser: pdf-text-extract\n- Parsed at: 2026-09-02\n- Confidence: high\n\n## Summary\nCheckout initializes with session."
        )

        # Analysis
        (analysis_dir / "flow.md").write_text(
            "# Flow Analysis\n\nSequence of stages:\n1. Init -> Token (source-001)\n"
        )
        (analysis_dir / "dependency.md").write_text(
            "# Dependency Analysis\n\n- Payment Gateway -> Inventory (source-001)\n"
        )

        # Knowledge
        (knowledge_dir / "big-picture.md").write_text(
            "# Big Picture\n\nPlatform overview. (source-001)"
        )
        (knowledge_dir / "workflow-reference.md").write_text(
            "# Workflow Reference\n\n```text\n[Input Data Contract]  -->  [Core Module]  -->  [Output Data Contract]\nCart ID, User ID      -->  Checkout Init   -->  Session Token\n                                                (Source: source-001)\n```\n\nBoundaries & Constraints:\nSession expires after 15 minutes. (source-001)\n"
        )

    def test_scaffolding(self):
        raw_dir = self.test_dir / "data-raw"
        raw_dir.mkdir()
        (raw_dir / "api.json").write_text("{}")
        (raw_dir / "flowchart.png").write_text("fake_png")

        count = scaffold_sources(raw_dir, self.test_dir)
        self.assertEqual(count, 2)
        self.assertTrue((self.test_dir / "data-cooked/source-index.md").is_file())
        self.assertTrue((self.test_dir / "data-cooked/source-001.md").is_file())
        self.assertTrue((self.test_dir / "data-cooked/source-002.md").is_file())

    def test_diagram_generator(self):
        steps = [
            {"input": "Req", "module": "Handler", "output": "Resp", "source": "source-001"}
        ]
        diag = generate_ascii_diagram(steps)
        self.assertIn("[Input Data Contract]", diag)
        self.assertIn("[Core Module]", diag)
        self.assertIn("[Output Data Contract]", diag)
        self.assertIn("Req", diag)
        self.assertIn("Handler", diag)

    def test_manifest_builder(self):
        self._create_mock_project()
        (self.test_dir / "task-config.resolved.json").write_text(
            json.dumps(
                {
                    "objective": "Explain checkout",
                    "audience": "Maintainers",
                    "input_fingerprint": "abc123",
                    "deliverables": [{"id": "demo", "type": "system-demo"}],
                }
            )
        )
        manifest = build_knowledge_manifest(self.test_dir)
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["total_knowledge_files"], 2)
        self.assertIn("source-001", manifest["sources"])
        self.assertEqual(manifest["input_fingerprint"], "abc123")
        self.assertEqual(manifest["deliverables"][0]["type"], "system-demo")
        self.assertTrue(manifest["artifacts"][0]["content_sha256"])
        self.assertTrue((self.test_dir / "knowledge/manifest.json").is_file())

    def test_guardian_passes_valid_project(self):
        self._create_mock_project()
        guardian = KnowledgeGuardian(self.test_dir)
        success = guardian.run_all()
        self.assertTrue(success, f"Guardian failed: {guardian.format_report()}")

    def test_guardian_catches_hallucinated_citation(self):
        self._create_mock_project()
        # Inject unverified citation
        (self.test_dir / "knowledge/workflow-reference.md").write_text(
            "# Workflow\nRefers to non-existent source-999"
        )
        guardian = KnowledgeGuardian(self.test_dir)
        success = guardian.run_all()
        self.assertFalse(success)
        self.assertTrue(any("source-999" in str(r.details) for r in guardian.results))

    def test_guardian_catches_forbidden_mermaid(self):
        self._create_mock_project()
        # Inject forbidden mermaid block
        (self.test_dir / "knowledge/workflow-reference.md").write_text(
            "# Workflow\n```mermaid\ngraph TD;\nA-->B;\n```"
        )
        guardian = KnowledgeGuardian(self.test_dir)
        success = guardian.run_all()
        self.assertFalse(success)
        self.assertTrue(any(r.name == "Diagram Quality Rule" and r.status == "FAIL" for r in guardian.results))

    def test_evaluator_scoring(self):
        self._create_mock_project()
        evaluator = KnowledgeEvaluator(self.test_dir)
        scores = evaluator.run_evaluation()
        self.assertEqual(len(scores), 7)
        report = evaluator.generate_iq_report()
        self.assertIn("IQ Composite Score", report)


if __name__ == "__main__":
    unittest.main()
