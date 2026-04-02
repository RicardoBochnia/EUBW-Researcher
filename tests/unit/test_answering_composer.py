from __future__ import annotations

import unittest

from eubw_researcher.answering import build_facet_coverage_report, compose_answer_bundle
from eubw_researcher.models import (
    AnswerAlignmentRecord,
    Citation,
    CitationQuality,
    ClaimTarget,
    ClaimState,
    ClaimType,
    ContradictionStatus,
    LedgerEvidence,
    LedgerEntry,
    QueryIntent,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    SupportDirectness,
)


def _topology_intent() -> QueryIntent:
    return QueryIntent(
        question="Synthetic topology question?",
        intent_type="certificate_topology_analysis",
        eu_first=True,
        claim_targets=[],
        preferred_kinds=[
            SourceKind.REGULATION,
            SourceKind.IMPLEMENTING_ACT,
            SourceKind.PROJECT_ARTIFACT,
        ],
        answer_pattern="certificate_topology",
        undefined_terms=[
            "derived certificate",
            "derived access certificate",
            "derived registration certificate",
        ],
    )


def _topology_intent_with_answer_pattern(answer_pattern: str) -> QueryIntent:
    intent = _topology_intent()
    intent.answer_pattern = answer_pattern
    return intent


def _generic_intent(
    intent_type: str = "wallet_requirements_summary",
    *,
    grouping_label: str | None = None,
) -> QueryIntent:
    claim_targets = (
        [
            ClaimTarget(
                target_id="synthetic_grouping_target",
                claim_text="Synthetic grouped claim.",
                claim_type=ClaimType.SYNTHESIS,
                required_source_role_level=SourceRoleLevel.HIGH,
                preferred_kinds=[SourceKind.REGULATION],
                scope_terms=["synthetic"],
                primary_terms=["grouped"],
                support_groups=[["synthetic", "grouped"]],
                contradiction_groups=[],
                grouping_label=grouping_label,
            )
        ]
        if grouping_label is not None
        else []
    )
    return QueryIntent(
        question="Synthetic generic question?",
        intent_type=intent_type,
        eu_first=True,
        claim_targets=claim_targets,
        preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
    )


def _high_role_citation(source_id: str) -> Citation:
    return Citation(
        source_id=source_id,
        document_title="Synthetic governing source",
        source_role_level=SourceRoleLevel.HIGH,
        source_kind=SourceKind.IMPLEMENTING_ACT,
        jurisdiction="EU",
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        document_path=None,
        canonical_url=None,
        source_origin=SourceOrigin.LOCAL,
        anchor_label="Article 2",
    )


def _entry(claim_id: str, claim_text: str, state: ClaimState) -> LedgerEntry:
    citation = _high_role_citation(f"{claim_id}_source")
    evidence = LedgerEvidence(
        citation=citation,
        source_role_level=SourceRoleLevel.HIGH,
        source_kind=SourceKind.IMPLEMENTING_ACT,
        source_kind_rank=1,
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
    return LedgerEntry(
        claim_id=claim_id,
        claim_text=claim_text,
        claim_type=ClaimType.OBLIGATION,
        required_source_role_level=SourceRoleLevel.HIGH,
        source_role_level=SourceRoleLevel.HIGH,
        jurisdiction="EU",
        support_directness=SupportDirectness.DIRECT,
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        contradiction_status=ContradictionStatus.NONE,
        final_claim_state=state,
        citations=[citation],
        supporting_evidence=[evidence],
        contradicting_evidence=[],
        governing_evidence=[evidence],
        rationale="Synthetic rationale.",
    )


def _project_entry(claim_id: str, claim_text: str, state: ClaimState) -> LedgerEntry:
    citation = Citation(
        source_id=f"{claim_id}_source",
        document_title="Synthetic project source",
        source_role_level=SourceRoleLevel.MEDIUM,
        source_kind=SourceKind.PROJECT_ARTIFACT,
        jurisdiction="EU",
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        document_path=None,
        canonical_url=None,
        source_origin=SourceOrigin.LOCAL,
        anchor_label="Section 3.2",
    )
    evidence = LedgerEvidence(
        citation=citation,
        source_role_level=SourceRoleLevel.MEDIUM,
        source_kind=SourceKind.PROJECT_ARTIFACT,
        source_kind_rank=3,
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
    return LedgerEntry(
        claim_id=claim_id,
        claim_text=claim_text,
        claim_type=ClaimType.SYNTHESIS,
        required_source_role_level=SourceRoleLevel.MEDIUM,
        source_role_level=SourceRoleLevel.MEDIUM,
        jurisdiction="EU",
        support_directness=SupportDirectness.DIRECT,
        citation_quality=CitationQuality.ANCHOR_GROUNDED,
        contradiction_status=ContradictionStatus.NONE,
        final_claim_state=state,
        citations=[citation],
        supporting_evidence=[evidence],
        contradicting_evidence=[],
        governing_evidence=[],
        rationale="Synthetic project rationale.",
    )


class ComposerTests(unittest.TestCase):
    def test_topology_empty_approved_entries_still_emit_all_false_facet_coverage(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [],
            query_intent=_topology_intent(),
        )

        self.assertIsNotNone(bundle.facet_coverage_report)
        self.assertFalse(bundle.facet_coverage_report.all_addressed())
        self.assertTrue(
            all(not facet.addressed for facet in bundle.facet_coverage_report.facets)
        )

    def test_build_facet_coverage_report_accepts_old_and_new_call_shapes(self) -> None:
        entries = [
            _entry(
                "topology_access_certificate_role",
                "Governing EU sources define a wallet-relying party access certificate as authenticating and validating the wallet-relying party in wallet interactions.",
                ClaimState.CONFIRMED,
            )
        ]

        old_shape = build_facet_coverage_report(
            "Synthetic topology question?",
            _topology_intent(),
            "Previously rendered answer text.",
            entries,
        )
        new_shape = build_facet_coverage_report(
            "Synthetic topology question?",
            _topology_intent(),
            entries,
        )

        self.assertIsNotNone(old_shape)
        self.assertIsNotNone(new_shape)
        self.assertEqual(old_shape.by_id().keys(), new_shape.by_id().keys())
        self.assertEqual(
            old_shape.by_id()["access_certificate_role"].addressed,
            new_shape.by_id()["access_certificate_role"].addressed,
        )

    def test_build_facet_coverage_report_rejects_invalid_call_shape(self) -> None:
        with self.assertRaises(TypeError):
            build_facet_coverage_report(
                "Synthetic topology question?",
                _topology_intent(),
            )

    def test_topology_composer_keys_off_intent_type_even_when_answer_pattern_drifts(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_access_certificate_role",
                    "Governing EU sources define a wallet-relying party access certificate as authenticating and validating the wallet-relying party in wallet interactions.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_topology_intent_with_answer_pattern("generic_answer"),
        )

        self.assertIsNotNone(bundle.facet_coverage_report)
        self.assertIn("Not explicitly defined:", bundle.rendered_answer)

    def test_topology_unresolved_bullet_does_not_claim_project_support_when_absent(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_registration_certificate_role",
                    "Governing EU sources define a wallet-relying party registration certificate as describing the relying party's intended use and the attributes it has registered to request from users.",
                    ClaimState.INTERPRETIVE,
                )
            ],
            query_intent=_topology_intent(),
        )

        self.assertIn("Open:", bundle.rendered_answer)
        self.assertNotIn(
            "while medium-rank project artifacts make the multi-certificate interpretation more explicit.",
            bundle.rendered_answer,
        )
        self.assertNotIn(
            "Evidence (medium-rank project support):",
            bundle.rendered_answer,
        )
        self.assertIn(
            "preserves the governing boundary conditions",
            bundle.rendered_answer,
        )

    def test_confirmed_registration_scope_claim_still_surfaces_confirmed_section(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_registration_certificate_role",
                    "Governing EU sources define a wallet-relying party registration certificate as describing the relying party's intended use and the attributes it has registered to request from users.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_topology_intent(),
        )

        self.assertIn("Confirmed:", bundle.rendered_answer)
        self.assertIn(
            "Governing EU sources define a wallet-relying party registration certificate",
            bundle.rendered_answer,
        )

    def test_open_scope_claim_does_not_emit_governing_scope_summary(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_registration_certificate_role",
                    "Governing EU sources define a wallet-relying party registration certificate as describing the relying party's intended use and the attributes it has registered to request from users.",
                    ClaimState.OPEN,
                )
            ],
            query_intent=_topology_intent(),
        )

        self.assertNotIn(
            "The governing EU material supports intended-use / service scoping:",
            bundle.rendered_answer,
        )
        self.assertIn("Open:", bundle.rendered_answer)
        self.assertNotIn(
            "preserve the governing boundary statements",
            bundle.rendered_answer,
        )

    def test_open_project_entry_does_not_emit_project_support_line(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_registration_certificate_role",
                    "Governing EU sources define a wallet-relying party registration certificate as describing the relying party's intended use and the attributes it has registered to request from users.",
                    ClaimState.INTERPRETIVE,
                ),
                _project_entry(
                    "topology_project_artifact_multiplicity",
                    "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
                    ClaimState.OPEN,
                ),
            ],
            query_intent=_topology_intent(),
        )

        self.assertNotIn(
            "Evidence (medium-rank project support):",
            bundle.rendered_answer,
        )
        self.assertNotIn(
            "while medium-rank project artifacts make the multi-certificate interpretation more explicit.",
            bundle.rendered_answer,
        )

    def test_partial_boundary_support_does_not_emit_combined_scoping_summary(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_access_certificate_role",
                    "Governing EU sources define a wallet-relying party access certificate as authenticating and validating the wallet-relying party in wallet interactions.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_topology_intent(),
        )

        self.assertNotIn(
            "The governing EU material supports intended-use / service scoping:",
            bundle.rendered_answer,
        )

    def test_open_only_project_entries_do_not_claim_project_support(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _project_entry(
                    "topology_project_artifact_multiplicity",
                    "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
                    ClaimState.OPEN,
                ),
                _project_entry(
                    "topology_project_intended_use_scoping",
                    "Official project artifacts explicitly describe registration certificates as issued per intended use.",
                    ClaimState.OPEN,
                ),
            ],
            query_intent=_topology_intent(),
        )

        self.assertNotIn(
            "while medium-rank project artifacts make the multi-certificate interpretation more explicit.",
            bundle.rendered_answer,
        )
        self.assertNotIn(
            "Evidence (medium-rank project support):",
            bundle.rendered_answer,
        )
        self.assertNotIn(
            "preserves the governing boundary conditions",
            bundle.rendered_answer,
        )
        self.assertIn(
            "does not surface approved governing-boundary support or approved medium-rank project-artifact support",
            bundle.rendered_answer,
        )

    def test_topology_term_status_without_locator_is_marked_missing(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _project_entry(
                    "topology_project_artifact_multiplicity",
                    "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
                    ClaimState.INTERPRETIVE,
                )
            ],
            query_intent=_topology_intent(),
        )

        self.assertFalse(bundle.pinpoint_evidence_report.all_cited_evidence_mapped)
        self.assertIn(
            "topology_undefined_term_status",
            bundle.pinpoint_evidence_report.missing_citation_claim_ids,
        )

    def test_strict_project_support_filter_does_not_fall_back_to_governing_evidence(self) -> None:
        project_entry = _project_entry(
            "topology_project_artifact_multiplicity",
            "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
            ClaimState.INTERPRETIVE,
        )
        governing_citation = _high_role_citation("governing_fallback_source")
        project_entry.supporting_evidence = [
            LedgerEvidence(
                citation=governing_citation,
                source_role_level=SourceRoleLevel.HIGH,
                source_kind=SourceKind.IMPLEMENTING_ACT,
                source_kind_rank=1,
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
        ]
        project_entry.citations = [governing_citation]

        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [project_entry],
            query_intent=_topology_intent(),
        )

        self.assertNotIn(
            "Evidence (medium-rank project support):",
            bundle.rendered_answer,
        )
        self.assertNotIn(
            "while medium-rank project artifacts make the multi-certificate interpretation more explicit.",
            bundle.rendered_answer,
        )

    def test_project_claim_with_no_strict_support_still_surfaces_generic_bullet(self) -> None:
        project_entry = _project_entry(
            "topology_project_artifact_multiplicity",
            "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
            ClaimState.INTERPRETIVE,
        )
        project_entry.supporting_evidence = []
        project_entry.governing_evidence = []
        project_entry.contradicting_evidence = []

        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [project_entry],
            query_intent=_topology_intent(),
        )

        self.assertIn("Interpretive:", bundle.rendered_answer)
        self.assertIn(
            "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
            bundle.rendered_answer,
        )
        self.assertNotIn(
            "Evidence (medium-rank project support):",
            bundle.rendered_answer,
        )

    def test_strict_filter_never_falls_back_to_entry_citations(self) -> None:
        project_entry = _project_entry(
            "topology_project_artifact_multiplicity",
            "Official project artifacts explicitly describe one or more access certificates for relying party instances.",
            ClaimState.INTERPRETIVE,
        )
        project_entry.supporting_evidence = []
        project_entry.governing_evidence = []
        project_entry.contradicting_evidence = []

        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [project_entry],
            query_intent=_topology_intent(),
        )

        self.assertNotIn(
            "The broader multiplicity or \"derived certificate\" conclusion is not stated as governing EU law. In this run, only medium-rank project artifacts make the multi-certificate interpretation more explicit;",
            bundle.rendered_answer,
        )

    def test_confirmed_medium_rank_generic_claim_does_not_fail_alignment(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            [
                _project_entry(
                    "synthetic_project_claim",
                    "Official project artifacts explicitly support this synthetic claim.",
                    ClaimState.CONFIRMED,
                )
            ],
        )

        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())
        self.assertIn("Confirmed:", bundle.rendered_answer)

    def test_generic_bundle_orders_sections_and_emits_cross_artifact_reports(self) -> None:
        entries = [
            _entry(
                "generic_confirmed_claim",
                "Governing EU sources confirm a synthetic registration requirement.",
                ClaimState.CONFIRMED,
            ),
            _project_entry(
                "generic_interpretive_claim",
                "Project artifacts add interpretive implementation detail for the synthetic requirement.",
                ClaimState.INTERPRETIVE,
            ),
            _entry(
                "generic_open_claim",
                "Governing EU sources leave a synthetic implementation boundary unresolved.",
                ClaimState.OPEN,
            ),
        ]

        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            entries,
            query_intent=_generic_intent("relying_party_registration_information"),
        )

        self.assertIsNone(bundle.facet_coverage_report)
        self.assertIn("Source-bound answer:", bundle.rendered_answer)
        self.assertLess(bundle.rendered_answer.index("Confirmed:"), bundle.rendered_answer.index("Interpretive:"))
        self.assertLess(bundle.rendered_answer.index("Interpretive:"), bundle.rendered_answer.index("Open:"))
        self.assertTrue(bundle.pinpoint_evidence_report.all_cited_evidence_mapped)
        self.assertEqual(
            {record.answer_claim_id for record in bundle.pinpoint_evidence_report.records},
            {"generic_confirmed_claim", "generic_interpretive_claim", "generic_open_claim"},
        )
        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())

    def test_generic_alignment_distinguishes_governing_and_non_governing_confirmed_claims(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            [
                _entry(
                    "generic_governing_claim",
                    "Governing EU sources confirm a synthetic high-rank claim.",
                    ClaimState.CONFIRMED,
                ),
                _project_entry(
                    "generic_project_claim",
                    "Project artifacts confirm a synthetic medium-rank claim.",
                    ClaimState.CONFIRMED,
                ),
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
        )

        categories_by_claim = {
            record.answer_claim_id: record.wording_category
            for record in bundle.answer_alignment_report.records
        }
        self.assertEqual(
            categories_by_claim["generic_governing_claim"],
            "governing_confirmed",
        )
        self.assertEqual(
            categories_by_claim["generic_project_claim"],
            "confirmed_non_governing",
        )

    def test_generic_bundle_keeps_non_topology_contract_for_grouping_capable_intent(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            [
                _entry(
                    "grouped_generic_claim",
                    "Governing EU sources confirm a grouped synthetic requirement.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent(
                "wallet_requirements_summary",
                grouping_label="Certificates and identity",
            ),
        )

        self.assertIsNone(bundle.facet_coverage_report)
        self.assertIn("Confirmed:", bundle.rendered_answer)
        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())

    def test_alignment_fails_when_governing_boundary_wording_uses_open_claims(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_registration_certificate_role",
                    "Governing EU sources define a wallet-relying party registration certificate as describing the relying party's intended use and the attributes it has registered to request from users.",
                    ClaimState.INTERPRETIVE,
                )
            ],
            query_intent=_topology_intent(),
        )

        bad_record = AnswerAlignmentRecord(
            answer_claim_id="synthetic",
            answer_section="Interpretive",
            wording_category="interpretive_governing_boundary",
            claim_ids=["topology_registration_certificate_role"],
            claim_states=[ClaimState.OPEN],
            cited_source_ids=["synthetic-source"],
            cited_source_roles=[SourceRoleLevel.HIGH],
            alignment_status="pass",
            notes=[],
        )
        bundle.answer_alignment_report.records = [bad_record]
        bundle.answer_alignment_report.blocking_violations = []

        # Re-run the actual internal path by composing with an open claim to ensure the rule is enforced.
        open_bundle = compose_answer_bundle(
            "Synthetic topology question?",
            [
                _entry(
                    "topology_registration_certificate_role",
                    "Governing EU sources define a wallet-relying party registration certificate as describing the relying party's intended use and the attributes it has registered to request from users.",
                    ClaimState.OPEN,
                )
            ],
            query_intent=_topology_intent(),
        )
        self.assertFalse(
            any(
                record.wording_category == "interpretive_governing_boundary"
                for record in open_bundle.answer_alignment_report.records
            )
        )


if __name__ == "__main__":
    unittest.main()
