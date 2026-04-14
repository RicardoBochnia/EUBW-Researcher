from __future__ import annotations

from types import SimpleNamespace
import unittest

from eubw_researcher.answering import build_relation_hint_report, compose_answer_bundle
from eubw_researcher.models import (
    AnswerAlignmentRecord,
    AnswerAlignmentReport,
    Citation,
    CitationQuality,
    ClaimState,
    ClaimTarget,
    ClaimType,
    ContradictionStatus,
    DocumentStatus,
    LedgerEvidence,
    LedgerEntry,
    PinpointEvidenceRecord,
    PinpointEvidenceReport,
    QueryIntent,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    SupportDirectness,
)
from eubw_researcher.trust import build_blind_validation_report


def _intent(intent_type: str) -> QueryIntent:
    return QueryIntent(
        question="Synthetic question?",
        intent_type=intent_type,
        eu_first=True,
        claim_targets=[
            ClaimTarget(
                target_id="synthetic",
                claim_text="Synthetic.",
                claim_type=ClaimType.SYNTHESIS,
                required_source_role_level=SourceRoleLevel.HIGH,
                preferred_kinds=[SourceKind.REGULATION],
                scope_terms=["synthetic"],
                primary_terms=["synthetic"],
                support_groups=[["synthetic"]],
                contradiction_groups=[],
            )
        ],
        preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
    )


def _citation(
    source_id: str,
    *,
    role_level: SourceRoleLevel,
    source_kind: SourceKind,
    anchor_label: str,
) -> Citation:
    return Citation(
        source_id=source_id,
        document_title=f"{source_id} title",
        source_role_level=role_level,
        source_kind=source_kind,
        jurisdiction="EU",
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        document_path=None,
        canonical_url=None,
        document_status=DocumentStatus.FINAL,
        source_origin=SourceOrigin.LOCAL,
        anchor_label=anchor_label,
    )


def _entry(
    claim_id: str,
    state: ClaimState,
    *,
    source_role_level: SourceRoleLevel,
    source_kind: SourceKind,
    required_source_role_level: SourceRoleLevel,
) -> LedgerEntry:
    citation = _citation(
        f"{claim_id}_source",
        role_level=source_role_level,
        source_kind=source_kind,
        anchor_label="Article 2" if source_role_level == SourceRoleLevel.HIGH else "Section 3.2",
    )
    evidence = LedgerEvidence(
        citation=citation,
        source_role_level=source_role_level,
        source_kind=source_kind,
        source_kind_rank=1 if source_role_level == SourceRoleLevel.HIGH else 3,
        source_origin=SourceOrigin.LOCAL,
        jurisdiction="EU",
        support_directness=SupportDirectness.DIRECT,
        term_overlap=1,
        scope_overlap=1,
        on_point_score=5,
        admissible=True,
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        anchor_audit_note=None,
    )
    governing_evidence = [evidence] if source_role_level == SourceRoleLevel.HIGH else []
    supporting_evidence = [] if source_role_level == SourceRoleLevel.HIGH else [evidence]
    return LedgerEntry(
        claim_id=claim_id,
        claim_text=f"{claim_id} text",
        claim_type=(
            ClaimType.OBLIGATION
            if source_role_level == SourceRoleLevel.HIGH
            else ClaimType.SYNTHESIS
        ),
        required_source_role_level=required_source_role_level,
        source_role_level=source_role_level,
        jurisdiction="EU",
        support_directness=SupportDirectness.DIRECT,
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        contradiction_status=ContradictionStatus.NONE,
        final_claim_state=state,
        citations=[citation],
        supporting_evidence=supporting_evidence,
        contradicting_evidence=[],
        governing_evidence=governing_evidence,
        rationale="Synthetic rationale.",
    )


class RelationHintTests(unittest.TestCase):
    def test_unsupported_intent_returns_no_relation_hint_report(self) -> None:
        report = build_relation_hint_report(
            "Synthetic question?",
            [],
            _intent("protocol_authorization_server_comparison"),
        )

        self.assertIsNone(report)

    def test_supported_intent_without_required_claims_returns_empty_report(self) -> None:
        report = build_relation_hint_report(
            "Synthetic question?",
            [
                _entry(
                    "wallet_access_certificate_requirement",
                    ClaimState.CONFIRMED,
                    source_role_level=SourceRoleLevel.HIGH,
                    source_kind=SourceKind.IMPLEMENTING_ACT,
                    required_source_role_level=SourceRoleLevel.HIGH,
                )
            ],
            _intent("wallet_requirements_summary"),
        )

        self.assertIsNotNone(report)
        assert report is not None
        self.assertEqual(report.families_considered, ["registration_requirement_layering"])
        self.assertEqual(report.records, [])

    def test_required_any_branch_selection_skips_open_alternative(self) -> None:
        entries = [
            _entry(
                "member_state_discretion",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.REGULATION,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "annex_registration_fields",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "wallet_access_certificate_requirement",
                ClaimState.OPEN,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
        ]

        report = build_relation_hint_report(
            "Synthetic question?",
            entries,
            _intent("wallet_requirements_summary"),
        )

        assert report is not None
        relation_record = next(
            record
            for record in report.records
            if record.hint_id == "layering_union_requirement_to_member_state_discretion"
        )
        self.assertEqual(relation_record.relation_state, "confirmed")
        self.assertEqual(
            relation_record.derived_from_claim_ids,
            ["member_state_discretion", "annex_registration_fields"],
        )
        self.assertTrue(relation_record.rendered_in_answer)

    def test_wallet_relation_hints_render_through_composer_and_alignment(self) -> None:
        entries = [
            _entry(
                "wallet_access_certificate_requirement",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "annex_registration_fields",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "member_state_discretion",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.REGULATION,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "wallet_national_guidance_boundary",
                ClaimState.INTERPRETIVE,
                source_role_level=SourceRoleLevel.MEDIUM,
                source_kind=SourceKind.NATIONAL_IMPLEMENTATION,
                required_source_role_level=SourceRoleLevel.MEDIUM,
            ),
        ]
        report = build_relation_hint_report(
            "Synthetic question?",
            entries,
            _intent("wallet_requirements_summary"),
        )
        bundle = compose_answer_bundle(
            "Synthetic question?",
            entries,
            query_intent=_intent("wallet_requirements_summary"),
            relation_hint_report=report,
        )

        self.assertIn("Cross-reference hints:", bundle.rendered_answer)
        self.assertIn(
            "relation_hint:layering_union_requirement_to_national_guidance_boundary",
            {
                record.answer_claim_id
                for record in bundle.answer_alignment_report.records
            },
        )
        relation_record = next(
            record
            for record in bundle.answer_alignment_report.records
            if record.answer_claim_id
            == "relation_hint:layering_union_requirement_to_national_guidance_boundary"
        )
        self.assertEqual(
            relation_record.wording_category,
            "relation_hint_partitioned_interpretive",
        )
        self.assertIn(
            "relation_hint:layering_union_requirement_to_national_guidance_boundary",
            {
                record.answer_claim_id
                for record in bundle.pinpoint_evidence_report.records
            },
        )

    def test_topology_relation_hints_remain_artifact_only(self) -> None:
        entries = [
            _entry(
                "topology_registration_certificate_role",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "topology_access_certificate_role",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "topology_registration_access_linkage",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "topology_project_artifact_multiplicity",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.MEDIUM,
                source_kind=SourceKind.PROJECT_ARTIFACT,
                required_source_role_level=SourceRoleLevel.MEDIUM,
            ),
            _entry(
                "topology_project_intended_use_scoping",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.MEDIUM,
                source_kind=SourceKind.PROJECT_ARTIFACT,
                required_source_role_level=SourceRoleLevel.MEDIUM,
            ),
        ]
        report = build_relation_hint_report(
            "Synthetic topology question?",
            entries,
            _intent("certificate_topology_analysis"),
        )
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            entries,
            query_intent=_intent("certificate_topology_analysis"),
            relation_hint_report=report,
        )

        assert report is not None
        self.assertEqual(
            {record.hint_id for record in report.records},
            {
                "topology_registration_access_dependency",
                "topology_governing_scope_boundary",
                "topology_non_governing_multiplicity_expansion",
            },
        )
        self.assertTrue(all(not record.rendered_in_answer for record in report.records))
        self.assertNotIn("Cross-reference hints:", bundle.rendered_answer)

    def test_blind_validation_fails_when_rendered_relation_hint_is_not_mirrored(self) -> None:
        entries = [
            _entry(
                "wallet_access_certificate_requirement",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "annex_registration_fields",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
        ]
        intent = _intent("wallet_requirements_summary")
        report = build_relation_hint_report("Synthetic question?", entries, intent)
        assert report is not None
        rendered_record = next(record for record in report.records if record.rendered_in_answer)
        result = SimpleNamespace(
            question="Synthetic question?",
            query_intent=intent,
            rendered_answer="Confirmed:\nSynthetic answer.",
            ledger_entries=entries,
            approved_entries=entries,
            relation_hint_report=report,
            facet_coverage_report=None,
            pinpoint_evidence_report=PinpointEvidenceReport(
                question="Synthetic question?",
                intent_type=intent.intent_type,
                records=[],
                all_cited_evidence_mapped=True,
            ),
            answer_alignment_report=AnswerAlignmentReport(
                question="Synthetic question?",
                intent_type=intent.intent_type,
                records=[],
            ),
        )

        report_output = build_blind_validation_report(result)

        self.assertFalse(report_output.passed)
        self.assertIn("relation_hints.json", report_output.artifacts_used)
        self.assertIn(
            f"rendered_relation_hint_contract:{rendered_record.hint_id}",
            report_output.missing_facets,
        )

    def test_blind_validation_fails_on_relation_hint_citation_drift(self) -> None:
        entries = [
            _entry(
                "wallet_access_certificate_requirement",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
            _entry(
                "annex_registration_fields",
                ClaimState.CONFIRMED,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                required_source_role_level=SourceRoleLevel.HIGH,
            ),
        ]
        intent = _intent("wallet_requirements_summary")
        report = build_relation_hint_report("Synthetic question?", entries, intent)
        bundle = compose_answer_bundle(
            "Synthetic question?",
            entries,
            query_intent=intent,
            relation_hint_report=report,
        )
        assert report is not None
        drifted_citation = _citation(
            "wallet_access_certificate_requirement_source",
            role_level=SourceRoleLevel.HIGH,
            source_kind=SourceKind.IMPLEMENTING_ACT,
            anchor_label="Article 99",
        )
        report.records[0].evidence_partitions[0].citations = [drifted_citation]
        report.records[0].supporting_source_ids = [drifted_citation.source_id]
        result = SimpleNamespace(
            question="Synthetic question?",
            query_intent=intent,
            rendered_answer=bundle.rendered_answer,
            ledger_entries=entries,
            approved_entries=entries,
            relation_hint_report=report,
            facet_coverage_report=None,
            pinpoint_evidence_report=bundle.pinpoint_evidence_report,
            answer_alignment_report=bundle.answer_alignment_report,
        )

        report_output = build_blind_validation_report(result)

        self.assertFalse(report_output.passed)
        self.assertIn("relation_hint_integrity", report_output.missing_facets)


if __name__ == "__main__":
    unittest.main()
