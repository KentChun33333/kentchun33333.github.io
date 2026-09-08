#!/usr/bin/env python3
"""Validate data_table.yaml and emit browser-ready graph data."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_table.yaml"
TARGET = ROOT / "data_table.generated.js"
REQUIRED_NODE_FIELDS = {"id", "grade", "title", "compensation", "detail", "tier", "level"}
VALID_TIERS = {"junior", "middle", "superscale", "political"}


def validate(data: dict) -> None:
    institutions = data.get("institutions", {})
    if data.get("default_axis") not in institutions:
        raise ValueError("default_axis must reference an institution")

    known_nodes: set[str] = set()
    for institution_id, institution in institutions.items():
        nodes = institution.get("nodes", [])
        ids: set[str] = set()
        levels: list[float] = []
        for node in nodes:
            missing = REQUIRED_NODE_FIELDS - node.keys()
            if missing:
                raise ValueError(f"{institution_id}.{node.get('id', '?')} missing {sorted(missing)}")
            if node["id"] in ids:
                raise ValueError(f"duplicate node id: {institution_id}.{node['id']}")
            if node["tier"] not in VALID_TIERS:
                raise ValueError(f"invalid tier on {institution_id}.{node['id']}")
            ids.add(node["id"])
            levels.append(float(node["level"]))
            known_nodes.add(f"{institution_id}.{node['id']}")
        if levels != sorted(levels):
            raise ValueError(f"nodes for {institution_id} must be ordered by level")

    for edge in data.get("anchors", []):
        if edge.get("from") not in known_nodes or edge.get("to") not in known_nodes:
            raise ValueError(f"anchor has unknown endpoint: {edge}")
        weight = float(edge.get("weight", 0))
        if not 0 < weight <= 1:
            raise ValueError(f"anchor weight must be within (0, 1]: {edge}")


def main() -> None:
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    validate(data)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    TARGET.write_text(
        "// Generated from data_table.yaml. Do not edit directly.\n"
        f"window.LEVEL_GRAPH={payload};\n",
        encoding="utf-8",
    )
    node_count = sum(len(item["nodes"]) for item in data["institutions"].values())
    print(f"validated {len(data['institutions'])} institutions, {node_count} nodes, "
          f"{len(data.get('anchors', []))} anchors")


if __name__ == "__main__":
    main()
