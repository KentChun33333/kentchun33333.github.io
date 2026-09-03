#!/usr/bin/env python3
"""Create, resolve, validate, and route Knowledge Distill task contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REGISTRY_PATH = HERE.parent / "reference" / "deliverable-registry.json"
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".php", ".swift", ".kt", ".scala", ".cs", ".sql", ".tf"}
DOC_SUFFIXES = {".md", ".mdx", ".txt", ".rst", ".pdf", ".docx", ".html"}
IGNORED_DIRS = {".git", ".cache", "node_modules", "graphify-out", "__pycache__"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def registry() -> dict[str, Any]:
    return load_json(REGISTRY_PATH)


def resolve(contract: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(contract))
    known = registry()
    for deliverable in result.get("deliverables", []):
        if not isinstance(deliverable, dict):
            continue
        kind = deliverable.get("type")
        spec = known.get(kind)
        if not spec:
            continue
        deliverable.setdefault("skill", spec["skill"])
        evaluation = deliverable.setdefault("evaluation", {})
        evaluation.setdefault("skill", spec["evaluation_skill"])
        evaluation.setdefault("profile", spec["evaluation_profile"])
        evaluation.setdefault("rules", [])
        requirements = deliverable.setdefault("requirements", {})
        for key in ("claims", "functions", "observable_effects"):
            requirements.setdefault(key, [])
    preparation = result.setdefault("preparation", {})
    preparation.setdefault("strategy", "auto")
    preparation.setdefault("graphify", "detect")
    preparation.setdefault("semantic_retrieval", "auto")
    result.setdefault("knowledge_package", "knowledge/manifest.json")
    return result


def input_files(paths: list[str], base: Path) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = (base / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and not any(part in IGNORED_DIRS for part in candidate.relative_to(path).parts)
            )
    return sorted(set(files))


def attach_input_fingerprint(contract: dict[str, Any], base: Path) -> dict[str, Any]:
    files = input_files(list(contract.get("input_data") or []), base)
    if not files:
        return contract
    digest = hashlib.sha256()
    for path in files:
        try:
            label = path.relative_to(base.resolve()).as_posix()
        except ValueError:
            label = str(path)
        digest.update(label.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    contract["input_fingerprint"] = digest.hexdigest()
    return contract


def validate(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    known = registry()
    for field in ("input_data", "objective", "audience", "deliverables"):
        if not contract.get(field):
            errors.append(f"missing required field: {field}")
    if contract.get("version") != 1:
        errors.append("version must be 1")
    ids: set[str] = set()
    outputs: set[str] = set()
    for index, item in enumerate(contract.get("deliverables") or []):
        prefix = f"deliverables[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        kind = item.get("type")
        if kind not in known:
            errors.append(f"{prefix}.type is unsupported: {kind!r}")
        for field in ("id", "output_path", "skill"):
            if not item.get(field):
                errors.append(f"{prefix}.{field} is required")
        if item.get("id") in ids:
            errors.append(f"duplicate deliverable id: {item.get('id')}")
        ids.add(str(item.get("id")))
        if item.get("output_path") in outputs:
            errors.append(f"duplicate output path: {item.get('output_path')}")
        outputs.add(str(item.get("output_path")))
        evaluation = item.get("evaluation") or {}
        if not evaluation.get("skill") or not evaluation.get("profile"):
            errors.append(f"{prefix}.evaluation requires skill and profile")
        if kind in known and item.get("skill") != known[kind]["skill"]:
            errors.append(f"{prefix}.skill must be {known[kind]['skill']!r} for {kind}")
        if kind in known:
            suffix = Path(str(item.get("output_path") or "")).suffix
            if suffix not in known[kind]["extensions"]:
                errors.append(f"{prefix}.output_path has unsupported extension {suffix!r}")
    prep = contract.get("preparation") or {}
    if prep.get("graphify", "detect") not in {"detect", "off", "required"}:
        errors.append("preparation.graphify must be detect, off, or required")
    if prep.get("semantic_retrieval", "auto") not in {"auto", "off", "required"}:
        errors.append("preparation.semantic_retrieval must be auto, off, or required")
    if prep.get("graphify") == "required" and shutil.which("graphify") is None:
        errors.append("Graphify is required but the graphify command is unavailable")
    return errors


def inventory(paths: list[str], base: Path) -> dict[str, Any]:
    files = input_files(paths, base)
    code = sum(path.suffix.lower() in CODE_SUFFIXES for path in files)
    docs = sum(path.suffix.lower() in DOC_SUFFIXES for path in files)
    size = sum(path.stat().st_size for path in files)
    return {"files": len(files), "code_files": code, "document_files": docs, "bytes": size}


def route(contract: dict[str, Any], base: Path) -> dict[str, Any]:
    stats = inventory(list(contract.get("input_data") or []), base)
    prep = contract.get("preparation") or {}
    graphify_mode = prep.get("graphify", "detect")
    installed = shutil.which("graphify") is not None
    relationship_heavy = stats["code_files"] >= 50 or (stats["code_files"] >= 20 and stats["document_files"] >= 5)
    use_graphify = graphify_mode == "required" or (graphify_mode == "detect" and installed and relationship_heavy)
    semantic_mode = prep.get("semantic_retrieval", "auto")
    use_semantic = semantic_mode == "required" or (semantic_mode == "auto" and stats["bytes"] >= 1_000_000)
    return {
        "inventory": stats,
        "graphify_available": installed,
        "use_graphify": use_graphify,
        "use_semantic_retrieval": use_semantic,
        "strategy": "graphify-assisted" if use_graphify else "native-distillation",
        "reasons": [
            "Graphify available" if installed else "Graphify unavailable; no installation attempted",
            "relationship-heavy input" if relationship_heavy else "input below relationship-heavy heuristic",
            "large corpus" if stats["bytes"] >= 1_000_000 else "corpus below semantic-retrieval heuristic",
        ],
        "heuristics_are_overridable": True,
    }


VALID_FAILURE_OWNERS = {"skill", "routing", "tool", "data", "model", "evaluator", "spec", "noise"}
VALID_INTERVENTIONS = {"clarify", "revise-skill", "repair-other", "retain"}


def load_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            value = yaml.safe_load(text)
        except ImportError:
            # Fallback if PyYAML unavailable
            value = json.loads(text)
    else:
        value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a dictionary/object")
    return value


def validate_change_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(contract, dict):
        return ["change contract must be an object"]
    if contract.get("version") != 1:
        errors.append("version must be 1")
    if not contract.get("skill_name") or not isinstance(contract.get("skill_name"), str):
        errors.append("skill_name must be a non-empty string")

    owner = contract.get("failure_owner")
    if not owner or owner not in VALID_FAILURE_OWNERS:
        errors.append(f"failure_owner must be one of {sorted(VALID_FAILURE_OWNERS)}; got {owner!r}")

    intervention = contract.get("intervention")
    if intervention and intervention not in VALID_INTERVENTIONS:
        errors.append(f"intervention must be one of {sorted(VALID_INTERVENTIONS)}; got {intervention!r}")

    if owner and owner != "skill" and intervention == "revise-skill":
        errors.append(f"failure_owner is {owner!r}; non-skill defects must not use intervention 'revise-skill'")

    problem = contract.get("problem")
    if not isinstance(problem, dict):
        errors.append("problem must be an object")
    else:
        for field in ("observed_behavior", "suspected_cause"):
            if not problem.get(field) or not isinstance(problem.get(field), str):
                errors.append(f"problem.{field} must be a non-empty string")

    objective = contract.get("objective")
    if not isinstance(objective, dict):
        errors.append("objective must be an object")
    else:
        for field in ("target_behavior", "success_metric"):
            if not objective.get(field) or not isinstance(objective.get(field), str):
                errors.append(f"objective.{field} must be a non-empty string")

    invariants = contract.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        errors.append("invariants must be a non-empty list of constraint strings")
    else:
        for idx, inv in enumerate(invariants):
            if not isinstance(inv, str) or not inv.strip():
                errors.append(f"invariants[{idx}] must be a non-empty string")

    proposed = contract.get("proposed_change")
    if not isinstance(proposed, dict):
        errors.append("proposed_change must be an object")
    else:
        for field in ("hypothesis", "minimal_scope"):
            if not proposed.get(field) or not isinstance(proposed.get(field), str):
                errors.append(f"proposed_change.{field} must be a non-empty string")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("output", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("contract", type=Path)
    resolved = sub.add_parser("resolve")
    resolved.add_argument("contract", type=Path)
    resolved.add_argument("--write", type=Path)
    routed = sub.add_parser("route")
    routed.add_argument("contract", type=Path)
    check_change = sub.add_parser("validate-change-contract")
    check_change.add_argument("contract", type=Path)
    init_change = sub.add_parser("init-change-contract")
    init_change.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "init":
        example = HERE.parent / "example" / "task-config.json"
        if args.output.exists():
            print(f"refusing to overwrite {args.output}")
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print(args.output)
        return 0

    if args.command == "init-change-contract":
        example = HERE.parent / "example" / "change-contract.yaml"
        if args.output.exists():
            print(f"refusing to overwrite {args.output}")
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if example.exists():
            content = example.read_text(encoding="utf-8")
        else:
            content = (
                "version: 1\n"
                "skill_name: knowledge-distill\n"
                "failure_owner: skill\n"
                "intervention: revise-skill\n\n"
                "problem:\n"
                "  observed_behavior: Evidence present but actionable synthesis is absent\n"
                "  suspected_cause: Procedural synthesis rule missing in core loop\n\n"
                "objective:\n"
                "  target_behavior: Causal evidence-to-recommendation structure\n"
                "  success_metric: Higher decision usefulness with zero hallucinated claims\n\n"
                "invariants:\n"
                "  - preserve valid source IDs and provenance hashes\n"
                "  - do not exceed token budget\n\n"
                "proposed_change:\n"
                "  hypothesis: Adding explicit synthesis gate improves downstream utility\n"
                "  minimal_scope: Synthesis instruction section only\n"
            )
        args.output.write_text(content, encoding="utf-8")
        print(args.output)
        return 0

    if args.command == "validate-change-contract":
        data = load_data(args.contract)
        errors = validate_change_contract(data)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, indent=2))
            return 1
        print(
            json.dumps(
                {
                    "ok": True,
                    "skill_name": data.get("skill_name"),
                    "failure_owner": data.get("failure_owner"),
                    "intervention": data.get("intervention", "revise-skill"),
                    "invariants_count": len(data.get("invariants", [])),
                },
                indent=2,
            )
        )
        return 0

    contract = attach_input_fingerprint(resolve(load_json(args.contract)), args.contract.resolve().parent)
    errors = validate(contract)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    if args.command == "validate":
        print(json.dumps({"ok": True, "deliverables": len(contract["deliverables"])}, indent=2))
    elif args.command == "resolve":
        payload = json.dumps(contract, indent=2) + "\n"
        if args.write:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(payload, encoding="utf-8")
            print(args.write)
        else:
            print(payload, end="")
    else:
        print(json.dumps(route(contract, args.contract.parent), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
