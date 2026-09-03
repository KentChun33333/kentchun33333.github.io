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
