from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from eubw_researcher.config import (
    load_archive_corpus_config,
    load_evaluation_scenarios,
    load_real_question_pack,
    load_runtime_config,
    load_source_hierarchy,
    load_web_allowlist,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigLoadingTests(unittest.TestCase):
    def test_runtime_and_hierarchy_configs_are_externalized(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.yaml")
        hierarchy = load_source_hierarchy(REPO_ROOT / "configs" / "source_hierarchy.yaml")
        allowlist = load_web_allowlist(REPO_ROOT / "configs" / "web_allowlist.yaml")
        archive_corpus = load_archive_corpus_config(
            REPO_ROOT / "configs" / "real_corpus_selection.yaml"
        )
        scenarios = load_evaluation_scenarios(
            REPO_ROOT / "configs" / "evaluation_scenarios.yaml"
        )
        real_scenarios = load_evaluation_scenarios(
            REPO_ROOT / "configs" / "evaluation_scenarios_real_corpus.yaml"
        )
        real_question_pack = load_real_question_pack(
            REPO_ROOT / "configs" / "real_question_pack.yaml"
        )

        self.assertEqual(runtime.retrieval_top_k, 5)
        self.assertEqual(runtime.web_discovery_max_depth, 1)
        self.assertEqual(runtime.web_max_admitted_per_domain, 10)
        self.assertTrue(hierarchy.default_eu_first)
        self.assertIn("openid.net", allowlist.allowed_domains)
        self.assertTrue(allowlist.policy_for_domain("eur-lex.europa.eu").allowed_path_prefixes)
        self.assertEqual(archive_corpus.archive_root.name, "archive")
        self.assertGreaterEqual(len(archive_corpus.sources), 11)
        self.assertIn(
            "eudi_discussion_topic_x_rp_registration",
            {source.source_id for source in archive_corpus.sources},
        )
        discussion_source = next(
            source
            for source in archive_corpus.sources
            if source.source_id == "eudi_discussion_topic_x_rp_registration"
        )
        self.assertIsNotNone(discussion_source.admission_reason)
        scenario_ids = {scenario.scenario_id for scenario in scenarios}
        self.assertEqual(
            scenario_ids,
            {
                "primary_success_scenario",
                "scenario_a_registration_and_access_certificate_analysis",
                "scenario_b_registration_certificate_mandatory",
                "scenario_c_protocol_authorization_server",
                "high_risk_failure_pattern",
            },
        )
        self.assertEqual(
            {scenario.scenario_id for scenario in real_scenarios},
            scenario_ids | {"scenario_d_certificate_topology_anchor"},
        )
        self.assertEqual(
            {scenario.scenario_id: scenario.required_intent_type for scenario in scenarios},
            {
                "primary_success_scenario": "wallet_requirements_summary",
                "scenario_a_registration_and_access_certificate_analysis": "certificate_layer_analysis",
                "scenario_b_registration_certificate_mandatory": "registration_certificate_scope",
                "scenario_c_protocol_authorization_server": "protocol_authorization_server_comparison",
                "high_risk_failure_pattern": "arf_boundary_check",
            },
        )
        manual_review_accept_ids = {
            scenario.scenario_id
            for scenario in real_scenarios
            if scenario.require_manual_review_accept
        }
        self.assertEqual(
            manual_review_accept_ids,
            {
                "primary_success_scenario",
                "scenario_b_registration_certificate_mandatory",
                "scenario_d_certificate_topology_anchor",
            },
        )
        spawned_validator_eligible_ids = {
            scenario.scenario_id
            for scenario in real_scenarios
            if scenario.spawned_validator_gate_eligible
        }
        self.assertEqual(
            spawned_validator_eligible_ids,
            {
                "scenario_d_certificate_topology_anchor",
                "high_risk_failure_pattern",
            },
        )
        spawned_validator_release_ids = {
            scenario.scenario_id
            for scenario in real_scenarios
            if scenario.spawned_validator_release_gate
        }
        self.assertEqual(
            spawned_validator_release_ids,
            {
                "scenario_d_certificate_topology_anchor",
                "high_risk_failure_pattern",
            },
        )
        self.assertEqual(
            [question.question_id for question in real_question_pack.questions],
            [
                "primary_success_scenario",
                "scenario_a_registration_and_access_certificate_analysis",
                "scenario_b_registration_certificate_mandatory",
                "scenario_c_protocol_authorization_server",
                "scenario_d_certificate_topology_anchor",
            ],
        )
        self.assertTrue(all(question.review_prompts for question in real_question_pack.questions))

    def test_real_question_pack_rejects_duplicate_question_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pack_path = Path(tmp_dir) / "real_question_pack.json"
            pack_path.write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "duplicate",
                                "title": "First",
                                "question": "Question A?",
                                "review_focus": "Focus",
                                "review_prompts": ["Prompt"],
                            },
                            {
                                "question_id": "duplicate",
                                "title": "Second",
                                "question": "Question B?",
                                "review_focus": "Focus",
                                "review_prompts": ["Prompt"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate question_id 'duplicate'"):
                load_real_question_pack(pack_path)

    def test_real_question_pack_rejects_unsafe_question_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pack_path = Path(tmp_dir) / "real_question_pack.json"
            pack_path.write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "../unsafe",
                                "title": "Unsafe",
                                "question": "Question?",
                                "review_focus": "Focus",
                                "review_prompts": ["Prompt"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "question_id must use only letters, numbers, periods, underscores, or hyphens",
            ):
                load_real_question_pack(pack_path)

    def test_real_question_pack_strips_optional_string_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pack_path = Path(tmp_dir) / "real_question_pack.json"
            pack_path.write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "safe_id",
                                "title": "Title",
                                "question": "Question?",
                                "review_focus": "Focus",
                                "expected_intent_type": " synthetic_intent ",
                                "seed_from_scenario_id": "   ",
                                "review_prompts": ["Prompt"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            pack = load_real_question_pack(pack_path)

            self.assertEqual(pack.questions[0].expected_intent_type, "synthetic_intent")
            self.assertIsNone(pack.questions[0].seed_from_scenario_id)

    def test_evaluation_scenarios_reject_duplicate_scenario_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scenarios_path = Path(tmp_dir) / "scenarios.json"
            scenarios_path.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "scenario_id": "duplicate",
                                "question": "Question A?",
                                "expectation": "Expectation A.",
                            },
                            {
                                "scenario_id": "duplicate",
                                "question": "Question B?",
                                "expectation": "Expectation B.",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "duplicate scenario_id 'duplicate'",
            ):
                load_evaluation_scenarios(scenarios_path)

    def test_evaluation_scenarios_reject_unsafe_scenario_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scenarios_path = Path(tmp_dir) / "scenarios.json"
            scenarios_path.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "scenario_id": "../unsafe",
                                "question": "Question?",
                                "expectation": "Expectation.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "scenario_id must use only letters, numbers, periods, underscores, or hyphens",
            ):
                load_evaluation_scenarios(scenarios_path)

    def test_evaluation_scenarios_require_release_gate_entries_to_be_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scenarios_path = Path(tmp_dir) / "scenarios.json"
            scenarios_path.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "scenario_id": "release_only",
                                "question": "Question?",
                                "expectation": "Expectation.",
                                "spawned_validator_release_gate": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "must also be spawned-validator eligible: release_only",
            ):
                load_evaluation_scenarios(scenarios_path)


if __name__ == "__main__":
    unittest.main()
