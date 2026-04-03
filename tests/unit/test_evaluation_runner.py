from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from eubw_researcher.evaluation.review import (
    build_manual_review_artifact,
    build_manual_review_report,
    build_manual_review_report_markdown,
)
from eubw_researcher.evaluation.runner import _evaluate_scenario, write_artifact_bundle
from eubw_researcher.models import (
    CorpusCoverageFamily,
    CorpusCoverageReport,
    RetrievalPlan,
    AnchorQuality,
    AnswerAlignmentRecord,
    AnswerAlignmentReport,
    BlindValidationReport,
    CitationQuality,
    ClaimState,
    EvaluationScenario,
    FacetCoverageFacet,
    FacetCoverageReport,
    NormalizationStatus,
    PinpointEvidenceRecord,
    PinpointEvidenceReport,
    ScenarioVerdict,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    SpawnedValidatorResult,
    WebFetchRecord,
)
from eubw_researcher.trust import (
    build_blind_validation_report,
    merge_spawned_validator_result,
    pinpoint_traceability_status,
)


def _minimal_result(record_type: str) -> SimpleNamespace:
    entry = SimpleNamespace(
        claim_id="synthetic-claim",
        final_claim_state=ClaimState.CONFIRMED,
        citations=[
            SimpleNamespace(
                source_id="synthetic-local-source",
                canonical_url=None,
                source_origin=SourceOrigin.LOCAL,
                source_role_level=SourceRoleLevel.HIGH,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
            )
        ],
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        governing_evidence=[],
        claim_text="Synthetic claim",
        source_role_level=SourceRoleLevel.HIGH,
        required_source_role_level=SourceRoleLevel.HIGH,
        support_directness=SimpleNamespace(value="direct"),
    )
    return SimpleNamespace(
        question="Synthetic question?",
        query_intent=SimpleNamespace(intent_type="synthetic_intent"),
        ledger_entries=[entry],
        approved_entries=[entry],
        rendered_answer="Confirmed:\nA reviewable answer.",
        gap_records=[],
        web_fetch_records=[
            WebFetchRecord(
                sub_question="test",
                canonical_url="https://example.test/source",
                domain="example.test",
                allowed=True,
                source_kind=SourceKind.TECHNICAL_STANDARD,
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
        retrieval_plan=SimpleNamespace(steps=[]),
        ingestion_report=[
            SimpleNamespace(
                anchor_quality=AnchorQuality.STRONG,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
                source_id="synthetic",
                source_origin=SourceOrigin.WEB,
            )
        ],
        facet_coverage_report=None,
        pinpoint_evidence_report=PinpointEvidenceReport(
            question="Synthetic question?",
            intent_type="synthetic_intent",
            records=[
                PinpointEvidenceRecord(
                    answer_claim_id="synthetic-claim",
                    answer_section="Confirmed",
                    answer_claim_text="Synthetic claim",
                    source_id="synthetic-local-source",
                    source_role_level=SourceRoleLevel.HIGH,
                    citation_quality=CitationQuality.ANCHOR_GROUNDED,
                    locator_type="heading_path",
                    locator_value="Article 1",
                    locator_precision="provision_level",
                    document_path=None,
                    canonical_url=None,
                    limitation_note="Exact line-level pinpoint is not available; this run exposes the nearest heading anchor.",
                )
            ],
        ),
        answer_alignment_report=AnswerAlignmentReport(
            question="Synthetic question?",
            intent_type="synthetic_intent",
            records=[
                AnswerAlignmentRecord(
                    answer_claim_id="synthetic-claim",
                    answer_section="Confirmed",
                    wording_category="governing_confirmed",
                    claim_ids=["synthetic-claim"],
                    claim_states=[ClaimState.CONFIRMED],
                    cited_source_ids=["synthetic-local-source"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                )
            ],
        ),
        blind_validation_report=BlindValidationReport(
            question="Synthetic question?",
            intent_type="synthetic_intent",
            validation_mode="structural_product_output_contract_check",
            artifacts_used=[
                "final_answer.txt",
                "approved_ledger.json",
                "pinpoint_evidence.json",
                "answer_alignment.json",
            ],
            raw_document_dependency="none",
            product_output_self_sufficient=True,
            passed=True,
            summary="Synthetic blind validation pass.",
        ),
    )


class EvaluationRunnerTests(unittest.TestCase):
    def test_pinpoint_traceability_rejects_approximate_only_locators(self) -> None:
        result = _minimal_result("fetch")
        result.pinpoint_evidence_report.records[0].locator_precision = "approximate"

        pinpoint_ok, message = pinpoint_traceability_status(result)

        self.assertFalse(pinpoint_ok)
        self.assertIn("only approximate document-level locators", message)

    def test_pinpoint_traceability_rejects_any_claim_without_precise_locator(self) -> None:
        result = _minimal_result("fetch")
        result.pinpoint_evidence_report.records.append(
            PinpointEvidenceRecord(
                answer_claim_id="approximate-only-claim",
                answer_section="Open",
                answer_claim_text="Synthetic approximate-only claim",
                source_id="synthetic-local-source-2",
                source_role_level=SourceRoleLevel.HIGH,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
                locator_type="document_title",
                locator_value="Synthetic approximate-only source",
                locator_precision="approximate",
                document_path=None,
                canonical_url=None,
                limitation_note="Only document-title traceability is available for this citation.",
            )
        )

        pinpoint_ok, message = pinpoint_traceability_status(result)

        self.assertFalse(pinpoint_ok)
        self.assertIn("approximate-only-claim", message)

    def test_pinpoint_traceability_allows_audit_confirmable_document_only_claim(self) -> None:
        result = _minimal_result("fetch")
        result.ledger_entries[0].citation_quality = CitationQuality.DOCUMENT_ONLY
        result.ledger_entries[0].governing_evidence = [
            SimpleNamespace(
                anchor_audit_note=(
                    "Expected anchors were not recoverable; treat this as a technical extraction failure "
                    "because the governing source remains directly readable."
                )
            )
        ]
        result.pinpoint_evidence_report.records[0].citation_quality = CitationQuality.DOCUMENT_ONLY
        result.pinpoint_evidence_report.records[0].locator_precision = "approximate"

        pinpoint_ok, message = pinpoint_traceability_status(result)
        blind_validation = build_blind_validation_report(result)

        self.assertTrue(pinpoint_ok)
        self.assertIn("reviewer-usable locators", message)
        self.assertTrue(blind_validation.passed)

    def test_pinpoint_traceability_allows_audit_confirmable_composite_answer_claim(self) -> None:
        result = _minimal_result("fetch")
        result.ledger_entries[0].citation_quality = CitationQuality.DOCUMENT_ONLY
        result.ledger_entries[0].governing_evidence = [
            SimpleNamespace(
                anchor_audit_note=(
                    "Expected anchors were not recoverable; treat this as a technical extraction failure "
                    "because the governing source remains directly readable."
                )
            )
        ]
        result.pinpoint_evidence_report.records = [
            PinpointEvidenceRecord(
                answer_claim_id="synthetic-summary",
                answer_section="Interpretive",
                answer_claim_text="Synthetic summary claim",
                source_id="synthetic-local-source",
                source_role_level=SourceRoleLevel.HIGH,
                citation_quality=CitationQuality.DOCUMENT_ONLY,
                locator_type="document_title",
                locator_value="Synthetic governing source",
                locator_precision="approximate",
                document_path=None,
                canonical_url=None,
                limitation_note="Only document-title traceability is available for this citation.",
            )
        ]
        result.answer_alignment_report = AnswerAlignmentReport(
            question="Synthetic question?",
            intent_type="synthetic_intent",
            records=[
                AnswerAlignmentRecord(
                    answer_claim_id="synthetic-summary",
                    answer_section="Interpretive",
                    wording_category="interpretive_state_forwarded",
                    claim_ids=["synthetic-claim"],
                    claim_states=[ClaimState.CONFIRMED],
                    cited_source_ids=["synthetic-local-source"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                )
            ],
        )

        pinpoint_ok, message = pinpoint_traceability_status(result)

        self.assertTrue(pinpoint_ok)
        self.assertIn("reviewer-usable locators", message)

    def test_blind_validation_uses_structural_topology_sections_not_rendered_text_markers(self) -> None:
        result = _minimal_result("fetch")
        result.query_intent = SimpleNamespace(intent_type="certificate_topology_analysis")
        result.rendered_answer = "Topology answer rendered with different formatting."
        result.facet_coverage_report = FacetCoverageReport(
            question=result.question,
            intent_type="certificate_topology_analysis",
            facets=[FacetCoverageFacet(facet_id, True, []) for facet_id in [
                "multiplicity_single_certificate",
                "derived_certificate_term_status",
                "registration_certificate_role",
                "access_certificate_role",
                "unresolved_or_interpretive_status",
            ]],
        )
        result.answer_alignment_report = AnswerAlignmentReport(
            question=result.question,
            intent_type="certificate_topology_analysis",
            records=[
                AnswerAlignmentRecord(
                    answer_claim_id="term-status",
                    answer_section="Not explicitly defined",
                    wording_category="term_status_scan",
                    claim_ids=[],
                    claim_states=[],
                    cited_source_ids=["synthetic-local-source"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                ),
                AnswerAlignmentRecord(
                    answer_claim_id="interpretive",
                    answer_section="Interpretive",
                    wording_category="interpretive_governing_boundary",
                    claim_ids=["synthetic-claim"],
                    claim_states=[ClaimState.INTERPRETIVE],
                    cited_source_ids=["synthetic-local-source"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                ),
                AnswerAlignmentRecord(
                    answer_claim_id="open",
                    answer_section="Open",
                    wording_category="open_state_forwarded",
                    claim_ids=["synthetic-open"],
                    claim_states=[ClaimState.OPEN],
                    cited_source_ids=["synthetic-local-source"],
                    cited_source_roles=[SourceRoleLevel.HIGH],
                ),
            ],
        )

        report = build_blind_validation_report(result)

        self.assertTrue(report.passed)
        self.assertEqual(report.missing_facets, [])

    def test_merge_spawned_validator_result_accepts_minor_confirmation_without_context_inheritance(self) -> None:
        structural_report = build_blind_validation_report(_minimal_result("fetch"))
        spawned_validator = SpawnedValidatorResult(
            passed=True,
            context_inherited=False,
            artifacts_used=["manual_review_report.md"],
            raw_document_dependency="minor_confirmation",
            product_output_self_sufficient=True,
            summary="Validator reused the bundle and only spot-checked cited sources.",
            validator_answer="Synthetic validator answer.",
        )

        merged = merge_spawned_validator_result(structural_report, spawned_validator)

        self.assertTrue(merged.structural_passed)
        self.assertTrue(merged.passed)
        self.assertEqual(merged.validation_mode, "structural_plus_spawned_validator_closeout")
        self.assertEqual(merged.raw_document_dependency, "minor_confirmation")
        self.assertIsNotNone(merged.spawned_validator)

    def test_merge_spawned_validator_result_rejects_inherited_context(self) -> None:
        structural_report = build_blind_validation_report(_minimal_result("fetch"))
        spawned_validator = SpawnedValidatorResult(
            passed=True,
            context_inherited=True,
            artifacts_used=["manual_review_report.md"],
            raw_document_dependency="none",
            product_output_self_sufficient=True,
            summary="Validator reported a pass.",
            validator_answer="Synthetic validator answer.",
        )

        merged = merge_spawned_validator_result(structural_report, spawned_validator)

        self.assertFalse(merged.passed)
        self.assertIn("inherited context", merged.summary)

    def test_merge_spawned_validator_result_preserves_structural_failure_dependency(self) -> None:
        structural_report = build_blind_validation_report(_minimal_result("fetch"))
        structural_report.structural_passed = False
        structural_report.product_output_self_sufficient = False
        structural_report.passed = False
        structural_report.raw_document_dependency = "central_reconstruction"
        spawned_validator = SpawnedValidatorResult(
            passed=True,
            context_inherited=False,
            artifacts_used=["manual_review_report.md"],
            raw_document_dependency="none",
            product_output_self_sufficient=True,
            summary="Validator reused the bundle without raw document reads.",
            validator_answer="Synthetic validator answer.",
        )

        merged = merge_spawned_validator_result(structural_report, spawned_validator)

        self.assertFalse(merged.passed)
        self.assertEqual(merged.raw_document_dependency, "central_reconstruction")
        self.assertIn("structural blind-validation precondition did not pass", merged.summary)

    def test_required_web_fetch_count_counts_fetch_records_only(self) -> None:
        scenario = EvaluationScenario(
            scenario_id="synthetic_fetch_gate",
            question="Synthetic question?",
            expectation="Require an actual fetched document.",
            required_web_fetch_count=1,
        )

        verdict = _evaluate_scenario(scenario, _minimal_result("discovery"))

        self.assertFalse(verdict.passed)
        self.assertIn("web_fetch_records>=1:fail", verdict.checks)

    def test_required_web_discovery_count_accepts_discovery_records(self) -> None:
        scenario = EvaluationScenario(
            scenario_id="synthetic_discovery_gate",
            question="Synthetic question?",
            expectation="Require at least one discovery step.",
            required_web_discovery_count=1,
        )

        verdict = _evaluate_scenario(scenario, _minimal_result("discovery"))

        self.assertTrue(verdict.passed)
        self.assertIn("web_discovery_records>=1:ok", verdict.checks)

    def test_required_intent_type_fails_when_analyzer_contract_drifts(self) -> None:
        scenario = EvaluationScenario(
            scenario_id="synthetic_intent_gate",
            question="Synthetic question?",
            expectation="Require a stable analyzed intent.",
            required_intent_type="wallet_requirements_summary",
        )

        verdict = _evaluate_scenario(scenario, _minimal_result("fetch"))

        self.assertFalse(verdict.passed)
        self.assertIn(
            "intent_type:wallet_requirements_summary:fail:synthetic_intent",
            verdict.checks,
        )

    def test_blind_validation_fails_when_generic_alignment_contract_breaks(self) -> None:
        result = _minimal_result("fetch")
        result.answer_alignment_report.blocking_violations = [
            "synthetic-claim: Confirmed wording is attached to a non-confirmed claim-state."
        ]

        report = build_blind_validation_report(result)

        self.assertFalse(report.passed)
        self.assertIn("answer_evidence_alignment", report.missing_facets)

    def test_manual_review_artifact_flags_missing_open_state_marker(self) -> None:
        result = _minimal_result("fetch")
        result.approved_entries[0].final_claim_state = ClaimState.OPEN
        result.rendered_answer = "Source-bound answer:\n- Synthetic claim without state marker."
        result.provisional_grouping = []
        result.query_intent = SimpleNamespace(
            intent_type="synthetic_intent",
            claim_targets=[],
        )

        artifact = build_manual_review_artifact(result)
        checks_by_id = {check.check_id: check for check in artifact.checks}

        self.assertEqual(checks_by_id["claim_state_visibility"].status, "fail")

    def test_manual_review_artifact_flags_missing_grouping_for_grouping_capable_intent(self) -> None:
        result = _minimal_result("fetch")
        result.provisional_grouping = []
        result.query_intent = SimpleNamespace(
            intent_type="wallet_requirements_summary",
            claim_targets=[SimpleNamespace(grouping_label="Certificates and identity")],
        )

        artifact = build_manual_review_artifact(result)
        checks_by_id = {check.check_id: check for check in artifact.checks}

        self.assertEqual(
            checks_by_id["provisional_grouping_present_when_applicable"].status,
            "fail",
        )

    def test_manual_review_accept_gate_requires_accept_judgment(self) -> None:
        result = _minimal_result("fetch")
        result.approved_entries = []
        result.rendered_answer = "Open:\nNeeds review."
        scenario = EvaluationScenario(
            scenario_id="synthetic_manual_review_gate",
            question="Synthetic question?",
            expectation="Require a passing manual review judgment.",
            required_intent_type="synthetic_intent",
            require_manual_review_accept=True,
        )

        verdict = _evaluate_scenario(scenario, result)

        self.assertFalse(verdict.passed)
        self.assertIn("manual_review_accept:fail", verdict.checks)

    def test_review_report_surfaces_digest_and_provenance_for_approved_web_sources(self) -> None:
        result = _minimal_result("fetch")
        result.ledger_entries[0].citations = [
            SimpleNamespace(
                source_id="synthetic-web-source",
                canonical_url="https://example.test/source",
                source_origin=SourceOrigin.WEB,
                source_role_level=SourceRoleLevel.HIGH,
                citation_quality=CitationQuality.ANCHOR_GROUNDED,
            )
        ]
        result.approved_entries = result.ledger_entries
        scenario = EvaluationScenario(
            scenario_id="synthetic_fetch_visibility_gate",
            question="Synthetic question?",
            expectation="Approved fetched evidence must stay reviewer-visible.",
            required_intent_type="synthetic_intent",
        )

        verdict = _evaluate_scenario(scenario, result)

        self.assertTrue(verdict.passed)
        self.assertIn("review_fetch_evidence_visible:ok", verdict.checks)

        report = build_manual_review_report(
            result,
            ScenarioVerdict(
                scenario_id="synthetic_fetch_visibility_gate",
                passed=True,
                checks=[],
            ),
            scenario_id="synthetic_fetch_visibility_gate",
            catalog_path="/tmp/synthetic_catalog.json",
            corpus_state_id="synthetic-state",
        )
        markdown = build_manual_review_report_markdown(report)
        self.assertIn("Approved Fetched-Source Evidence", markdown)
        self.assertIn("digest=`abc123`", markdown)
        self.assertIn("provenance=`configured_seed_url`", markdown)
        self.assertIn("Pinpoint traceability verdict", markdown)
        self.assertIn("Reusable without raw-document reconstruction", markdown)

    def test_certificate_topology_eval_requires_facet_coverage(self) -> None:
        result = _minimal_result("fetch")
        result.query_intent = SimpleNamespace(intent_type="certificate_topology_analysis")
        result.facet_coverage_report = FacetCoverageReport(
            question=result.question,
            intent_type="certificate_topology_analysis",
            facets=[
                FacetCoverageFacet(
                    facet_id="multiplicity_single_certificate",
                    addressed=False,
                    evidence=[],
                ),
                FacetCoverageFacet(
                    facet_id="derived_certificate_term_status",
                    addressed=True,
                    evidence=["answer:not-explicitly-defined-section"],
                ),
                FacetCoverageFacet(
                    facet_id="registration_certificate_role",
                    addressed=True,
                    evidence=["claim_id:topology_registration_certificate_role"],
                ),
                FacetCoverageFacet(
                    facet_id="access_certificate_role",
                    addressed=True,
                    evidence=["claim_id:topology_access_certificate_role"],
                ),
                FacetCoverageFacet(
                    facet_id="unresolved_or_interpretive_status",
                    addressed=True,
                    evidence=["answer:open-section"],
                ),
            ],
        )
        scenario = EvaluationScenario(
            scenario_id="synthetic_topology_gate",
            question=result.question,
            expectation="Require topology facet coverage.",
            required_intent_type="certificate_topology_analysis",
        )

        verdict = _evaluate_scenario(scenario, result)

        self.assertFalse(verdict.passed)
        self.assertIn("facet_coverage_artifact:ok", verdict.checks)
        self.assertIn("facet:multiplicity_single_certificate:fail", verdict.checks)
        self.assertIn("pinpoint_evidence_artifact:ok", verdict.checks)
        self.assertIn("answer_alignment:ok", verdict.checks)
        self.assertIn("blind_validation:ok", verdict.checks)

    def test_manual_review_report_rejects_incomplete_topology_facet_coverage(self) -> None:
        result = _minimal_result("fetch")
        result.query_intent = SimpleNamespace(intent_type="certificate_topology_analysis")
        result.facet_coverage_report = FacetCoverageReport(
            question=result.question,
            intent_type="certificate_topology_analysis",
            facets=[
                FacetCoverageFacet("multiplicity_single_certificate", False, []),
                FacetCoverageFacet("derived_certificate_term_status", True, []),
                FacetCoverageFacet("registration_certificate_role", True, []),
                FacetCoverageFacet("access_certificate_role", True, []),
                FacetCoverageFacet("unresolved_or_interpretive_status", True, []),
            ],
        )

        report = build_manual_review_report(
            result,
            ScenarioVerdict(
                scenario_id="synthetic_topology_review",
                passed=True,
                checks=[],
            ),
            scenario_id="synthetic_topology_review",
            catalog_path="/tmp/synthetic_catalog.json",
            corpus_state_id="synthetic-state",
        )

        self.assertEqual(report.usefulness_verdict, "needs_follow_up")
        self.assertEqual(report.final_judgment, "reject")

    def test_topology_review_report_rejects_missing_v2_2_trust_artifacts(self) -> None:
        result = _minimal_result("fetch")
        result.query_intent = SimpleNamespace(intent_type="certificate_topology_analysis")
        result.facet_coverage_report = FacetCoverageReport(
            question=result.question,
            intent_type="certificate_topology_analysis",
            facets=[FacetCoverageFacet(facet_id, True, []) for facet_id in [
                "multiplicity_single_certificate",
                "derived_certificate_term_status",
                "registration_certificate_role",
                "access_certificate_role",
                "unresolved_or_interpretive_status",
            ]],
        )
        result.pinpoint_evidence_report = None

        report = build_manual_review_report(
            result,
            ScenarioVerdict(
                scenario_id="synthetic_topology_review",
                passed=True,
                checks=[],
            ),
            scenario_id="synthetic_topology_review",
            catalog_path="/tmp/synthetic_catalog.json",
            corpus_state_id="synthetic-state",
        )

        self.assertEqual(report.pinpoint_traceability_verdict, "needs_follow_up")
        self.assertEqual(report.final_judgment, "reject")


class WriteArtifactBundleCoverageTests(unittest.TestCase):
    def _make_coverage_report(self) -> CorpusCoverageReport:
        return CorpusCoverageReport(
            catalog_path="/fake/curated_catalog.json",
            corpus_state_id="teststate01",
            generation_timestamp="2026-01-01T00:00:00+00:00",
            admitted_source_counts_by_kind={"regulation": 1},
            families=[
                CorpusCoverageFamily(
                    family_id="governing_eu_regulation",
                    minimum_count=1,
                    admitted_count=1,
                    admitted_source_ids=["reg_a"],
                    missing=False,
                )
            ],
            passed=True,
        )

    def _make_result(self):
        result = _minimal_result("fetch")
        result.corpus_coverage_report = self._make_coverage_report()
        result.provisional_grouping = []
        result.facet_coverage_report = None
        result.query_intent = SimpleNamespace(intent_type="synthetic_intent", claim_targets=[])
        # write_artifact_bundle serializes retrieval_plan via dataclass_to_dict;
        # replace the SimpleNamespace with a proper serializable dataclass
        result.retrieval_plan = RetrievalPlan(question="Synthetic question?", steps=[])
        result.ledger_entries = []
        result.approved_entries = []
        result.ingestion_report = []
        result.gap_records = []
        return result

    def test_write_artifact_bundle_writes_coverage_summary_md(self):
        result = self._make_result()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_artifact_bundle(output_dir, result, corpus_state_id="teststate01")
            summary_path = output_dir / "corpus_coverage_summary.md"
            self.assertTrue(summary_path.exists(), "corpus_coverage_summary.md not written")
            content = summary_path.read_text(encoding="utf-8")
            self.assertIn("teststate01", content)
            self.assertIn("PASS", content)
            self.assertIn("governing_eu_regulation", content)

    def test_write_artifact_bundle_skips_coverage_summary_when_report_absent(self):
        result = self._make_result()
        result.corpus_coverage_report = None
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_artifact_bundle(output_dir, result)
            self.assertFalse((output_dir / "corpus_coverage_summary.md").exists())


if __name__ == "__main__":
    unittest.main()
