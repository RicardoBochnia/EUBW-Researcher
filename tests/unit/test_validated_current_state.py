from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from eubw_researcher.corpus.reporting import (
    build_validated_current_state_report,
    render_validated_current_state_report_md,
)
from eubw_researcher.evaluation.runner import (
    build_eval_run_manifest,
    load_eval_run_manifest,
    write_eval_run_manifest,
)
from eubw_researcher.evaluation.spawned_validator_gate import (
    build_spawned_validator_gate_manifest,
    load_spawned_validator_gate_manifest,
    write_spawned_validator_gate_manifest,
)
from eubw_researcher.models import (
    EvalScenarioRunSummary,
    SpawnedValidatorGateManifest,
    SpawnedValidatorGateScenarioRunSummary,
)


class EvalRunManifestTests(unittest.TestCase):
    def test_build_eval_run_manifest_records_binding_gate_state(self) -> None:
        repo_root = Path("/tmp/repo")
        output_dir = repo_root / "artifacts" / "eval_runs_real_corpus"
        scenario_runs = [
            EvalScenarioRunSummary(
                scenario_id="primary_success_scenario",
                passed=True,
                require_manual_review_accept=True,
                manual_review_accept_satisfied=True,
                final_judgment="accept",
                output_dir=str(output_dir / "primary_success_scenario"),
                verdict_path=str(output_dir / "primary_success_scenario" / "verdict.json"),
                manual_review_report_path=str(
                    output_dir / "primary_success_scenario" / "manual_review_report.md"
                ),
            )
        ]
        fixed_now = datetime(2026, 4, 4, 13, 45, 0, tzinfo=timezone.utc)

        with patch(
            "eubw_researcher.evaluation.runner._utcnow",
            return_value=fixed_now,
        ), patch(
            "eubw_researcher.evaluation.runner.collect_git_metadata",
            return_value={"commit": "abc123", "branch": "main", "dirty": False},
        ):
            manifest = build_eval_run_manifest(
                repo_root,
                scenario_config_path=repo_root / "configs" / "evaluation_scenarios_real_corpus.yaml",
                catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                corpus_state_id="state123",
                runtime_contract_version="option_a_runtime.v1",
                scenario_runs=scenario_runs,
                coverage_gate_passed=True,
                coverage_report_path=output_dir / "corpus_coverage_report.json",
                coverage_summary_path=output_dir / "corpus_coverage_summary.md",
            )

        self.assertEqual(manifest.binding_gate_surface, "real_corpus_eval")
        self.assertTrue(manifest.overall_passed)
        self.assertEqual(manifest.runtime_contract_version, "option_a_runtime.v1")
        self.assertEqual(manifest.git_commit, "abc123")
        self.assertEqual(len(manifest.scenario_runs), 1)

    def test_eval_run_manifest_round_trips_through_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            manifest_path = tmp_root / "eval_run_manifest.json"
            scenario_runs = [
                EvalScenarioRunSummary(
                    scenario_id="scenario_b",
                    passed=False,
                    require_manual_review_accept=False,
                    manual_review_accept_satisfied=None,
                    final_judgment="reject",
                    output_dir=str(tmp_root / "scenario_b"),
                    verdict_path=str(tmp_root / "scenario_b" / "verdict.json"),
                    manual_review_report_path=str(
                        tmp_root / "scenario_b" / "manual_review_report.md"
                    ),
                )
            ]
            manifest = build_eval_run_manifest(
                tmp_root,
                scenario_config_path=tmp_root / "synthetic_scenarios.json",
                catalog_path=tmp_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                corpus_state_id="state456",
                runtime_contract_version="option_a_runtime.v1",
                scenario_runs=scenario_runs,
                coverage_gate_passed=False,
                coverage_report_path=None,
                coverage_summary_path=None,
            )
            write_eval_run_manifest(manifest, manifest_path)

            loaded = load_eval_run_manifest(manifest_path)

        self.assertEqual(loaded.corpus_state_id, "state456")
        self.assertFalse(loaded.overall_passed)
        self.assertEqual(loaded.scenario_runs[0].final_judgment, "reject")
        self.assertIsNone(loaded.scenario_runs[0].manual_review_accept_satisfied)

    def test_build_eval_run_manifest_defaults_unknown_git_dirty_to_true(self) -> None:
        with patch(
            "eubw_researcher.evaluation.runner.collect_git_metadata",
            return_value={"commit": "abc123", "branch": "main"},
        ):
            manifest = build_eval_run_manifest(
                Path("/tmp/repo"),
                scenario_config_path=Path("/tmp/repo/configs/evaluation_scenarios_real_corpus.yaml"),
                catalog_path=Path("/tmp/repo/artifacts/real_corpus/curated_catalog.json"),
                corpus_state_id="state123",
                runtime_contract_version="option_a_runtime.v1",
                scenario_runs=[],
                coverage_gate_passed=True,
                coverage_report_path=None,
                coverage_summary_path=None,
            )

        self.assertTrue(manifest.git_dirty)
        self.assertFalse(manifest.overall_passed)

    def test_load_eval_run_manifest_defaults_missing_git_dirty_to_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "eval_run_manifest.json"
            manifest_path.write_text(
                """
{
  "run_timestamp": "2026-04-04T00:00:00+00:00",
  "scenario_config_path": "/tmp/repo/configs/evaluation_scenarios_real_corpus.yaml",
  "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
  "corpus_state_id": "state123",
  "runtime_contract_version": "option_a_runtime.v1",
  "binding_gate_surface": "real_corpus_eval",
  "coverage_gate_passed": true,
  "overall_passed": true,
  "coverage_report_path": null,
  "coverage_summary_path": null,
  "git_commit": "abc123",
  "git_branch": "main",
  "scenario_runs": []
}
""".strip(),
                encoding="utf-8",
            )

            manifest = load_eval_run_manifest(manifest_path)

        self.assertTrue(manifest.git_dirty)


class ValidatedCurrentStateReportTests(unittest.TestCase):
    def _manifest(self):
        with patch(
            "eubw_researcher.evaluation.runner.collect_git_metadata",
            return_value={"commit": "abc123", "branch": "main", "dirty": False},
        ):
            return build_eval_run_manifest(
                Path("/tmp/repo"),
                scenario_config_path=Path("/tmp/repo/configs/evaluation_scenarios_real_corpus.yaml"),
                catalog_path=Path("/tmp/repo/artifacts/real_corpus/curated_catalog.json"),
                corpus_state_id="state123",
                runtime_contract_version="option_a_runtime.v1",
                scenario_runs=[
                    EvalScenarioRunSummary(
                        scenario_id="primary_success_scenario",
                        passed=True,
                        require_manual_review_accept=True,
                        manual_review_accept_satisfied=True,
                        final_judgment="accept",
                        output_dir="/tmp/repo/artifacts/eval_runs_real_corpus/primary_success_scenario",
                        verdict_path="/tmp/repo/artifacts/eval_runs_real_corpus/primary_success_scenario/verdict.json",
                        manual_review_report_path="/tmp/repo/artifacts/eval_runs_real_corpus/primary_success_scenario/manual_review_report.md",
                    )
                ],
                coverage_gate_passed=True,
                coverage_report_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/corpus_coverage_report.json"),
                coverage_summary_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/corpus_coverage_summary.md"),
            )

    def _spawned_validator_manifest(self, *, gate_target: str = "release_gate"):
        return build_spawned_validator_gate_manifest(
            scenario_config_path=Path("/tmp/repo/configs/evaluation_scenarios_real_corpus.yaml"),
            catalog_path=Path("/tmp/repo/artifacts/real_corpus/curated_catalog.json"),
            corpus_state_id="state123",
            runtime_contract_version="option_a_runtime.v1",
            gate_target=gate_target,
            validator_command="python3 validator.py",
            scenario_runs=[
                SpawnedValidatorGateScenarioRunSummary(
                    scenario_id="scenario_d_certificate_topology_anchor",
                    deterministic_passed=True,
                    spawned_validator_invoked=True,
                    spawned_validator_contract_passed=True,
                    spawned_validator_passed=True,
                    final_passed=True,
                    output_dir="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor",
                    verdict_path="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor/verdict.json",
                    blind_validation_report_path="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor/blind_validation_report.json",
                    spawned_validator_request_path="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor/spawned_validator_request.json",
                    spawned_validator_result_path="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor/spawned_validator_result.json",
                )
            ],
        )

    def test_spawned_validator_manifest_round_trips_through_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "spawned_validator_gate_manifest.json"
            manifest = self._spawned_validator_manifest()
            write_spawned_validator_gate_manifest(manifest, manifest_path)

            loaded = load_spawned_validator_gate_manifest(manifest_path)

        self.assertTrue(loaded.overall_passed)
        self.assertEqual(loaded.gate_target, "release_gate")
        self.assertEqual(loaded.scenario_runs[0].scenario_id, "scenario_d_certificate_topology_anchor")

    def test_build_validated_current_state_report_accepts_matching_state(self) -> None:
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/./curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }
        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=Path("/tmp/repo/artifacts/current_state/corpus_coverage_report.json"),
            coverage_summary_path=Path("/tmp/repo/artifacts/current_state/corpus_coverage_summary.md"),
            corpus_selection_summary_path=Path("/tmp/repo/artifacts/current_state/corpus_selection_summary.md"),
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
            real_question_pack_manifest={
                "run_id": "pack123",
                "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
                "corpus_state_id": "state123",
                "runtime_contract_version": "option_a_runtime.v1",
            },
            real_question_pack_manifest_path=Path(
                "/tmp/repo/artifacts/real_question_pack_runs/pack123/pack_run_manifest.json"
            ),
            spawned_validator_gate_manifest=self._spawned_validator_manifest(),
            spawned_validator_gate_manifest_path=Path(
                "/tmp/repo/artifacts/spawned_validator_gate_runs/spawned_validator_gate_manifest.json"
            ),
            git_metadata={"commit": "abc123", "branch": "main", "dirty": False},
        )

        self.assertTrue(report.validated)
        self.assertEqual(report.binding_gate_surface, "real_corpus_eval")
        self.assertEqual(
            report.release_validation_mode,
            "deterministic_eval_plus_supplemental_spawned_validator",
        )
        self.assertTrue(report.spawned_validator_gate_passed)
        self.assertTrue(report.spawned_validator_gate_matches_state)
        self.assertTrue(report.supplemental_real_question_pack_matches_state)
        self.assertEqual(len(report.binding_review_samples), 1)
        self.assertEqual(
            report.catalog_path,
            str(Path("/tmp/repo/artifacts/real_corpus/curated_catalog.json").resolve()),
        )

    def test_build_validated_current_state_report_flags_mismatched_state(self) -> None:
        snapshot = {
            "corpus_state_id": "different-state",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }
        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
        )

        self.assertFalse(report.validated)
        self.assertFalse(report.current_catalog_matches_eval_gate)

    def test_build_validated_current_state_report_can_bind_spawned_validator_gate(self) -> None:
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }

        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
            spawned_validator_gate_manifest=self._spawned_validator_manifest(),
            spawned_validator_gate_manifest_path=Path(
                "/tmp/repo/artifacts/spawned_validator_gate_runs/spawned_validator_gate_manifest.json"
            ),
            promote_spawned_validator_gate=True,
        )

        self.assertTrue(report.validated)
        self.assertEqual(
            report.release_validation_mode,
            "deterministic_eval_plus_binding_spawned_validator",
        )
        self.assertTrue(report.spawned_validator_gate_passed)

    def test_build_validated_current_state_report_requires_release_gate_for_binding(self) -> None:
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }

        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
            spawned_validator_gate_manifest=self._spawned_validator_manifest(
                gate_target="named_scenarios"
            ),
            spawned_validator_gate_manifest_path=Path(
                "/tmp/repo/artifacts/spawned_validator_gate_runs/spawned_validator_gate_manifest.json"
            ),
            promote_spawned_validator_gate=True,
        )

        self.assertFalse(report.validated)
        self.assertEqual(
            report.release_validation_mode,
            "deterministic_eval_plus_binding_spawned_validator",
        )
        self.assertTrue(report.spawned_validator_gate_passed)
        self.assertTrue(report.spawned_validator_gate_matches_state)

    def test_build_validated_current_state_report_rejects_binding_manifest_without_verified_runs(self) -> None:
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }
        tampered_manifest = SpawnedValidatorGateManifest(
            run_timestamp="2026-04-04T00:00:00+00:00",
            scenario_config_path="/tmp/repo/configs/evaluation_scenarios_real_corpus.yaml",
            catalog_path="/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            corpus_state_id="state123",
            runtime_contract_version="option_a_runtime.v1",
            gate_target="release_gate",
            validator_command="python3 validator.py",
            overall_passed=True,
            scenario_runs=[],
        )

        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
            spawned_validator_gate_manifest=tampered_manifest,
            spawned_validator_gate_manifest_path=Path(
                "/tmp/repo/artifacts/spawned_validator_gate_runs/spawned_validator_gate_manifest.json"
            ),
            promote_spawned_validator_gate=True,
        )

        self.assertFalse(report.validated)
        self.assertFalse(report.spawned_validator_gate_passed)

    def test_build_validated_current_state_report_rejects_binding_manifest_without_validator_invocation(self) -> None:
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }
        manifest_without_invocation = SpawnedValidatorGateManifest(
            run_timestamp="2026-04-04T00:00:00+00:00",
            scenario_config_path="/tmp/repo/configs/evaluation_scenarios_real_corpus.yaml",
            catalog_path="/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            corpus_state_id="state123",
            runtime_contract_version="option_a_runtime.v1",
            gate_target="release_gate",
            validator_command="python3 validator.py",
            overall_passed=True,
            scenario_runs=[
                SpawnedValidatorGateScenarioRunSummary(
                    scenario_id="scenario_d_certificate_topology_anchor",
                    deterministic_passed=True,
                    spawned_validator_invoked=False,
                    spawned_validator_contract_passed=None,
                    spawned_validator_passed=None,
                    final_passed=True,
                    output_dir="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor",
                    verdict_path="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor/verdict.json",
                    blind_validation_report_path="/tmp/repo/artifacts/spawned_validator_gate_runs/scenario_d_certificate_topology_anchor/blind_validation_report.json",
                )
            ],
        )

        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
            spawned_validator_gate_manifest=manifest_without_invocation,
            spawned_validator_gate_manifest_path=Path(
                "/tmp/repo/artifacts/spawned_validator_gate_runs/spawned_validator_gate_manifest.json"
            ),
            promote_spawned_validator_gate=True,
        )

        self.assertFalse(report.validated)
        self.assertFalse(report.spawned_validator_gate_passed)

    def test_render_validated_current_state_report_markdown_lists_binding_sample(self) -> None:
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }
        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=self._manifest(),
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=Path("/tmp/repo/artifacts/current_state/corpus_coverage_report.json"),
            coverage_summary_path=Path("/tmp/repo/artifacts/current_state/corpus_coverage_summary.md"),
            corpus_selection_summary_path=Path("/tmp/repo/artifacts/current_state/corpus_selection_summary.md"),
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
        )

        output = render_validated_current_state_report_md(report)

        self.assertIn("# Validated Current State", output)
        self.assertIn("primary_success_scenario", output)
        self.assertIn("real_corpus_eval", output)
        self.assertIn("deterministic_eval_only", output)

    def test_build_validated_current_state_report_preserves_unknown_coverage_state(self) -> None:
        manifest = self._manifest()
        manifest.coverage_gate_passed = None
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }

        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=manifest,
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
        )

        self.assertIsNone(report.coverage_gate_passed)
        self.assertFalse(report.validated)
        self.assertIn("Coverage gate passed: unknown", render_validated_current_state_report_md(report))

    def test_render_validated_current_state_report_marks_unknown_manual_review_status(self) -> None:
        manifest = self._manifest()
        manifest.scenario_runs[0].manual_review_accept_satisfied = None
        snapshot = {
            "corpus_state_id": "state123",
            "catalog_path": "/tmp/repo/artifacts/real_corpus/curated_catalog.json",
            "total_sources": 7,
            "counts_by_kind": {"regulation": 2},
            "counts_by_role_level": {"high": 7},
            "source_ids": ["a"],
        }

        report = build_validated_current_state_report(
            snapshot,
            eval_manifest=manifest,
            eval_manifest_path=Path("/tmp/repo/artifacts/eval_runs_real_corpus/eval_run_manifest.json"),
            runtime_contract_version="option_a_runtime.v1",
            coverage_report_path=None,
            coverage_summary_path=None,
            corpus_selection_summary_path=None,
            corpus_state_snapshot_path=Path("/tmp/repo/artifacts/current_state/corpus_state_snapshot.json"),
        )

        self.assertIsNone(report.binding_review_samples[0].manual_review_accept_satisfied)
        self.assertIn("unknown", render_validated_current_state_report_md(report))
        self.assertIn("| primary_success_scenario | unknown |", render_validated_current_state_report_md(report))


if __name__ == "__main__":
    unittest.main()
