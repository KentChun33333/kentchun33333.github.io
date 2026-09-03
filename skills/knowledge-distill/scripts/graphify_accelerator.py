#!/usr/bin/env python3
"""Plan or explicitly run the optional Graphify preparation accelerator."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from task_contract import attach_input_fingerprint, load_json, resolve, route, validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--code-only", action="store_true")
    args = parser.parse_args()

    contract_path = args.contract.resolve()
    contract = attach_input_fingerprint(resolve(load_json(contract_path)), contract_path.parent)
    errors = validate(contract)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    decision = route(contract, contract_path.parent)
    if not decision["use_graphify"]:
        print(json.dumps({"ok": True, "executed": False, "decision": decision}, indent=2))
        return 0
    executable = shutil.which("graphify")
    if not executable:
        print(json.dumps({"ok": False, "error": "Graphify was selected but is unavailable"}, indent=2))
        return 1
    inputs = list(contract["input_data"])
    if len(inputs) != 1:
        print(json.dumps({"ok": False, "error": "Graphify execution currently requires one input file or folder"}, indent=2))
        return 1
    command = [executable, "extract", inputs[0]]
    if args.code_only:
        command.append("--code-only")
    plan = {"ok": True, "executed": False, "command": command, "cwd": str(contract_path.parent), "decision": decision}
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return 0
    completed = subprocess.run(command, cwd=contract_path.parent, check=False)
    graph = contract_path.parent / "graphify-out" / "graph.json"
    result = {**plan, "executed": True, "returncode": completed.returncode, "graph": str(graph), "graph_exists": graph.exists()}
    print(json.dumps(result, indent=2))
    return 0 if completed.returncode == 0 and graph.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
