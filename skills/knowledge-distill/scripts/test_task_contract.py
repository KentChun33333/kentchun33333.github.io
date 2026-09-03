import json
import tempfile
import unittest
from pathlib import Path

from task_contract import resolve, route, validate


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


if __name__ == "__main__":
    unittest.main()
