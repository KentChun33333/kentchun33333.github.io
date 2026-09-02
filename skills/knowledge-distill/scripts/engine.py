#!/usr/bin/env python3
"""
Knowledge Distill Engine: Unified CLI for Guardian, Evaluation, and Automation.

Commands:
  guard      Audit folder contract, citations, diagrams, and provenance quality gates.
  evaluate   Compute 7-dimension IQ review score, compression ratio, and duplication rate.
  scaffold   Scan raw sources, generate source-index.md, and create cooked template stubs.
  diagram    Generate standard 3-column ASCII stacking contract flow diagrams.
  manifest   Generate machine-readable knowledge/manifest.json for downstream agents.
  audit-all  Run guardian, evaluation, and manifest generation in one pipeline.
"""

import argparse
import json
import sys
from pathlib import Path

# Add script directory to sys.path for local imports
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from automation import build_knowledge_manifest, generate_ascii_diagram, scaffold_sources
from evaluator import KnowledgeEvaluator
from guardian import KnowledgeGuardian


def cmd_guard(args):
    project_dir = Path(args.project_dir)
    guardian = KnowledgeGuardian(project_dir)
    success = guardian.run_all()
    print(guardian.format_report())
    if not success and args.strict:
        sys.exit(1)


def cmd_evaluate(args):
    project_dir = Path(args.project_dir)
    evaluator = KnowledgeEvaluator(project_dir)
    evaluator.run_evaluation()
    report = evaluator.generate_iq_report()
    print(report)

    if args.write:
        out_path = project_dir / "analysis" / "iq-training-evaluation.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[Engine] Saved IQ Evaluation to: {out_path}")


def cmd_scaffold(args):
    raw_dir = Path(args.raw_dir)
    project_dir = Path(args.project_dir)
    count = scaffold_sources(raw_dir, project_dir)
    print(f"[Engine] Successfully indexed {count} source(s) into {project_dir / 'data-cooked'}")


def cmd_diagram(args):
    if args.json:
        steps_data = json.loads(args.json)
    elif args.file:
        steps_data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    elif args.input and args.module and args.output:
        steps_data = [{
            "input": args.input,
            "module": args.module,
            "output": args.output,
            "source": args.source or "",
        }]
    else:
        # Default demonstration
        steps_data = [
            {"input": "Raw Request / Config", "module": "Input Normalization", "output": "Parsed Struct", "source": "source-001"},
            {"input": "Parsed Struct", "module": "Core Transformation Engine", "output": "Verified Result", "source": "source-001, source-002"},
        ]

    diagram = generate_ascii_diagram(steps_data)
    print(diagram)


def cmd_manifest(args):
    project_dir = Path(args.project_dir)
    manifest = build_knowledge_manifest(project_dir)
    print(f"[Engine] Wrote knowledge/manifest.json ({manifest['total_knowledge_files']} artifacts indexed).")


def cmd_audit_all(args):
    project_dir = Path(args.project_dir)
    print(f"============================================================")
    print(f"1. RUNNING GUARDIAN QUALITY GATES ON: {project_dir.name}")
    print(f"============================================================")
    guardian = KnowledgeGuardian(project_dir)
    guard_success = guardian.run_all()
    print(guardian.format_report())

    print(f"\n============================================================")
    print(f"2. RUNNING 7-DIMENSION IQ EVALUATION")
    print(f"============================================================")
    evaluator = KnowledgeEvaluator(project_dir)
    evaluator.run_evaluation()
    report = evaluator.generate_iq_report()
    print(report)

    if args.write:
        out_eval = project_dir / "analysis" / "iq-training-evaluation.md"
        out_eval.parent.mkdir(parents=True, exist_ok=True)
        out_eval.write_text(report, encoding="utf-8")
        print(f"\n[Engine] Saved IQ evaluation to: {out_eval}")

    print(f"\n============================================================")
    print(f"3. COMPILING DOWNSTREAM AGENT MANIFEST")
    print(f"============================================================")
    manifest = build_knowledge_manifest(project_dir)
    print(f"[Engine] Wrote {project_dir / 'knowledge/manifest.json'} with {manifest['total_knowledge_files']} files.")

    if not guard_success and args.strict:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge Distill Automation, Guardian & Evaluation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # guard
    p_guard = subparsers.add_parser("guard", help="Audit folder contracts, citations, and quality gates")
    p_guard.add_argument("project_dir", help="Path to distillation project directory")
    p_guard.add_argument("--strict", action="store_true", help="Exit with non-zero code on failures")
    p_guard.set_defaults(func=cmd_guard)

    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="Score output on 7 IQ dimensions")
    p_eval.add_argument("project_dir", help="Path to distillation project directory")
    p_eval.add_argument("--write", action="store_true", help="Write report to analysis/iq-training-evaluation.md")
    p_eval.set_defaults(func=cmd_evaluate)

    # scaffold
    p_scaffold = subparsers.add_parser("scaffold", help="Index raw sources and create cooked stubs")
    p_scaffold.add_argument("raw_dir", help="Directory containing raw source files")
    p_scaffold.add_argument("project_dir", help="Target project root directory")
    p_scaffold.set_defaults(func=cmd_scaffold)

    # diagram
    p_diag = subparsers.add_parser("diagram", help="Generate ASCII stacking flow diagrams")
    p_diag.add_argument("--input", help="Input contract string")
    p_diag.add_argument("--module", help="Core module name")
    p_diag.add_argument("--output", help="Output contract string")
    p_diag.add_argument("--source", help="Source ID citation")
    p_diag.add_argument("--json", help="JSON string with list of step dicts")
    p_diag.add_argument("--file", help="Path to JSON file containing step dicts")
    p_diag.set_defaults(func=cmd_diagram)

    # manifest
    p_man = subparsers.add_parser("manifest", help="Build knowledge/manifest.json for downstream agents")
    p_man.add_argument("project_dir", help="Path to distillation project directory")
    p_man.set_defaults(func=cmd_manifest)

    # audit-all
    p_all = subparsers.add_parser("audit-all", help="Run guard + evaluate + manifest")
    p_all.add_argument("project_dir", help="Path to distillation project directory")
    p_all.add_argument("--write", action="store_true", help="Persist evaluation report to analysis/")
    p_all.add_argument("--strict", action="store_true", help="Exit with non-zero on failure")
    p_all.set_defaults(func=cmd_audit_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
