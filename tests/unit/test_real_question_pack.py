from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.evaluation.real_question_pack import (
    _build_question_verdict,
    default_real_question_pack_output_dir,
    _git_metadata,
    run_real_question_pack,
)


class RealQuestionPackRunnerTests(unittest.TestCase):
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
        intent_type: str = "synthetic_intent",
    ) -> SimpleNamespace:
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type=intent_type),
            approved_entries=[object(), object()],
            gap_records=[object()],
            web_fetch_records=[object(), object()],
            provisional_grouping=[],
            corpus_coverage_report=object(),
        )
        return SimpleNamespace(
            contract_version="option_a_runtime.v1",
            catalog_path=(output_dir.parents[3] / "artifacts" / "real_corpus" / "curated_catalog.json").resolve(),
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
                bundle_dir.mkdir(parents=True, exist_ok=True)
                for artifact_name in [
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
                ]:
                    (bundle_dir / artifact_name).write_text("{}", encoding="utf-8")

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
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir
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
            self.assertEqual(payload["runtime_contract_version"], "option_a_runtime.v1")
            self.assertEqual(payload["git_branch"], "codex/issue-8-real-question-pack")
            self.assertFalse(payload["git_dirty"])
            self.assertEqual(len(payload["question_runs"]), 1)
            self.assertEqual(payload["question_runs"][0]["final_judgment"], "accept")
            self.assertEqual(
                payload["question_runs"][0]["product_output_self_sufficiency_verdict"],
                "needs_follow_up",
            )
            self.assertEqual(payload["question_runs"][0]["missing_artifacts"], [])
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
                bundle_dir.mkdir(parents=True, exist_ok=True)
                for artifact_name in [
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
                ]:
                    (bundle_dir / artifact_name).write_text("{}", encoding="utf-8")

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
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir,
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
                bundle_dir.mkdir(parents=True, exist_ok=True)
                for artifact_name in [
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
                ]:
                    (bundle_dir / artifact_name).write_text("{}", encoding="utf-8")

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
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle,
            ):
                response = self._fake_response(question_dir, intent_type="synthetic_intent")
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

    def test_runner_records_missing_artifacts_in_manifest_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            question_dir = output_dir / "synthetic_question"

            def _rewrite_bundle_incomplete(bundle_dir, result, *, verdict=None, **_kwargs):
                bundle_dir.mkdir(parents=True, exist_ok=True)
                for artifact_name in [
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
                    # verdict.json intentionally omitted to simulate a missing artifact
                ]:
                    (bundle_dir / artifact_name).write_text("{}", encoding="utf-8")

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
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                side_effect=_build_report,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.write_artifact_bundle",
                side_effect=_rewrite_bundle_incomplete,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report_markdown",
                return_value="# Report\n",
            ):
                facade_cls.return_value.run_evidence_only.return_value = self._fake_response(
                    question_dir
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
            self.assertIn("verdict.json", run_summary["missing_artifacts"])
            self.assertEqual(run_summary["final_judgment"], "reject")

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
            "eubw_researcher.evaluation.real_question_pack._run_git_command",
            side_effect=["branch-name", "commit-sha", None],
        ):
            metadata = _git_metadata(Path("/tmp/repo"))

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


if __name__ == "__main__":
    unittest.main()
