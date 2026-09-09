#!/usr/bin/env python3
"""Validate data_table.yaml and emit browser-ready graph data."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_table.yaml"
I18N_SOURCE = ROOT / "data_table.i18n.yaml"
TARGET = ROOT / "data_table.generated.js"
REQUIRED_NODE_FIELDS = {"id", "grade", "title", "compensation", "detail", "tier", "level"}
VALID_TIERS = {"junior", "middle", "superscale", "political"}
REQUIRED_I18N_UI_FIELDS = {
    "language", "primary_axis", "select_primary", "visible_columns",
    "matrix_title", "matrix_subtitle",
    "toggle_columns", "search_placeholder", "choose_view", "stack_chart",
    "detail_table", "all_levels", "political_apex", "senior_executive",
    "management_tech", "professional_entry", "primary", "stack_note",
    "no_grade", "continues", "coverage_band", "anchored", "projected",
    "grades", "not_provided", "clear_selection", "graph_unavailable",
    "axis_status",
}


def validate(data: dict) -> None:
    institutions = data.get("institutions", {})
    if data.get("default_axis") not in institutions:
        raise ValueError("default_axis must reference an institution")

    institution_order = data.get("institution_order", [])
    if not isinstance(institution_order, list) or set(institution_order) != set(institutions):
        raise ValueError("institution_order must list every institution exactly once")
    if len(institution_order) != len(set(institution_order)):
        raise ValueError("institution_order must not contain duplicates")

    default_visible = data.get("default_visible_institutions", [])
    if not isinstance(default_visible, list) or not default_visible:
        raise ValueError("default_visible_institutions must be a non-empty list")
    if len(default_visible) != len(set(default_visible)):
        raise ValueError("default_visible_institutions must not contain duplicates")
    unknown_visible = set(default_visible) - set(institutions)
    if unknown_visible:
        raise ValueError(
            f"default_visible_institutions has unknown institutions: {sorted(unknown_visible)}"
        )
    if data["default_axis"] not in default_visible:
        raise ValueError("default_axis must be visible by default")

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


def validate_i18n(data: dict, i18n: dict) -> None:
    languages = i18n.get("languages", {})
    default_language = i18n.get("default_language")
    if not languages or default_language not in languages:
        raise ValueError("i18n must define languages and a valid default_language")

    institutions = data["institutions"]
    known_node_ids = {
        institution_id: {node["id"] for node in institution["nodes"]}
        for institution_id, institution in institutions.items()
    }
    for language_id, language in languages.items():
        missing_ui = REQUIRED_I18N_UI_FIELDS - set(language.get("ui", {}))
        if missing_ui:
            raise ValueError(
                f"i18n language {language_id} is missing UI fields: {sorted(missing_ui)}"
            )
        localized_institutions = language.get("institutions", {})
        unknown_institutions = set(localized_institutions) - set(institutions)
        if unknown_institutions:
            raise ValueError(
                f"i18n language {language_id} has unknown institutions: "
                f"{sorted(unknown_institutions)}"
            )
        missing_institutions = set(institutions) - set(localized_institutions)
        if missing_institutions:
            raise ValueError(
                f"i18n language {language_id} is missing institutions: "
                f"{sorted(missing_institutions)}"
            )
        for institution_id, localized in localized_institutions.items():
            missing_labels = {"label", "short_label"} - set(localized)
            if missing_labels:
                raise ValueError(
                    f"i18n language {language_id} is missing labels for "
                    f"{institution_id}: {sorted(missing_labels)}"
                )
            unknown_nodes = set(localized.get("nodes", {})) - known_node_ids[institution_id]
            if unknown_nodes:
                raise ValueError(
                    f"i18n language {language_id} has unknown nodes for "
                    f"{institution_id}: {sorted(unknown_nodes)}"
                )
            # English descriptions live in the canonical data_table.yaml; every
            # additional language must provide a complete node overlay regardless
            # of which language the interface opens with by default.
            if language_id != "en":
                translated_nodes = localized.get("nodes", {})
                missing_nodes = known_node_ids[institution_id] - set(translated_nodes)
                if missing_nodes:
                    raise ValueError(
                        f"i18n language {language_id} is missing node descriptions for "
                        f"{institution_id}: {sorted(missing_nodes)}"
                    )


def main() -> None:
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    validate(data)
    if I18N_SOURCE.exists():
        i18n = yaml.safe_load(I18N_SOURCE.read_text(encoding="utf-8"))
        validate_i18n(data, i18n)
        data["i18n"] = i18n
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    TARGET.write_text(
        "// Generated from data_table.yaml and data_table.i18n.yaml. Do not edit directly.\n"
        f"window.LEVEL_GRAPH={payload};\n",
        encoding="utf-8",
    )
    node_count = sum(len(item["nodes"]) for item in data["institutions"].values())
    print(f"validated {len(data['institutions'])} institutions, {node_count} nodes, "
          f"{len(data.get('anchors', []))} anchors")


if __name__ == "__main__":
    main()
