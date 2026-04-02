from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher import (
    AgentRuntimeMode,
    AgentRuntimeRequest,
    ResearchRuntimeFacade,
)


class RuntimeFacadeTests(unittest.TestCase):
    def _write_default_catalog(self, repo_root: Path) -> Path:
        catalog_path = repo_root / "artifacts" / "real_corpus" / "curated_catalog.json"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text("{}", encoding="utf-8")
        return catalog_path

    def _patched_result(self) -> SimpleNamespace:
        return SimpleNamespace(
            rendered_answer="Confirmed:\nSynthetic answer.",
            corpus_coverage_report=None,
        )

    def test_answer_question_route_returns_contract_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            catalog_path = self._write_default_catalog(repo_root)
            coverage_report = SimpleNamespace(passed=True)
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", coverage_report, "state-123"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls, patch.object(
                ResearchRuntimeFacade, "_write_artifact_bundle"
            ) as write_bundle:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).answer_question("  Synthetic question?  ")

            pipeline_cls.assert_called_once_with(
                runtime_config="runtime",
                hierarchy="hierarchy",
                allowlist="allowlist",
                ingestion_bundle="bundle",
            )
            pipeline_cls.return_value.answer_question.assert_called_once_with("Synthetic question?")
            write_bundle.assert_not_called()
            self.assertEqual(response.contract_version, "option_a_runtime.v1")
            self.assertEqual(response.mode, AgentRuntimeMode.ANSWER_QUESTION)
            self.assertEqual(response.catalog_path, catalog_path.resolve())
            self.assertIsNone(response.output_dir)
            self.assertEqual(response.corpus_state_id, "state-123")
            self.assertIs(response.result, result)
            self.assertIs(response.result.corpus_coverage_report, coverage_report)

    def test_write_reviewable_artifact_bundle_route_writes_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            catalog_path = self._write_default_catalog(repo_root)
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", None, "state-456"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls, patch.object(
                ResearchRuntimeFacade, "_write_artifact_bundle"
            ) as write_bundle:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).write_reviewable_artifact_bundle(
                    "Synthetic question?",
                    "artifacts/manual_runs/synthetic",
                )

            self.assertEqual(response.mode, AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE)
            self.assertEqual(
                response.output_dir,
                (repo_root / "artifacts" / "manual_runs" / "synthetic").resolve(),
            )
            write_bundle.assert_called_once_with(
                (repo_root / "artifacts" / "manual_runs" / "synthetic").resolve(),
                result,
                catalog_path=catalog_path.resolve(),
                corpus_state_id="state-456",
            )

    def test_evidence_only_route_sets_mode_without_writing_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            catalog_path = self._write_default_catalog(repo_root)
            coverage_report = SimpleNamespace(passed=True)
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", coverage_report, "state-789"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls, patch.object(
                ResearchRuntimeFacade, "_write_artifact_bundle"
            ) as write_bundle:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).run_evidence_only(
                    "Synthetic question?",
                    catalog_path=catalog_path,
                )

            pipeline_cls.return_value.answer_question.assert_called_once_with(
                "Synthetic question?"
            )
            write_bundle.assert_not_called()
            self.assertEqual(response.mode, AgentRuntimeMode.EVIDENCE_ONLY)
            self.assertEqual(response.catalog_path, catalog_path.resolve())
            self.assertIsNone(response.output_dir)
            self.assertEqual(response.corpus_state_id, "state-789")
            self.assertIs(response.result.corpus_coverage_report, coverage_report)

    def test_write_route_requires_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            facade = ResearchRuntimeFacade(tmp_dir)

            with self.assertRaisesRegex(
                ValueError,
                "output_dir is required for write_reviewable_artifact_bundle",
            ):
                facade.run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode=AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE,
                    )
                )

    def test_non_artifact_routes_reject_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            facade = ResearchRuntimeFacade(tmp_dir)

            with self.assertRaisesRegex(
                ValueError,
                "output_dir is only supported for write_reviewable_artifact_bundle",
            ):
                facade.run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode=AgentRuntimeMode.EVIDENCE_ONLY,
                        output_dir="artifacts/should_not_write",
                    )
                )

    def test_missing_catalog_raises_regular_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            facade = ResearchRuntimeFacade(tmp_dir)

            with self.assertRaisesRegex(FileNotFoundError, "Catalog file not found:"):
                facade.answer_question("Synthetic question?")

    def test_run_accepts_string_mode_from_request_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            catalog_path = self._write_default_catalog(repo_root)
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", None, "state-321"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode="answer_question",
                        catalog_path=catalog_path,
                    )
                )

            self.assertEqual(response.mode, AgentRuntimeMode.ANSWER_QUESTION)

    def test_run_rejects_unknown_string_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            facade = ResearchRuntimeFacade(tmp_dir)

            with self.assertRaisesRegex(ValueError, "unsupported_mode"):
                facade.run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode="unsupported_mode",
                    )
                )
