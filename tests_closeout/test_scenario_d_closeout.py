from __future__ import annotations

import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.evaluation.closeout import (
    SCENARIO_D_ID,
    _build_spawned_validator_request,
    _invoke_spawned_validator,
    run_scenario_d_closeout,
)
from eubw_researcher.models import (
    AnchorQuality,
    AnswerAlignmentRecord,
    AnswerAlignmentReport,
    BlindValidationReport,
    CitationQuality,
    ClaimState,
    EvaluationScenario,
    NormalizationStatus,
    PinpointEvidenceRecord,
    PinpointEvidenceReport,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    WebFetchRecord,
    dataclass_to_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FAKE_VALIDATOR = (
    f"{shlex.quote(sys.executable)} "
    f"{shlex.quote(str(REPO_ROOT / 'tests_closeout' / 'fixtures' / 'fake_spawned_validator.py'))}"
)


def _minimal_result(record_type: str, *, intent_type: str) -> SimpleNamespace:
    entry = SimpleNamespace(
        claim_id="synthetic-claim",
        final_claim_state=ClaimState.CONFIRMED,
        citations=[
            SimpleNamespace(
                source_id="celex_32025R0848_fulltext_en",
                canonical_url=None,
                source_origin=SourceOrigin.LOCAL,
                source_role_level=SourceRoleLevel.HIGH,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
            ),
            SimpleNamespace(
                source_id="eudi_discussion_topic_x_rp_registration",
                canonical_url=None,
                source_origin=SourceOrigin.LOCAL,
                source_role_level=SourceRoleLevel.MEDIUM,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
            ),
        ],
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        governing_evidence=[],
        claim_text="Synthetic claim",
        source_role_level=SourceRoleLevel.HIGH,
        required_source_role_level=SourceRoleLevel.HIGH,
        support_directness=SimpleNamespace(value="direct"),
    )
    open_entry = SimpleNamespace(
        claim_id="synthetic-open",
        final_claim_state=ClaimState.INTERPRETIVE,
        citations=[entry.citations[0]],
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        governing_evidence=[],
        claim_text="Synthetic interpretive claim",
        source_role_level=SourceRoleLevel.HIGH,
        required_source_role_level=SourceRoleLevel.HIGH,
        support_directness=SimpleNamespace(value="direct"),
    )
    return SimpleNamespace(
        question="Synthetic topology question?",
        query_intent=SimpleNamespace(
            intent_type=intent_type,
            claim_targets=[],
        ),
        ledger_entries=[entry, open_entry, open_entry, entry],
        approved_entries=[entry, open_entry],
        rendered_answer=(
            "Not explicitly defined:\n"
            "- derived certificate\n\n"
            "Confirmed:\n- role statement\n\n"
            "Interpretive:\n- organisation-level certificate\n\n"
            "Open:\n- multiplicity remains interpretive\n"
        ),
        gap_records=[],
        web_fetch_records=[
            WebFetchRecord(
                sub_question="test",
                canonical_url="https://example.test/source",
                domain="example.test",
                allowed=True,
                source_kind=SourceKind.REGULATION,
                source_role_level=SourceRoleLevel.HIGH,
                jurisdiction="EU",
                retrieval_timestamp="2026-04-01T00:00:00+00:00",
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
                metadata_complete=True,
                reason="synthetic",
                record_type=record_type,
                content_type="text/html",
                normalization_status=NormalizationStatus.SUCCESS,
                content_digest="abc123",
                provenance_record="configured_seed_url",
            )
        ],
        retrieval_plan=SimpleNamespace(steps=[SimpleNamespace(source_kind="regulation")]),
        ingestion_report=[
            SimpleNamespace(
                source_id="synthetic",
                anchor_quality=AnchorQuality.STRONG,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
            )
        ],
        provisional_grouping=[],
        facet_coverage_report=SimpleNamespace(
            question="Synthetic topology question?",
            intent_type="certificate_topology_analysis",
            facets=[
                SimpleNamespace(facet_id="multiplicity_single_certificate", addressed=True, evidence=[]),
                SimpleNamespace(facet_id="derived_certificate_term_status", addressed=True, evidence=[]),
                SimpleNamespace(facet_id="registration_certificate_role", addressed=True, evidence=[]),
                SimpleNamespace(facet_id="access_certificate_role", addressed=True, evidence=[]),
                SimpleNamespace(facet_id="unresolved_or_interpretive_status", addressed=True, evidence=[]),
            ],
            all_addressed=lambda: True,
            by_id=lambda: {
                "multiplicity_single_certificate": SimpleNamespace(addressed=True, evidence=[]),
                "derived_certificate_term_status": SimpleNamespace(addressed=True, evidence=[]),
                "registration_certificate_role": SimpleNamespace(addressed=True, evidence=[]),
                "access_certificate_role": SimpleNamespace(addressed=True, evidence=[]),
                "unresolved_or_interpretive_status": SimpleNamespace(addressed=True, evidence=[]),
            },
        ),
        pinpoint_evidence_report=PinpointEvidenceReport(
            question="Synthetic topology question?",
            intent_type="certificate_topology_analysis",
            records=[
                PinpointEvidenceRecord(
                    answer_claim_id="synthetic-claim",
                    answer_section="Confirmed",
                    answer_claim_text="Synthetic claim",
                    source_id="celex_32025R0848_fulltext_en",
                    source_role_level=SourceRoleLevel.HIGH,
                    citation_quality=CitationQuality.ANCHOR_GROUNDED,
                    locator_type="heading_path",
                    locator_value="Article 1",
                    locator_precision="provision_level",
                    document_path=None,
                    canonical_url=None,
                    limitation_note=None,
                )
            ],
            all_cited_evidence_mapped=True,
            missing_citation_claim_ids=[],
        ),
        answer_alignment_report=AnswerAlignmentReport(
            question="Synthetic topology question?",
            intent_type="certificate_topology_analysis",
            records=[
                AnswerAlignmentRecord(
                    answer_claim_id="term-status",
                    answer_section="Not explicitly defined",
                    wording_category="term_status_scan",
                    claim_ids=[],
                    claim_states=[],
                    cited_source_ids=["celex_32025R0848_fulltext_en"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                ),
                AnswerAlignmentRecord(
                    answer_claim_id="interpretive",
                    answer_section="Interpretive",
                    wording_category="interpretive_governing_boundary",
                    claim_ids=["synthetic-claim"],
                    claim_states=[ClaimState.INTERPRETIVE],
                    cited_source_ids=["celex_32025R0848_fulltext_en"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                ),
                AnswerAlignmentRecord(
                    answer_claim_id="open",
                    answer_section="Open",
                    wording_category="open_state_forwarded",
                    claim_ids=["synthetic-open"],
                    claim_states=[ClaimState.OPEN],
                    cited_source_ids=["eudi_discussion_topic_x_rp_registration"],
                    cited_source_roles=[SourceRoleLevel.MEDIUM],
                ),
            ],
            blocking_violations=[],
        ),
        blind_validation_report=BlindValidationReport(
            question="Synthetic topology question?",
            intent_type="certificate_topology_analysis",
            validation_mode="structural_product_output_contract_check",
            artifacts_used=[
                "final_answer.txt",
                "approved_ledger.json",
                "pinpoint_evidence.json",
                "answer_alignment.json",
                "facet_coverage.json",
            ],
            raw_document_reads=[],
            raw_document_dependency="none",
            structural_passed=True,
            product_output_self_sufficient=True,
            passed=True,
            summary="Structural blind validation passes.",
            missing_facets=[],
        ),
        corpus_coverage_report=None,
    )


def _fake_write_artifact_bundle(output_dir: Path, result, verdict=None, **_: object) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in [
        "final_answer.txt",
        "approved_ledger.json",
        "facet_coverage.json",
        "pinpoint_evidence.json",
        "answer_alignment.json",
        "manual_review_report.md",
    ]:
        (output_dir / filename).write_text("synthetic\n", encoding="utf-8")
    (output_dir / "blind_validation_report.json").write_text(
        json.dumps(dataclass_to_dict(result.blind_validation_report), indent=2),
        encoding="utf-8",
    )
    if verdict is not None:
        (output_dir / "verdict.json").write_text(
            json.dumps(dataclass_to_dict(verdict), indent=2),
            encoding="utf-8",
        )


class _DummyPipeline:
    def __init__(self, result: SimpleNamespace) -> None:
        self._result = result

    def answer_question(self, question: str) -> SimpleNamespace:
        return self._result


class ScenarioDCloseoutTests(unittest.TestCase):
    def test_invoke_spawned_validator_accepts_minor_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode minor_confirmation",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertTrue(result.passed)
            self.assertEqual(result.raw_document_dependency, "minor_confirmation")
            self.assertFalse(result.context_inherited)

    def test_invoke_spawned_validator_rejects_nonzero_exit_even_with_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode nonzero",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertEqual(result.exit_code, 3)
            self.assertIn("non-zero exit", result.error)

    def test_invoke_spawned_validator_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --sleep-seconds 1.0",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=0.01,
            )

            self.assertFalse(result.passed)
            self.assertIn("timed out", result.error)

    def test_invoke_spawned_validator_rejects_invalid_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode invalid_json",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("valid JSON", result.error)

    def test_invoke_spawned_validator_rejects_non_utf8_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode non_utf8",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("UTF-8", result.error)

    def test_invoke_spawned_validator_rejects_partial_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode partial_json",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("valid JSON", result.error)

    def test_invoke_spawned_validator_rejects_unparseable_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command='python3 "unterminated',
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("could not be parsed", result.error)

    def test_invoke_spawned_validator_rejects_string_booleans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode string_bools",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("must be a boolean", result.error)

    def test_invoke_spawned_validator_rejects_bad_document_path_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode bad_document_path",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("document_path must be a string", result.error)

    def test_invoke_spawned_validator_rejects_missing_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command="definitely-not-a-real-validator-binary",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("could not be started", result.error)

    def test_invoke_spawned_validator_does_not_accept_stale_result_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )
            output_path.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "context_inherited": False,
                        "artifacts_used": [],
                        "raw_document_dependency": "none",
                        "product_output_self_sufficient": True,
                        "summary": "stale",
                        "validator_answer": "stale",
                    }
                ),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode no_output",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertFalse(result.passed)
            self.assertIn("did not write", result.error)

    def test_invoke_spawned_validator_can_echo_request_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            request_path = tmp_path / "request.json"
            output_path = tmp_path / "result.json"
            request_path.write_text(
                json.dumps(_build_spawned_validator_request(tmp_path, "Synthetic question?"), indent=2),
                encoding="utf-8",
            )

            result = _invoke_spawned_validator(
                repo_root=REPO_ROOT,
                validator_command=f"{FAKE_VALIDATOR} --mode echo_request",
                request_path=request_path,
                result_path=output_path,
                timeout_seconds=10.0,
            )

            self.assertTrue(result.passed)
            self.assertIsNotNone(result.notes)
            echoed_request = json.loads(result.notes)
            self.assertIn("instructions", echoed_request)
            self.assertIn("prohibited", echoed_request)
            self.assertIn("required_artifacts", echoed_request)

    def test_run_scenario_d_closeout_skips_validator_when_deterministic_gate_fails(self) -> None:
        failing_result = _minimal_result("fetch", intent_type="wrong_intent")
        scenario = EvaluationScenario(
            scenario_id=SCENARIO_D_ID,
            question="Synthetic topology question?",
            expectation="Synthetic Scenario D closeout.",
            required_intent_type="certificate_topology_analysis",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            with patch("eubw_researcher.evaluation.closeout._scenario_config_path", return_value=Path("synthetic.json")), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    _DummyPipeline(failing_result),
                    None,
                    "synthetic-state",
                    Path("/tmp/synthetic_catalog.json"),
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle",
                side_effect=_fake_write_artifact_bundle,
            ):
                scenario_dir, verdict = run_scenario_d_closeout(
                    repo_root=REPO_ROOT,
                    output_dir=output_root,
                    validator_command=f"{FAKE_VALIDATOR} --mode pass",
                    timeout_seconds=10.0,
                    catalog_path=Path("/tmp/synthetic_catalog.json"),
                )

            self.assertFalse(verdict.passed)
            self.assertIn("spawned_validator:skipped_deterministic_gate_failed", verdict.checks)
            self.assertFalse((scenario_dir / "spawned_validator_request.json").exists())

    def test_run_scenario_d_closeout_writes_merged_blind_validation_report(self) -> None:
        passing_result = _minimal_result("fetch", intent_type="certificate_topology_analysis")
        scenario = EvaluationScenario(
            scenario_id=SCENARIO_D_ID,
            question="Synthetic topology question?",
            expectation="Synthetic Scenario D closeout.",
            required_intent_type="certificate_topology_analysis",
            required_states=[ClaimState.CONFIRMED, ClaimState.INTERPRETIVE],
            allowed_states=[ClaimState.CONFIRMED, ClaimState.INTERPRETIVE],
            required_sources=[
                "celex_32025R0848_fulltext_en",
                "eudi_discussion_topic_x_rp_registration",
            ],
            required_answer_substrings=[
                "Not explicitly defined:",
                "derived certificate",
                "Interpretive:",
                "Open:",
                "organisation-level certificate",
            ],
            forbidden_answer_substrings=["Blocked:"],
            require_manual_review_accept=True,
            min_ledger_entries=4,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            with patch("eubw_researcher.evaluation.closeout._scenario_config_path", return_value=Path("synthetic.json")), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    _DummyPipeline(passing_result),
                    None,
                    "synthetic-state",
                    Path("/tmp/synthetic_catalog.json"),
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle",
                side_effect=_fake_write_artifact_bundle,
            ):
                scenario_dir, verdict = run_scenario_d_closeout(
                    repo_root=REPO_ROOT,
                    output_dir=output_root,
                    validator_command=f"{FAKE_VALIDATOR} --mode minor_confirmation",
                    timeout_seconds=10.0,
                    catalog_path=Path("/tmp/synthetic_catalog.json"),
                )

            self.assertTrue(verdict.passed, msg=verdict.checks)
            self.assertTrue((scenario_dir / "spawned_validator_request.json").exists())
            self.assertTrue((scenario_dir / "spawned_validator_result.json").exists())
            blind_validation = json.loads(
                (scenario_dir / "blind_validation_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                blind_validation["validation_mode"],
                "structural_plus_spawned_validator_closeout",
            )
            self.assertEqual(blind_validation["raw_document_dependency"], "minor_confirmation")
            self.assertTrue(blind_validation["passed"])
            self.assertIn("spawned_validator", blind_validation)

    def test_run_scenario_d_closeout_fails_when_validator_reports_inherited_context(self) -> None:
        passing_result = _minimal_result("fetch", intent_type="certificate_topology_analysis")
        scenario = EvaluationScenario(
            scenario_id=SCENARIO_D_ID,
            question="Synthetic topology question?",
            expectation="Synthetic Scenario D closeout.",
            required_intent_type="certificate_topology_analysis",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            with patch("eubw_researcher.evaluation.closeout._scenario_config_path", return_value=Path("synthetic.json")), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    _DummyPipeline(passing_result),
                    None,
                    "synthetic-state",
                    Path("/tmp/synthetic_catalog.json"),
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle",
                side_effect=_fake_write_artifact_bundle,
            ):
                scenario_dir, verdict = run_scenario_d_closeout(
                    repo_root=REPO_ROOT,
                    output_dir=output_root,
                    validator_command=f"{FAKE_VALIDATOR} --mode inherited_context",
                    timeout_seconds=10.0,
                    catalog_path=Path("/tmp/synthetic_catalog.json"),
                )

            self.assertFalse(verdict.passed)
            self.assertIn("spawned_validator_context_inherited:false:fail", verdict.checks)
            blind_validation = json.loads(
                (scenario_dir / "blind_validation_report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(blind_validation["passed"])
            self.assertTrue(blind_validation["spawned_validator"]["context_inherited"])

    def test_run_scenario_d_closeout_fails_when_validator_requires_central_reconstruction(self) -> None:
        passing_result = _minimal_result("fetch", intent_type="certificate_topology_analysis")
        scenario = EvaluationScenario(
            scenario_id=SCENARIO_D_ID,
            question="Synthetic topology question?",
            expectation="Synthetic Scenario D closeout.",
            required_intent_type="certificate_topology_analysis",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            with patch("eubw_researcher.evaluation.closeout._scenario_config_path", return_value=Path("synthetic.json")), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    _DummyPipeline(passing_result),
                    None,
                    "synthetic-state",
                    Path("/tmp/synthetic_catalog.json"),
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle",
                side_effect=_fake_write_artifact_bundle,
            ):
                scenario_dir, verdict = run_scenario_d_closeout(
                    repo_root=REPO_ROOT,
                    output_dir=output_root,
                    validator_command=f"{FAKE_VALIDATOR} --mode central_reconstruction",
                    timeout_seconds=10.0,
                    catalog_path=Path("/tmp/synthetic_catalog.json"),
                )

            self.assertFalse(verdict.passed)
            self.assertIn(
                "spawned_validator_raw_document_dependency:central_reconstruction:fail",
                verdict.checks,
            )
            blind_validation = json.loads(
                (scenario_dir / "blind_validation_report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(blind_validation["passed"])
            self.assertEqual(
                blind_validation["spawned_validator"]["raw_document_dependency"],
                "central_reconstruction",
            )

    def test_run_scenario_d_closeout_writes_bundle_before_invoking_validator(self) -> None:
        passing_result = _minimal_result("fetch", intent_type="certificate_topology_analysis")
        scenario = EvaluationScenario(
            scenario_id=SCENARIO_D_ID,
            question="Synthetic topology question?",
            expectation="Synthetic Scenario D closeout.",
            required_intent_type="certificate_topology_analysis",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            with patch("eubw_researcher.evaluation.closeout._scenario_config_path", return_value=Path("synthetic.json")), patch(
                "eubw_researcher.evaluation.closeout.load_evaluation_scenarios",
                return_value=[scenario],
            ), patch(
                "eubw_researcher.evaluation.closeout._run_pipeline",
                return_value=(
                    _DummyPipeline(passing_result),
                    None,
                    "synthetic-state",
                    Path("/tmp/synthetic_catalog.json"),
                ),
            ), patch(
                "eubw_researcher.evaluation.closeout.write_artifact_bundle",
                side_effect=_fake_write_artifact_bundle,
            ):
                _, verdict = run_scenario_d_closeout(
                    repo_root=REPO_ROOT,
                    output_dir=output_root,
                    validator_command=f"{FAKE_VALIDATOR} --mode assert_bundle_ready",
                    timeout_seconds=10.0,
                    catalog_path=Path("/tmp/synthetic_catalog.json"),
                )

            self.assertTrue(verdict.passed, msg=verdict.checks)


if __name__ == "__main__":
    unittest.main()
