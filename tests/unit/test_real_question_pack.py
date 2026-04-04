from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.evaluation.git_metadata import collect_git_metadata
from eubw_researcher.evaluation.real_question_pack import (
    _build_question_verdict,
    default_real_question_pack_output_dir,
    _git_metadata,
    run_real_question_pack,
)
from eubw_researcher.models import ManualReviewArtifact, ManualReviewCheck

REAL_CORPUS_BUNDLE_ARTIFACTS = [
    "retrieval_plan.json",
    "gap_records.json",
    "web_fetch_records.json",
    "ingestion_report.json",
    "ledger_entries.json",
    "approved_ledger.json",
    "final_answer.txt",
    "pinpoint_evidence.json",
    "answer_alignment.json",
    "blind_validation_report.json",
    "manual_review.json",
    "manual_review_report.md",
    "corpus_coverage_report.json",
    "verdict.json",
]

NON_REAL_CORPUS_BUNDLE_ARTIFACTS = [
    artifact_name
    for artifact_name in REAL_CORPUS_BUNDLE_ARTIFACTS
    if artifact_name != "corpus_coverage_report.json"
]

def _fake_review_artifact(_result, *, scenario_id=None):
    return ManualReviewArtifact(
        question="Synthetic question?",
        scenario_id=scenario_id,
        artifact_scope="synthetic_intent",
        filled=False,
        checks=[
            ManualReviewCheck(
                check_id="blocked_claims_hidden",
                status="pass",
                evidence="ok",
            ),
        ],
        summary="1/1 checks passing.",
    )


class RealQuestionPackRunnerTests(unittest.TestCase):
    @staticmethod
    def _write_bundle_artifacts(bundle_dir: Path, artifact_names) -> None:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        for artifact_name in artifact_names:
            (bundle_dir / artifact_name).write_text("{}", encoding="utf-8")

    def _write_pack_config(self, root: Path) -> Path:
        pack_path = root / "pack.json"
        pack_path.write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "synthetic_question",
                            "title": "Synthetic Question",
                            "question": "Synthetic question?",
                            "review_focus": "Synthetic review focus.",
                            "expected_intent_type": "synthetic_intent",
                            "tags": ["synthetic"],
                            "review_prompts": ["Is the bundle usable?"],
                            "seed_from_scenario_id": "scenario.synthetic",
                        }
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return pack_path

    def _fake_response(
        self,
        output_dir: Path,
        *,
        repo_root: Path = None,
        intent_type: str = "synthetic_intent",
        web_fetch_records=None,
        catalog_path: Path = None,
    ) -> SimpleNamespace:
        if catalog_path is None and repo_root is None:
            raise ValueError("repo_root is required when catalog_path is not provided.")
        resolved_catalog_path = (
            catalog_path.resolve()
            if catalog_path is not None
            else (repo_root / "artifacts" / "real_corpus" / "curated_catalog.json").resolve()
        )
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type=intent_type),
            approved_entries=[object(), object()],
            gap_records=[object()],
            web_fetch_records=web_fetch_records
            if web_fetch_records is not None
            else [
                SimpleNamespace(record_type="discovery"),
                SimpleNamespace(record_type="fetch"),
                SimpleNamespace(record_type="fetch"),
            ],
            provisional_grouping=[],
            corpus_coverage_report=object(),
        )
        return SimpleNamespace(
            contract_version="option_a_runtime.v2",
            result_schema_version="agent_runtime_result.v1",
            catalog_path=resolved_catalog_path,
            corpus_state_id="synthetic-state",
            output_dir=output_dir.resolve(),
            result=result,
        )

    def test_default_output_dir_uses_timestamped_run_id(self) -> None:
        repo_root = Path("/tmp/repo")
        fixed_now = datetime(2026, 4, 3, 10, 15, 30, tzinfo=timezone.utc)

        with patch(
            "eubw_researcher.evaluation.real_question_pack._utcnow",
            return_value=fixed_now,
        ):
            output_dir = default_real_question_pack_output_dir(repo_root)

        self.assertEqual(
            output_dir,
            Path("/tmp/repo/artifacts/real_question_pack_runs/20260403T101530Z"),
        )

    def test_runner_captures_git_metadata_before_default_run_dir_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            fixed_now = datetime(2026, 4, 3, 10, 15, 30, tzinfo=timezone.utc)
            expected_run_root = (
                repo_root / "artifacts" / "real_question_pack_runs" / "20260403T101530Z"
            )
            question_dir = expected_run_root / "synthetic_question"

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, **_kwargs):
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            def _git_metadata(_repo_root):
                self.assertFalse(expected_run_root.exists())
                return {"commit": "abc123", "branch": "branch", "dirty": False}

            with patch(
                "eubw_researcher.evaluation.real_question_pack._utcnow",
                return_value=fixed_now,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                side_effect=_git_metadata,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

                run_root, manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            self.assertEqual(run_root, expected_run_root.resolve())
            self.assertFalse(manifest.git_dirty)
            self.assertTrue(manifest.repo_local_artifacts_written)

    def test_runner_marks_repo_local_artifacts_written_for_repo_local_real_corpus_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = Path(tmp_dir).parent / "external-real-question-pack-run"
            question_dir = output_dir / "synthetic_question"

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, **_kwargs):
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={"commit": "abc123", "branch": "branch", "dirty": False},
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                )

                _run_root, manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            self.assertTrue(manifest.repo_local_artifacts_written)

    def test_runner_keeps_repo_local_artifacts_written_false_when_output_and_catalog_are_external(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, tempfile.TemporaryDirectory() as external_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = Path(external_dir) / "real-question-pack-run"
            question_dir = output_dir / "synthetic_question"
            external_catalog_path = Path(external_dir) / "catalog" / "source_catalog.json"
            external_catalog_path.parent.mkdir(parents=True, exist_ok=True)
            external_catalog_path.write_text("{}", encoding="utf-8")

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, **_kwargs):
                self._write_bundle_artifacts(bundle_dir, NON_REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={"commit": "abc123", "branch": "branch", "dirty": False},
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    catalog_path=external_catalog_path,
                )

                _run_root, manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=external_catalog_path,
                )

            self.assertFalse(manifest.repo_local_artifacts_written)

    def test_runner_writes_manifest_with_review_signals_and_no_benchmark_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            question_dir = output_dir / "synthetic_question"
            fixed_now = datetime(2026, 4, 3, 10, 15, 30, tzinfo=timezone.utc)
            built_reports = []
            captured_report = {}

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, manual_review_report=None, **_kwargs):
                captured_report["value"] = manual_review_report
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                report = SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="needs_follow_up",
                )
                built_reports.append(report)
                return report

            with patch(
                "eubw_researcher.evaluation.real_question_pack._utcnow",
                return_value=fixed_now,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={
                    "commit": "abc123",
                    "branch": "codex/issue-8-real-question-pack",
                    "dirty": False,
                },
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                )

                run_root, manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            manifest_path = run_root / "pack_run_manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(run_root, output_dir.resolve())
            self.assertEqual(manifest.run_id, "synthetic-run")
            self.assertEqual(payload["selected_question_ids"], ["synthetic_question"])
            self.assertEqual(payload["runtime_contract_version"], "option_a_runtime.v2")
            self.assertEqual(payload["git_branch"], "codex/issue-8-real-question-pack")
            self.assertFalse(payload["git_dirty"])
            self.assertTrue(payload["repo_local_artifacts_written"])
            self.assertEqual(payload["run_triage_summary"]["total_questions"], 1)
            self.assertEqual(
                payload["run_triage_summary"]["accepted_question_ids"],
                ["synthetic_question"],
            )
            self.assertEqual(payload["run_triage_summary"]["rejected_question_ids"], [])
            self.assertEqual(
                payload["run_triage_summary"]["question_ids_with_discovery"],
                ["synthetic_question"],
            )
            self.assertEqual(
                payload["run_triage_summary"]["question_ids_with_fetch"],
                ["synthetic_question"],
            )
            self.assertEqual(
                payload["run_triage_summary"]["question_ids_with_missing_artifacts"],
                [],
            )
            self.assertEqual(len(payload["question_runs"]), 1)
            self.assertEqual(
                payload["question_runs"][0]["review_focus"],
                "Synthetic review focus.",
            )
            self.assertEqual(
                payload["question_runs"][0]["linked_scenario_id"],
                "scenario.synthetic",
            )
            self.assertEqual(payload["question_runs"][0]["tags"], ["synthetic"])
            self.assertEqual(payload["question_runs"][0]["discovery_record_count"], 1)
            self.assertEqual(payload["question_runs"][0]["web_fetch_count"], 2)
            self.assertTrue(payload["question_runs"][0]["used_official_web_discovery"])
            self.assertFalse(payload["question_runs"][0]["local_corpus_only"])
            self.assertFalse(payload["question_runs"][0]["has_missing_artifacts"])
            self.assertEqual(payload["question_runs"][0]["final_judgment"], "accept")
            self.assertEqual(
                payload["question_runs"][0]["product_output_self_sufficiency_verdict"],
                "needs_follow_up",
            )
            self.assertEqual(payload["question_runs"][0]["missing_artifacts"], [])
            self.assertFalse(payload["question_runs"][0]["review_complete"])
            self.assertNotIn("score", payload)
            self.assertNotIn("pass_rate", payload)
            self.assertEqual(len(built_reports), 1)
            self.assertIs(captured_report["value"], built_reports[0])

    def test_runner_rejects_question_summary_when_expected_intent_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            question_dir = output_dir / "synthetic_question"

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, **_kwargs):
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={"commit": "abc123", "branch": "branch", "dirty": False},
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                    intent_type="wrong_intent",
                )

                run_root, _manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            payload = json.loads(
                (run_root / "pack_run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["question_runs"][0]["intent_type"], "wrong_intent")
            self.assertEqual(payload["question_runs"][0]["final_judgment"], "reject")
            self.assertEqual(
                payload["run_triage_summary"]["rejected_question_ids"],
                ["synthetic_question"],
            )

    def test_runner_clears_stale_question_artifacts_before_writing_new_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            question_dir = output_dir / "synthetic_question"
            question_dir.mkdir(parents=True, exist_ok=True)
            (question_dir / "facet_coverage.json").write_text("stale", encoding="utf-8")

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, **_kwargs):
                self.assertFalse((bundle_dir / "facet_coverage.json").exists())
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={"commit": "abc123", "branch": "branch", "dirty": False},
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                response = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                    intent_type="synthetic_intent",
                )
                response.result.web_fetch_records = []
                facade_cls.return_value.run_evidence_only.return_value = response

                run_root, _manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            payload = json.loads(
                (run_root / "pack_run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("facet_coverage.json", payload["question_runs"][0]["artifacts_present"])
            self.assertIn("verdict.json", payload["question_runs"][0]["artifacts_present"])
            self.assertTrue(payload["question_runs"][0]["local_corpus_only"])
            self.assertFalse(payload["question_runs"][0]["used_official_web_discovery"])
            self.assertEqual(payload["run_triage_summary"]["question_ids_with_discovery"], [])
            self.assertEqual(payload["run_triage_summary"]["question_ids_with_fetch"], [])

    def test_runner_records_missing_artifacts_in_manifest_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            question_dir = output_dir / "synthetic_question"

            def _rewrite_bundle_missing_facet(bundle_dir, result, *, verdict=None, **_kwargs):
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={"commit": "abc123", "branch": "branch", "dirty": False},
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_fake_review_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle_missing_facet,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report_markdown",
                return_value="# Report\n",
            ):
                # Use topology intent so facet_coverage.json is expected
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                    intent_type="certificate_topology_analysis",
                )

                # Must not raise even when an artifact is missing
                run_root, manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            payload = json.loads((run_root / "pack_run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["question_runs"]), 1)
            run_summary = payload["question_runs"][0]
            # facet_coverage.json is expected for topology but was never written; it remains
            # missing even after the runner's rewrite of verdict.json / manual_review_report.md
            self.assertEqual(run_summary["missing_artifacts"], ["facet_coverage.json"])
            self.assertTrue(run_summary["has_missing_artifacts"])
            # artifacts_present and missing_artifacts are consistent: facet_coverage.json is absent
            self.assertNotIn("facet_coverage.json", run_summary["artifacts_present"])
            self.assertEqual(run_summary["final_judgment"], "reject")
            self.assertEqual(
                payload["run_triage_summary"]["question_ids_with_missing_artifacts"],
                ["synthetic_question"],
            )

    def test_question_verdict_encodes_missing_artifacts(self) -> None:
        question = SimpleNamespace(
            question_id="synthetic_question",
            expected_intent_type="synthetic_intent",
        )
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type="synthetic_intent"),
        )

        verdict = _build_question_verdict(
            question,
            result,
            missing_artifacts=["facet_coverage.json", "verdict.json"],
        )

        self.assertFalse(verdict.passed)
        self.assertIn("intent_type:synthetic_intent:ok", verdict.checks)
        self.assertTrue(
            any("required_artifacts:missing:" in c for c in verdict.checks),
            msg=f"Expected artifact-missing check in {verdict.checks}",
        )

    def test_runner_rejects_unknown_question_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)

            with self.assertRaisesRegex(
                ValueError,
                "Unknown real-question pack question_id: missing",
            ):
                run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="missing",
                    output_dir=repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run",
                )

    def test_runner_rejects_repo_root_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)

            with self.assertRaisesRegex(
                ValueError,
                "Real-question pack output_dir must not resolve to the repository root",
            ):
                run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=".",
                )

    def test_git_metadata_treats_unknown_status_as_dirty(self) -> None:
        with patch(
            "eubw_researcher.evaluation.git_metadata._run_git_command",
            side_effect=["branch-name", "commit-sha", None],
        ):
            metadata = collect_git_metadata(Path("/tmp/repo"))

        self.assertEqual(metadata["branch"], "branch-name")
        self.assertEqual(metadata["commit"], "commit-sha")
        self.assertTrue(metadata["dirty"])

    def test_question_verdict_does_not_encode_artifact_checks(self) -> None:
        question = SimpleNamespace(
            question_id="synthetic_question",
            expected_intent_type="synthetic_intent",
        )
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type="synthetic_intent"),
        )

        verdict = _build_question_verdict(question, result)

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.checks, ["intent_type:synthetic_intent:ok"])

    def test_runner_passes_review_artifact_to_write_artifact_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            question_dir = output_dir / "synthetic_question"
            captured_bundle_kwargs: dict = {}

            def _rewrite_bundle(bundle_dir, result, *, verdict=None, manual_review_report=None, **kwargs):
                captured_bundle_kwargs.update(kwargs)
                self._write_bundle_artifacts(bundle_dir, REAL_CORPUS_BUNDLE_ARTIFACTS)

            built_artifacts: list = []

            def _build_artifact(result, *, scenario_id=None):
                artifact = _fake_review_artifact(result, scenario_id=scenario_id)
                built_artifacts.append(artifact)
                return artifact

            def _build_report(_result, verdict, **_kwargs):
                return SimpleNamespace(
                    final_judgment="accept" if verdict.passed else "reject",
                    usefulness_verdict="accept",
                    source_bound_verdict="accept",
                    pinpoint_traceability_verdict="accept",
                    product_output_self_sufficiency_verdict="accept",
                )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={"commit": "abc123", "branch": "branch", "dirty": False},
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_artifact",
                side_effect=_build_artifact,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
                    repo_root=repo_root,
                )
                run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            # The artifact built for verdict gating must be the same object passed to
            # write_artifact_bundle, eliminating the double-build.
            self.assertEqual(len(built_artifacts), 1)
            self.assertIs(
                captured_bundle_kwargs.get("manual_review_artifact"),
                built_artifacts[0],
            )

    def test_question_verdict_encodes_failed_review_checks(self) -> None:
        question = SimpleNamespace(
            question_id="synthetic_question",
            expected_intent_type="synthetic_intent",
        )
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type="synthetic_intent"),
        )
        artifact = ManualReviewArtifact(
            question="Synthetic question?",
            scenario_id="synthetic_question",
            artifact_scope="synthetic_intent",
            filled=False,
            checks=[
                ManualReviewCheck(
                    check_id="blocked_claims_hidden",
                    status="fail",
                    evidence="Blocked content visible.",
                ),
                ManualReviewCheck(
                    check_id="approved_entries_have_citations",
                    status="pass",
                    evidence="All entries cited.",
                ),
            ],
            summary="1/2 checks passing.",
        )

        verdict = _build_question_verdict(question, result, review_artifact=artifact)

        self.assertFalse(verdict.passed)
        self.assertIn("review_check:blocked_claims_hidden:fail", verdict.checks)
        self.assertFalse(
            any("review_check:" in c and ":pass" in c for c in verdict.checks),
            msg="Passing review checks must not be encoded in the verdict",
        )

    def test_question_verdict_with_all_passing_review_checks_remains_passed(self) -> None:
        question = SimpleNamespace(
            question_id="synthetic_question",
            expected_intent_type="synthetic_intent",
        )
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type="synthetic_intent"),
        )
        artifact = ManualReviewArtifact(
            question="Synthetic question?",
            scenario_id="synthetic_question",
            artifact_scope="synthetic_intent",
            filled=False,
            checks=[
                ManualReviewCheck(
                    check_id="blocked_claims_hidden",
                    status="pass",
                    evidence="ok",
                ),
                ManualReviewCheck(
                    check_id="pinpoint_traceability",
                    status="pass",
                    evidence="ok",
                ),
            ],
            summary="2/2 checks passing.",
        )

        verdict = _build_question_verdict(question, result, review_artifact=artifact)

        self.assertTrue(verdict.passed)
        self.assertFalse(
            any("review_check:" in c for c in verdict.checks),
            msg="No review_check entries expected when all checks pass",
        )


if __name__ == "__main__":
    unittest.main()
