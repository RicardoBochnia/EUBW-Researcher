from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eubw_researcher.evaluation.spawned_validator_gate import (
    _build_spawned_validator_request,
    _resolve_selected_scenarios,
)
from eubw_researcher.models import EvaluationScenario


class SpawnedValidatorGateTests(unittest.TestCase):
    def test_build_spawned_validator_request_requires_optional_facet_only_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_dir = Path(tmp_dir)
            request = _build_spawned_validator_request(
                bundle_dir,
                "Synthetic high-risk question?",
            )
            self.assertNotIn("facet_coverage.json", request["required_artifacts"])

            (bundle_dir / "facet_coverage.json").write_text("{}", encoding="utf-8")
            request_with_facet = _build_spawned_validator_request(
                bundle_dir,
                "Synthetic topology question?",
            )

        self.assertIn("facet_coverage.json", request_with_facet["required_artifacts"])

    def test_resolve_selected_scenarios_rejects_duplicate_requested_ids(self) -> None:
        scenarios = [
            EvaluationScenario(
                scenario_id="synthetic_a",
                question="Question A?",
                expectation="Expectation A.",
                spawned_validator_gate_eligible=True,
            ),
            EvaluationScenario(
                scenario_id="synthetic_b",
                question="Question B?",
                expectation="Expectation B.",
                spawned_validator_gate_eligible=True,
            ),
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate scenario_ids are not allowed: synthetic_a",
        ):
            _resolve_selected_scenarios(
                scenarios,
                scenario_ids=["synthetic_a", "synthetic_a"],
                release_gate=False,
                require_eligibility=True,
            )


if __name__ == "__main__":
    unittest.main()
