import json
import tempfile
import unittest
from pathlib import Path

from evaluate_web import audit, compare


class EvaluateWebTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[3]
        self.artifact = self.repo / "skills" / "web" / "examples" / "system-demo.html"

    def contract(self) -> dict:
        return {
            "version": 1,
            "input_data": ["fixture"],
            "input_fingerprint": "fixed-fixture-sha256",
            "comparison": {"model": "fixed", "tools": ["browser"], "token_budget": 1000},
            "objective": "Trace graph updates",
            "audience": "Maintainers",
            "deliverables": [
                {
                    "id": "demo",
                    "type": "system-demo",
                    "skill": "web",
                    "output_path": "demo.html",
                    "requirements": {
                        "claims": ["Updates replace source-owned edges"],
                        "functions": ["Advance and reset the flow"],
                        "observable_effects": ["Active stage and status change visibly"],
                    },
                    "evaluation": {
                        "skill": "evaluate-web-deliverable",
                        "profile": "system-demo-v1",
                        "rules": [],
                    },
                }
            ],
        }

    def judgment(self, score: int) -> dict:
        dimensions = (
            "architecture_fidelity", "end_to_end_trace", "state_transition_clarity",
            "requested_effects", "alternate_failure_path", "information_design",
            "usability_accessibility",
        )
        return {
            "claim_results": [{"requirement": "Updates replace source-owned edges", "passed": True, "evidence": "Core mechanism copy"}],
            "function_results": [{"requirement": "Advance and reset the flow", "passed": True, "evidence": "Both controls operated"}],
            "effect_results": [{"requirement": "Active stage and status change visibly", "passed": True, "evidence": "Active card and status changed"}],
            "rubric_scores": {key: {"score": score, "evidence": f"Observed {key}"} for key in dimensions},
            "hard_failures": [],
        }

    def test_complete_audit_and_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(self.contract()), encoding="utf-8")
            low_path = root / "low.json"
            high_path = root / "high.json"
            low_path.write_text(json.dumps(self.judgment(3)), encoding="utf-8")
            high_path.write_text(json.dumps(self.judgment(4)), encoding="utf-8")
            low = audit(contract_path, "demo", self.artifact, low_path)
            high = audit(contract_path, "demo", self.artifact, high_path)
            self.assertTrue(low["complete"])
            self.assertEqual(low["quality_score"], 60)
            self.assertTrue(compare(low, high)["accepted"])


if __name__ == "__main__":
    unittest.main()
