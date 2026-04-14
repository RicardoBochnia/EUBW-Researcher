from __future__ import annotations

import importlib
import re
import tempfile
import typing
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher import (
    AgentRuntimeMode,
    AgentRuntimeRequest,
    AgentRuntimeResult,
    ResearchRuntimeFacade,
)
from eubw_researcher.models import CorpusCoverageFamily, CorpusCoverageReport

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = REPO_ROOT / "configs" / "runtime.scan.yaml"


class RuntimeFacadeTests(unittest.TestCase):
    def test_package_root_exports_only_runtime_facade_contract(self) -> None:
        package = importlib.import_module("eubw_researcher")

        self.assertEqual(
            package.__all__,
            [
                "AgentRuntimeMode",
                "AgentRuntimeRequest",
                "AgentRuntimeResult",
                "AgentRuntimeResponse",
                "ResearchRuntimeFacade",
            ],
        )
        self.assertFalse(hasattr(package, "ResearchPipeline"))

    def test_public_response_annotation_uses_stable_runtime_result_type(self) -> None:
        response_hints = typing.get_type_hints(importlib.import_module("eubw_researcher.runtime_facade").AgentRuntimeResponse)

        self.assertIs(response_hints["result"], AgentRuntimeResult)

    def _write_default_catalog(self, repo_root: Path) -> Path:
        catalog_path = repo_root / "artifacts" / "real_corpus" / "curated_catalog.json"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text("{}", encoding="utf-8")
        return catalog_path

    def _patched_result(self) -> SimpleNamespace:
        return SimpleNamespace(
            question="Synthetic question?",
            query_intent=SimpleNamespace(intent_type="synthetic_intent"),
            retrieval_plan=SimpleNamespace(
                question="Synthetic question?",
                normalized_question="Synthetic question?",
                question_term_normalizations=[],
                target_queries=[],
                steps=[],
            ),
            gap_records=[],
            web_fetch_records=[],
            ingestion_report=[],
            ledger_entries=[],
            approved_entries=[],
            rendered_answer="Confirmed:\nSynthetic answer.",
            provisional_grouping=[],
            facet_coverage_report=None,
            pinpoint_evidence_report=None,
            answer_alignment_report=None,
            blind_validation_report=None,
            corpus_coverage_report=None,
        )

    def _coverage_report(self) -> CorpusCoverageReport:
        return CorpusCoverageReport(
            catalog_path="/tmp/catalog.json",
            corpus_state_id="state-from-report",
            generation_timestamp="2026-04-04T14:00:00+00:00",
            admitted_source_counts_by_kind={"specification": 1},
            families=[
                CorpusCoverageFamily(
                    family_id="wallet_requirements",
                    minimum_count=1,
                    admitted_count=1,
                    admitted_source_ids=["source-1"],
                    missing=False,
                )
            ],
            passed=True,
        )

    def test_answer_question_route_returns_contract_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            catalog_path = self._write_default_catalog(repo_root)
            coverage_report = self._coverage_report()
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_terminology_config",
                return_value="terminology",
            ), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", coverage_report, "state-123"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls, patch.object(
                ResearchRuntimeFacade, "_write_artifact_bundle"
            ) as write_bundle:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).answer_question(
                    "  Synthetic question?  ",
                    runtime_config_path=RUNTIME_CONFIG_PATH,
                )

            pipeline_cls.assert_called_once_with(
                runtime_config="runtime",
                hierarchy="hierarchy",
                allowlist="allowlist",
                ingestion_bundle="bundle",
                terminology="terminology",
                catalog_path=catalog_path.resolve(),
                corpus_state_id="state-123",
            )
            pipeline_cls.return_value.answer_question.assert_called_once_with("Synthetic question?")
            write_bundle.assert_not_called()
            self.assertEqual(response.contract_version, "option_a_runtime.v2")
            self.assertEqual(response.result_schema_version, "agent_runtime_result.v3")
            self.assertEqual(response.mode, AgentRuntimeMode.ANSWER_QUESTION)
            self.assertEqual(response.catalog_path, catalog_path.resolve())
            self.assertIsNone(response.output_dir)
            self.assertEqual(response.corpus_state_id, "state-123")
            self.assertIsInstance(response.result, AgentRuntimeResult)
            self.assertEqual(response.result.question, "Synthetic question?")
            self.assertEqual(response.result.query_intent.intent_type, "synthetic_intent")
            self.assertEqual(response.result.rendered_answer, "Confirmed:\nSynthetic answer.")
            self.assertIsInstance(response.result.corpus_coverage_report, CorpusCoverageReport)
            self.assertTrue(response.result.corpus_coverage_report.passed)

    def test_write_reviewable_artifact_bundle_route_writes_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            catalog_path = self._write_default_catalog(repo_root)
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_terminology_config",
                return_value="terminology",
            ), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", None, "state-456"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls, patch.object(
                ResearchRuntimeFacade, "_write_artifact_bundle"
            ) as write_bundle:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).write_reviewable_artifact_bundle(
                    "Synthetic question?",
                    "artifacts/manual_runs/synthetic",
                    runtime_config_path=RUNTIME_CONFIG_PATH,
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
            coverage_report = self._coverage_report()
            result = self._patched_result()

            with patch("eubw_researcher.runtime_facade.load_runtime_config", return_value="runtime"), patch(
                "eubw_researcher.runtime_facade.load_source_hierarchy",
                return_value="hierarchy",
            ), patch("eubw_researcher.runtime_facade.load_web_allowlist", return_value="allowlist"), patch(
                "eubw_researcher.runtime_facade.load_terminology_config",
                return_value="terminology",
            ), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", coverage_report, "state-789"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls, patch.object(
                ResearchRuntimeFacade, "_write_artifact_bundle"
            ) as write_bundle:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).run_evidence_only(
                    "Synthetic question?",
                    catalog_path=catalog_path,
                    runtime_config_path=RUNTIME_CONFIG_PATH,
                )

            pipeline_cls.return_value.answer_question.assert_called_once_with(
                "Synthetic question?"
            )
            write_bundle.assert_not_called()
            self.assertEqual(response.mode, AgentRuntimeMode.EVIDENCE_ONLY)
            self.assertEqual(response.catalog_path, catalog_path.resolve())
            self.assertIsNone(response.output_dir)
            self.assertEqual(response.corpus_state_id, "state-789")
            self.assertIsInstance(response.result, AgentRuntimeResult)
            self.assertIsInstance(response.result.corpus_coverage_report, CorpusCoverageReport)
            self.assertTrue(response.result.corpus_coverage_report.passed)

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

    def test_write_route_rejects_blank_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            facade = ResearchRuntimeFacade(tmp_dir)

            with self.assertRaisesRegex(ValueError, "output_dir must not be empty"):
                facade.run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode=AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE,
                        output_dir="   ",
                    )
                )

    def test_write_route_rejects_repo_root_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            facade = ResearchRuntimeFacade(tmp_dir)

            with self.assertRaisesRegex(
                ValueError, "output_dir must not resolve to the repository root"
            ):
                facade.run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode=AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE,
                        output_dir=".",
                    )
                )

    def test_write_route_rejects_output_dir_that_is_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            output_file = repo_root / "existing_output.txt"
            output_file.write_text("not a directory", encoding="utf-8")
            facade = ResearchRuntimeFacade(repo_root)

            with self.assertRaisesRegex(
                ValueError,
                re.escape(f"output_dir must be a directory path: {output_file.resolve()}"),
            ):
                facade.run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode=AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE,
                        output_dir=output_file,
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
                "eubw_researcher.runtime_facade.load_terminology_config",
                return_value="terminology",
            ), patch(
                "eubw_researcher.runtime_facade.load_or_build_ingestion_bundle",
                return_value=(None, "bundle", None, "state-321"),
            ), patch("eubw_researcher.runtime_facade.ResearchPipeline") as pipeline_cls:
                pipeline_cls.return_value.answer_question.return_value = result

                response = ResearchRuntimeFacade(repo_root).run(
                    AgentRuntimeRequest(
                        question="Synthetic question?",
                        mode="answer_question",
                        catalog_path=catalog_path,
                        runtime_config_path=RUNTIME_CONFIG_PATH,
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
