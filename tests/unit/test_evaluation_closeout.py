from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.evaluation.closeout import (
    SCENARIO_D_ID,
    _append_corpus_coverage_gate,
    _build_closeout_verdict,
    _clear_closeout_sidecar_files,
    _invoke_spawned_validator,
    _parse_spawned_validator_payload,
    default_closeout_output_dir,
    run_scenario_d_closeout,
)
from eubw_researcher.models import (
    BlindValidationRawRead,
    BlindValidationReport,
    CorpusCoverageFamily,
    CorpusCoverageReport,
    EvaluationScenario,
    ScenarioVerdict,
    SpawnedValidatorResult,
)

RUNTIME_CONFIG_PATH = Path("/tmp/repo/configs/runtime.scan.yaml")
RUNTIME_CONFIG_DIGEST = "runtime-digest"
LOCAL_RETRIEVAL_BACKEND = "scan"


def _coverage_report(passed: bool) -> CorpusCoverageReport:
    return CorpusCoverageReport(
        catalog_path="/tmp/catalog.json",
        corpus_state_id="synthetic-state",
        generation_timestamp="2026-04-04T00:00:00+00:00",
        admitted_source_counts_by_kind={"regulation": 1},
        families=[
            CorpusCoverageFamily(
                family_id="synthetic-family",
                minimum_count=1,
                admitted_count=1 if passed else 0,
                admitted_source_ids=["source-a"] if passed else [],
                missing=not passed,
            )
        ],
        passed=passed,
    )


def _blind_validation_report(passed: bool = True) -> BlindValidationReport:
    return BlindValidationReport(
        question="Synthetic question?",
        intent_type="certificate_topology_analysis",
        validation_mode="structural_product_output_contract_check",
        artifacts_used=["final_answer.txt", "approved_ledger.json"],
        raw_document_dependency="none" if passed else "central_reconstruction",
        structural_passed=passed,
        product_output_self_sufficient=passed,
        passed=passed,
        summary="Synthetic blind validation report.",
    )


def _spawned_validator_result(**overrides: object) -> SpawnedValidatorResult:
    payload = dict(
        passed=True,
        context_inherited=False,
        artifacts_used=["manual_review_report.md"],
        raw_document_reads=[],
        raw_document_dependency="none",
        product_output_self_sufficient=True,
        summary="Validator reused the generated bundle.",
        validator_answer="Synthetic validator answer.",
        validator_command="python validator.py",
        exit_code=0,
        stdout="validator stdout",
        stderr="",
        error=None,
    )
    payload.update(overrides)
    return SpawnedValidatorResult(**payload)


class CloseoutTests(unittest.TestCase):
    def test_default_closeout_output_dir_uses_standard_artifact_path(self) -> None:
        repo_root = Path("/tmp/repo")
        self.assertEqual(
            default_closeout_output_dir(repo_root),
            repo_root / "artifacts" / "scenario_d_closeout",
        )

    def test_append_corpus_coverage_gate_fails_when_report_fails(self) -> None:
        verdict = _append_corpus_coverage_gate(
            ScenarioVerdict(scenario_id=SCENARIO_D_ID, passed=True, checks=["deterministic:ok"]),
            _coverage_report(False),
        )

        self.assertFalse(verdict.passed)
        self.assertEqual(
            verdict.checks,
            ["deterministic:ok", "corpus_coverage_gate:fail"],
        )

    def test_clear_closeout_sidecar_files_removes_request_and_result_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario_dir = Path(temp_dir)
            for filename in ["spawned_validator_request.json", "spawned_validator_result.json"]:
                (scenario_dir / filename).write_text("{}", encoding="utf-8")

            _clear_closeout_sidecar_files(scenario_dir)

            self.assertFalse((scenario_dir / "spawned_validator_request.json").exists())
            self.assertFalse((scenario_dir / "spawned_validator_result.json").exists())

    def test_parse_spawned_validator_payload_normalizes_raw_document_reads(self) -> None:
        result = _parse_spawned_validator_payload(
            {
                "passed": True,
                "context_inherited": False,
                "artifacts_used": ["final_answer.txt", "manual_review_report.md"],
                "raw_document_reads": [
                    {
                        "source_id": "source-a",
                        "document_path": "/tmp/source-a.txt",
                        "purpose": "confirm citation",
                        "classification": "minor_confirmation",
                    }
                ],
                "raw_document_dependency": "minor_confirmation",
                "product_output_self_sufficient": True,
                "summary": "Validator reused the bundle with one spot-check.",
                "validator_answer": "Synthetic validator answer.",
                "notes": "One citation was double-checked.",
            },
            validator_command="python validator.py",
            exit_code=0,
            stdout=b"validator stdout",
            stderr=b"",
        )

        self.assertEqual(result.raw_document_dependency, "minor_confirmation")
        self.assertEqual(result.stdout, "validator stdout")
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.raw_document_reads,
            [
                BlindValidationRawRead(
                    source_id="source-a",
                    document_path=Path("/tmp/source-a.txt"),
                    purpose="confirm citation",
                    classification="minor_confirmation",
                )
            ],
        )

    def test_parse_spawned_validator_payload_rejects_invalid_contract_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "raw_document_dependency must be one of"):
            _parse_spawned_validator_payload(
                {
                    "passed": True,
                    "context_inherited": False,
                    "artifacts_used": ["final_answer.txt"],
                    "raw_document_dependency": "full_reconstruction",
                    "product_output_self_sufficient": True,
                    "summary": "Synthetic summary.",
                    "validator_answer": "Synthetic answer.",
                },
                validator_command="python validator.py",
                exit_code=0,
                stdout="",
                stderr="",
            )

    def test_invoke_spawned_validator_handles_timeouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            result_path = Path(temp_dir) / "result.json"
            request_path.write_text("{}", encoding="utf-8")
            timeout = subprocess.TimeoutExpired(
                cmd=["python", "validator.py"],
                timeout=5.0,
                output=b"partial stdout",
                stderr=b"partial stderr",
            )
            with patch(
                "eubw_researcher.evaluation.closeout.subprocess.run",
                side_effect=timeout,
            ):
                result = _invoke_spawned_validator(
                    repo_root=Path(temp_dir),
                    validator_command="python validator.py",
                    request_path=request_path,
                    result_path=result_path,
                    timeout_seconds=5.0,
                )

        self.assertFalse(result.passed)
        self.assertEqual(result.stdout, "partial stdout")
        self.assertEqual(result.stderr, "partial stderr")
        self.assertIn("timed out", result.error or "")

    def test_invoke_spawned_validator_rejects_non_zero_exit_even_with_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            result_path = Path(temp_dir) / "result.json"
            request_path.write_text("{}", encoding="utf-8")
            payload = {
                "passed": True,
                "context_inherited": False,
                "artifacts_used": ["final_answer.txt"],
                "raw_document_dependency": "none",
                "product_output_self_sufficient": True,
                "summary": "Synthetic summary.",
                "validator_answer": "Synthetic answer.",
            }
            completed = subprocess.CompletedProcess(
                args=["python", "validator.py"],
                returncode=2,
                stdout=b"",
                stderr=b"validator stderr",
            )

            def _mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
                result_path.write_text(json.dumps(payload), encoding="utf-8")
                return completed

            with patch(
                "eubw_researcher.evaluation.closeout.subprocess.run",
                side_effect=_mock_run,
            ):
                result = _invoke_spawned_validator(
                    repo_root=Path(temp_dir),
                    validator_command="python validator.py",
                    request_path=request_path,
                    result_path=result_path,
                    timeout_seconds=5.0,
                )

        self.assertFalse(result.passed)
        self.assertEqual(result.exit_code, 2)
        self.assertIn("non-zero exit is a closeout failure", result.error or "")

    def test_build_closeout_verdict_marks_unknowns_when_validator_output_contract_fails(self) -> None:
        verdict = _build_closeout_verdict(
            ScenarioVerdict(scenario_id=SCENARIO_D_ID, passed=True, checks=["deterministic:ok"]),
            _blind_validation_report(passed=False),
            _spawned_validator_result(
                passed=False,
                exit_code=None,
                error="Validator output file did not contain valid JSON.",
            ),
        )

        self.assertFalse(verdict.passed)
        self.assertIn("spawned_validator_output_contract:fail", verdict.checks)
        self.assertIn("spawned_validator_context_inherited:unknown", verdict.checks)
        self.assertIn("blind_validation_closeout:fail", verdict.checks)

    def test_run_scenario_d_closeout_skips_spawned_validator_when_deterministic_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            output_dir = repo_root / "artifacts"
            scenario = EvaluationScenario(
                scenario_id=SCENARIO_D_ID,
                question="Synthetic question?",
                expectation="Synthetic expectation.",
            )
            result = SimpleNamespace(
                blind_validation_report=None,
                corpus_coverage_report=None,
            )
            pipeline = SimpleNamespace(answer_question=lambda question: result)
            with patch(
                "eubw_researcher.evaluation.closeout._scenario_config_path",
                return_value=repo_root / "configs" / "eval.json",
            ), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    pipeline,
                    None,
                    "synthetic-state",
                    repo_root / "catalog.json",
                    RUNTIME_CONFIG_PATH,
                    RUNTIME_CONFIG_DIGEST,
                    LOCAL_RETRIEVAL_BACKEND,
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout._evaluate_scenario",
                return_value=ScenarioVerdict(
                    scenario_id=SCENARIO_D_ID,
                    passed=False,
                    checks=["deterministic:fail"],
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.build_blind_validation_report",
                return_value=_blind_validation_report(),
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle"
            ) as write_artifact_bundle, patch(
                "eubw_researcher.evaluation.closeout._invoke_spawned_validator"
            ) as invoke_spawned_validator:
                scenario_dir, verdict = run_scenario_d_closeout(
                    repo_root=repo_root,
                    output_dir=output_dir,
                    validator_command="python validator.py",
                    timeout_seconds=5.0,
                )

        self.assertEqual(scenario_dir, output_dir / SCENARIO_D_ID)
        self.assertFalse(verdict.passed)
        self.assertIn("spawned_validator:skipped_deterministic_gate_failed", verdict.checks)
        invoke_spawned_validator.assert_not_called()
        write_artifact_bundle.assert_called_once()

    def test_run_scenario_d_closeout_writes_validator_sidecars_and_rewrites_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            output_dir = repo_root / "artifacts"
            scenario = EvaluationScenario(
                scenario_id=SCENARIO_D_ID,
                question="Synthetic question?",
                expectation="Synthetic expectation.",
            )
            structural_report = _blind_validation_report()
            merged_report = BlindValidationReport(
                question="Synthetic question?",
                intent_type="certificate_topology_analysis",
                validation_mode="structural_plus_spawned_validator_closeout",
                artifacts_used=["final_answer.txt", "approved_ledger.json", "manual_review_report.md"],
                raw_document_dependency="none",
                structural_passed=True,
                product_output_self_sufficient=True,
                passed=True,
                summary="Synthetic merged closeout pass.",
            )
            result = SimpleNamespace(
                blind_validation_report=None,
                corpus_coverage_report=None,
            )
            pipeline = SimpleNamespace(answer_question=lambda question: result)
            spawned_validator = _spawned_validator_result()
            with patch(
                "eubw_researcher.evaluation.closeout._scenario_config_path",
                return_value=repo_root / "configs" / "eval.json",
            ), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    pipeline,
                    _coverage_report(True),
                    "synthetic-state",
                    repo_root / "catalog.json",
                    RUNTIME_CONFIG_PATH,
                    RUNTIME_CONFIG_DIGEST,
                    LOCAL_RETRIEVAL_BACKEND,
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout._evaluate_scenario",
                return_value=ScenarioVerdict(
                    scenario_id=SCENARIO_D_ID,
                    passed=True,
                    checks=["deterministic:ok"],
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.build_blind_validation_report",
                return_value=structural_report,
            ), patch(
                "eubw_researcher.evaluation.closeout._invoke_spawned_validator",
                return_value=spawned_validator,
            ), patch(
                "eubw_researcher.evaluation.closeout.merge_spawned_validator_result",
                return_value=merged_report,
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle"
            ) as write_artifact_bundle:
                scenario_dir, verdict = run_scenario_d_closeout(
                    repo_root=repo_root,
                    output_dir=output_dir,
                    validator_command="python validator.py",
                    timeout_seconds=5.0,
                )

                request_path = scenario_dir / "spawned_validator_request.json"
                result_path = scenario_dir / "spawned_validator_result.json"
                request_payload = json.loads(request_path.read_text(encoding="utf-8"))
                written_result = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertTrue(verdict.passed)
        self.assertEqual(scenario_dir, output_dir / SCENARIO_D_ID)
        self.assertEqual(request_payload["question"], "Synthetic question?")
        self.assertIn("manual_review_report.md", request_payload["required_artifacts"])
        self.assertEqual(written_result["validator_answer"], "Synthetic validator answer.")
        self.assertEqual(write_artifact_bundle.call_count, 2)
