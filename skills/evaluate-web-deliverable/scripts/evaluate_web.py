#!/usr/bin/env python3
"""Contract-bound scoring for categorized HTML deliverables."""

from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROFILES = HERE.parent / "references" / "profiles.json"


class Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.tags: set[str] = set()
        self.text: list[str] = []
        self.has_viewport = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "meta" and values.get("name") == "viewport":
            self.has_viewport = True

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def canonical_fingerprint(contract: dict[str, Any], deliverable: dict[str, Any]) -> str:
    frozen = {
        "version": contract.get("version"),
        "input_data": contract.get("input_data"),
        "input_fingerprint": contract.get("input_fingerprint"),
        "objective": contract.get("objective"),
        "audience": contract.get("audience"),
        "comparison": contract.get("comparison"),
        "deliverable": deliverable,
    }
    payload = json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def select_deliverable(contract: dict[str, Any], deliverable_id: str) -> dict[str, Any]:
    matches = [item for item in contract.get("deliverables", []) if item.get("id") == deliverable_id]
    if len(matches) != 1:
        raise ValueError(f"expected one deliverable with id {deliverable_id!r}")
    return matches[0]


def preflight(text: str, deliverable: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = Inspector()
    parsed.feed(text)
    duplicates = sorted({value for value in parsed.ids if parsed.ids.count(value) > 1})
    checks = [
        {"name": "html_document", "passed": {"html", "head", "body", "title", "main"} <= parsed.tags},
        {"name": "viewport", "passed": parsed.has_viewport},
        {"name": "unique_ids", "passed": not duplicates, "detail": duplicates},
        {"name": "scripted_interaction", "passed": "script" in parsed.tags},
        {"name": "live_feedback", "passed": "aria-live" in text},
        {"name": "category_matches_profile", "passed": deliverable.get("type") == profile.get("category")},
    ]
    return checks


def score_judgment(judgment: dict[str, Any], deliverable: dict[str, Any], profile: dict[str, Any]) -> tuple[float, list[str]]:
    errors: list[str] = []
    rubric = judgment.get("rubric_scores") or {}
    weighted = 0.0
    for dimension, weight in profile["dimensions"].items():
        entry = rubric.get(dimension) or {}
        score = entry.get("score")
        evidence = str(entry.get("evidence") or "").strip()
        if not isinstance(score, (int, float)) or not 0 <= score <= 5:
            errors.append(f"missing or invalid 0-5 score: {dimension}")
            continue
        if not evidence:
            errors.append(f"missing judgment evidence: {dimension}")
        weighted += (float(score) / 5.0) * weight

    requirements = deliverable.get("requirements") or {}
    result_groups = (
        ("claims", "claim_results", "required claim not demonstrated"),
        ("functions", "function_results", "required function not demonstrated"),
        ("observable_effects", "effect_results", "observable effect not demonstrated"),
    )
    for requirement_key, result_key, error_label in result_groups:
        expected = [str(value) for value in requirements.get(requirement_key, [])]
        observed = {
            str(item.get("requirement")): item
            for item in judgment.get(result_key, [])
            if isinstance(item, dict)
        }
        for requirement in expected:
            result = observed.get(requirement) or {}
            if not result.get("passed") or not str(result.get("evidence") or "").strip():
                errors.append(f"{error_label}: {requirement}")
    return round(weighted, 2), errors


def audit(contract_path: Path, deliverable_id: str, artifact: Path, judgment_path: Path | None) -> dict[str, Any]:
    contract = read_object(contract_path)
    deliverable = select_deliverable(contract, deliverable_id)
    profiles = read_object(PROFILES)
    profile_name = (deliverable.get("evaluation") or {}).get("profile")
    if profile_name not in profiles:
        raise ValueError(f"unknown evaluation profile {profile_name!r}")
    profile = profiles[profile_name]
    text = artifact.read_text(encoding="utf-8")
    checks = preflight(text, deliverable, profile)
    score: float | None = None
    judgment_errors: list[str] = []
    hard_failures: list[str] = []
    if judgment_path:
        judgment = read_object(judgment_path)
        score, judgment_errors = score_judgment(judgment, deliverable, profile)
        hard_failures = [str(item) for item in judgment.get("hard_failures", [])]
    failed_checks = [item["name"] for item in checks if not item["passed"]]
    complete = judgment_path is not None and not failed_checks and not judgment_errors and not hard_failures
    reproducible = bool(contract.get("input_fingerprint") and contract.get("comparison"))
    return {
        "contract_fingerprint": canonical_fingerprint(contract, deliverable),
        "deliverable_id": deliverable_id,
        "profile": profile_name,
        "artifact": str(artifact),
        "preflight": checks,
        "quality_score": score,
        "errors": failed_checks + judgment_errors,
        "hard_failures": hard_failures,
        "complete": complete,
        "reproducible": reproducible,
        "promotable": complete and reproducible,
    }


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    same = baseline.get("contract_fingerprint") == candidate.get("contract_fingerprint") and baseline.get("profile") == candidate.get("profile")
    base_score = baseline.get("quality_score")
    candidate_score = candidate.get("quality_score")
    higher = isinstance(base_score, (int, float)) and isinstance(candidate_score, (int, float)) and candidate_score > base_score
    accepted = bool(same and baseline.get("promotable") and candidate.get("promotable") and higher)
    return {
        "comparable": same,
        "baseline_score": base_score,
        "candidate_score": candidate_score,
        "delta": round(candidate_score - base_score, 2) if higher else None,
        "accepted": accepted,
        "reason": "candidate passes the same contract with a higher score" if accepted else "comparison or promotion condition failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--contract", type=Path, required=True)
    audit_parser.add_argument("--deliverable", required=True)
    audit_parser.add_argument("--artifact", type=Path, required=True)
    audit_parser.add_argument("--judgment", type=Path)
    audit_parser.add_argument("--write", type=Path)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("baseline", type=Path)
    compare_parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        result = audit(args.contract, args.deliverable, args.artifact, args.judgment)
        code = 0 if result["complete"] or args.judgment is None else 1
        payload = json.dumps(result, indent=2) + "\n"
        if args.write:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(payload, encoding="utf-8")
            print(args.write)
        else:
            print(payload, end="")
        return code
    result = compare(read_object(args.baseline), read_object(args.candidate))
    print(json.dumps(result, indent=2))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
