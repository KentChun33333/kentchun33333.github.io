import json
import tempfile
import unittest
from pathlib import Path

from task_contract import resolve, route, validate, validate_change_contract


class TaskContractTest(unittest.TestCase):
    def test_resolves_multiple_deliverables_to_distinct_skills_and_profiles(self) -> None:
        contract = resolve(
            {
                "version": 1,
                "input_data": ["data"],
                "objective": "Explain and demonstrate the system",
                "audience": "Engineering leaders",
                "deliverables": [
                    {"id": "research", "type": "research-site", "output_path": "research.html"},
                    {"id": "demo", "type": "agentic-demo", "output_path": "demo.html"},
                ],
            }
        )
        self.assertEqual(validate(contract), [])
        self.assertEqual(contract["deliverables"][0]["skill"], "web")
        self.assertEqual(contract["deliverables"][1]["skill"], "build-async-agentic-web-demo")
        self.assertNotEqual(
            contract["deliverables"][0]["evaluation"]["profile"],
            contract["deliverables"][1]["evaluation"]["profile"],
        )

    def test_route_never_installs_graphify_and_reports_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            (data / "small.py").write_text("def run():\n    pass\n", encoding="utf-8")
            contract = resolve(
                {
                    "version": 1,
                    "input_data": ["data"],
                    "objective": "Explain",
                    "audience": "Maintainers",
                    "deliverables": [
                        {"id": "demo", "type": "system-demo", "output_path": "demo.html"}
                    ],
                }
            )
            decision = route(contract, root)
            self.assertEqual(decision["inventory"]["code_files"], 1)
            self.assertFalse(decision["use_graphify"])

    def test_validate_change_contract_success(self) -> None:
        valid = {
            "version": 1,
            "skill_name": "knowledge-distill",
            "failure_owner": "skill",
            "intervention": "revise-skill",
            "problem": {
                "observed_behavior": "Evidence lacks decision synthesis",
                "suspected_cause": "Missing step in loop",
            },
            "objective": {
                "target_behavior": "Evidence-to-action reasoning",
                "success_metric": "Usefulness increases",
            },
            "invariants": ["preserve citations", "no hallucination"],
            "proposed_change": {
                "hypothesis": "Structured gate improves transfer",
                "minimal_scope": "SKILL.md synthesis section",
            },
        }
        errors = validate_change_contract(valid)
        self.assertEqual(errors, [])

    def test_validate_change_contract_rejects_non_skill_owner_revising_skill(self) -> None:
        invalid = {
            "version": 1,
            "skill_name": "knowledge-distill",
            "failure_owner": "tool",
            "intervention": "revise-skill",
            "problem": {
                "observed_behavior": "Parser dropped blocks",
                "suspected_cause": "Parser regex bug",
            },
            "objective": {
                "target_behavior": "Parse all blocks",
                "success_metric": "0 dropped blocks",
            },
            "invariants": ["keep format"],
            "proposed_change": {
                "hypothesis": "Add prompt rules to fix parser bug",
                "minimal_scope": "SKILL.md",
            },
        }
        errors = validate_change_contract(invalid)
        self.assertTrue(any("non-skill defects must not use intervention 'revise-skill'" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
