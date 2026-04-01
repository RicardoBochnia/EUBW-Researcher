from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.config import (
    load_archive_corpus_config,
    load_evaluation_scenarios,
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

        self.assertEqual(runtime.retrieval_top_k, 5)
        self.assertEqual(runtime.web_discovery_max_depth, 1)
        self.assertEqual(runtime.web_max_admitted_per_domain, 10)
        self.assertTrue(hierarchy.default_eu_first)
        self.assertIn("openid.net", allowlist.allowed_domains)
        self.assertTrue(allowlist.policy_for_domain("eur-lex.europa.eu").allowed_path_prefixes)
        self.assertEqual(archive_corpus.archive_root.name, "archive")
        self.assertGreaterEqual(len(archive_corpus.sources), 10)
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
        self.assertEqual({scenario.scenario_id for scenario in real_scenarios}, scenario_ids)
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
            },
        )


if __name__ == "__main__":
    unittest.main()
