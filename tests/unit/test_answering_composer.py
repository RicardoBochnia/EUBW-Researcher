from __future__ import annotations

import unittest
from typing import Optional

from eubw_researcher.answering import build_facet_coverage_report, compose_answer_bundle
from eubw_researcher.models import (
    AnswerAlignmentRecord,
    Citation,
    CitationQuality,
    ClaimTarget,
    ClaimState,
    ClaimType,
    ContradictionStatus,
    DocumentStatus,
    EvidenceSynthesisMatrix,
    EvidenceSynthesisRecord,
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
    grouping_label: Optional[str] = None,
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

    def test_generic_composer_qualifies_draft_support_in_rendered_answer(self) -> None:
        entry = _entry(
            "draft_obligation",
            "A draft legal source describes a Germany-specific implementation step.",
            ClaimState.INTERPRETIVE,
        )
        entry.governing_document_status = DocumentStatus.DRAFT

        bundle = compose_answer_bundle(
            "Synthetic draft question?",
            [entry],
            query_intent=_generic_intent(),
        )

        self.assertIn("Current draft support indicates:", bundle.rendered_answer)

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

    def test_vnext_dynamic_entries_are_rendered_as_opened_evidence_not_raw_claims(self) -> None:
        raw_snippet = (
            "Parliament and of the Council generic front matter that is useful as a "
            "retrieval hit but should not be promoted into composed answer prose."
        )
        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            [
                _entry(
                    "dynamic_cluster_1_regulation_document",
                    raw_snippet,
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
        )

        self.assertIn("Opened", bundle.rendered_answer)
        self.assertIn("standalone composed claim", bundle.rendered_answer)
        self.assertNotIn(raw_snippet, bundle.rendered_answer)
        categories_by_claim = {
            record.answer_claim_id: record.wording_category
            for record in bundle.answer_alignment_report.records
        }
        self.assertEqual(
            categories_by_claim["dynamic_cluster_1_regulation_document"],
            "dynamic_evidence_support",
        )
        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())

    def test_vnext_dynamic_entries_without_precise_locator_are_not_rendered(self) -> None:
        approximate_entry = _entry(
            "dynamic_cluster_unanchored_archive",
            "Opened archive evidence without an anchor should stay out of final prose.",
            ClaimState.INTERPRETIVE,
        )
        for citation in approximate_entry.citations:
            citation.anchor_label = None
            citation.canonical_url = "https://example.test/archive"
        for evidence in approximate_entry.supporting_evidence:
            evidence.citation.anchor_label = None
            evidence.citation.canonical_url = "https://example.test/archive"

        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            [approximate_entry],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
        )

        self.assertNotIn("dynamic_cluster_unanchored_archive", bundle.rendered_answer)
        self.assertNotIn("Opened archive evidence without an anchor", bundle.rendered_answer)
        self.assertNotIn(
            "dynamic_cluster_unanchored_archive",
            {
                record.answer_claim_id
                for record in bundle.pinpoint_evidence_report.records
            },
        )

    def test_vnext_review_details_compact_long_candidate_claims(self) -> None:
        long_claim = (
            " ".join(["Legacy imported snippet text that should be reviewable but compact."] * 40)
            + " TAIL_MARKER_SHOULD_NOT_RENDER"
        )

        bundle = compose_answer_bundle(
            "Synthetic generic question?",
            [_entry("CLM-LEGACY-LONG", long_claim, ClaimState.CONFIRMED)],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
        )

        self.assertIn("Pruefdetails:", bundle.rendered_answer)
        self.assertIn("Legacy imported snippet text", bundle.rendered_answer)
        self.assertIn("...", bundle.rendered_answer)
        self.assertNotIn("TAIL_MARKER_SHOULD_NOT_RENDER", bundle.rendered_answer)
        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())

    def test_vnext_product_summary_uses_reading_matrix_before_review_details(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Provider portability?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="synthesis_1",
                    claim_id="dynamic_cluster_1_ts10",
                    cluster_id="cluster_portability",
                    answer_role="candidate_core_claim",
                    statement=(
                        "The MigrationObject exportable object contains "
                        "TransactionLogObject, ListOfCredentials, and all "
                        "non-device-bound attestations files."
                    ),
                    source_ids=["ec_ts10_data_portability_export"],
                    chunk_ids=["chunk_1"],
                    locators=["4.2 Migration Object Structure"],
                    verification_status=ClaimState.INTERPRETIVE,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="synthesis_2",
                    claim_id="portability_reviewed_claim",
                    cluster_id="cluster_wua",
                    answer_role="candidate_core_claim",
                    statement="Wallet Unit Attestation lifecycle and revocation status anchor the target wallet unit.",
                    source_ids=["ec_ts03_wallet_unit_attestation"],
                    chunk_ids=["chunk_2"],
                    locators=["2.4 Life Cycle"],
                    verification_status=ClaimState.INTERPRETIVE,
                )
            ],
        )

        bundle = compose_answer_bundle(
            "Was passiert bei einem Wechsel des Wallet-Providers mit Nachweisen, Mandaten, Vertrauenskette und Auditspur, wenn echte Portabilitaet gefordert wird?",
            [
                _entry(
                    "dynamic_cluster_1_ts10",
                    "Raw MigrationObject snippet that should remain in review details.",
                    ClaimState.CONFIRMED,
                ),
                _entry(
                    "portability_reviewed_claim",
                    "Providerwechsel braucht eine kontrollierte Migration.",
                    ClaimState.CONFIRMED,
                ),
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        summary_index = bundle.rendered_answer.index("Kurzantwort:")
        details_index = bundle.rendered_answer.index("Pruefdetails:")
        opened_index = bundle.rendered_answer.index("Opened evidence")
        self.assertLess(summary_index, details_index)
        self.assertLess(details_index, opened_index)
        self.assertIn("MigrationObject", bundle.rendered_answer[:details_index])
        self.assertIn("ec_ts10_data_portability_export", bundle.rendered_answer[:details_index])
        self.assertIn("Mandate", bundle.rendered_answer[:details_index])
        self.assertIn("Vertrauenskette", bundle.rendered_answer[:details_index])
        self.assertIn("ec_ts03_wallet_unit_attestation", bundle.rendered_answer[:details_index])
        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())

    def test_vnext_renderer_trust_mark_product_answer(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Wann muss ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="trust_mark_remove",
                    claim_id="dynamic_cluster_1_trust_mark_removal",
                    cluster_id="cluster_trust_mark",
                    answer_role="core_answer_support",
                    statement=(
                        "Passage supports: Wenn die Zertifizierungs- oder Anerkennungsbasis "
                        "fuer die Wallet Solution nicht mehr gilt und eine cancellation "
                        "erfolgt, muss der Wallet Provider das sichtbare EUDI Wallet Trust "
                        "Mark entfernen."
                    ),
                    source_ids=["ec_ts01_wallet_trust_mark"],
                    chunk_ids=["ec_ts01_wallet_trust_mark:1.2"],
                    locators=[
                        "Specification of EUDI Wallet Trust Mark > 1 Introduction and Overview > 1.2 Scope for the Trust Mark Requirements and Design"
                    ],
                    facet_tags=["trust_mark_meaning", "trust_mark_removal"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="trust_mark_scope",
                    claim_id="dynamic_cluster_1_trust_mark_scope",
                    cluster_id="cluster_trust_mark",
                    answer_role="scope_boundary",
                    statement=(
                        "RP/AP Scope Boundary: Section 1.2 scopes the trust mark to "
                        "the Wallet solution and visible EUDI Wallet Trust Mark; it is "
                        "not a quality mark for Relying Party services or Attestation "
                        "Provider qualifications."
                    ),
                    source_ids=["ec_ts01_wallet_trust_mark"],
                    chunk_ids=["ec_ts01_wallet_trust_mark:1.2"],
                    locators=[
                        "Specification of EUDI Wallet Trust Mark > 1 Introduction and Overview > 1.2 Scope for the Trust Mark Requirements and Design"
                    ],
                    facet_tags=["trust_mark_meaning", "trust_mark_scope_boundary"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?",
            [
                _project_entry(
                    "dynamic_cluster_1_trust_mark_removal",
                    "Raw Trust-Mark passage that should be rendered as a product answer.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        details_index = bundle.rendered_answer.index("Pruefdetails:")
        short_answer = bundle.rendered_answer[:details_index]
        self.assertTrue(bundle.rendered_answer.startswith("Kurzantwort:"))
        self.assertNotIn("Passage supports", bundle.rendered_answer)
        self.assertIn("ec_ts01_wallet_trust_mark", short_answer)
        self.assertIn("1.2 Scope", short_answer)
        self.assertIn("Daraus folgt keine Bewertung", short_answer)
        self.assertIn("Relying Parties", short_answer)
        self.assertIn("Attestation Provider", short_answer)
        self.assertNotIn("RP/AP Scope Boundary", short_answer)

    def test_vnext_renderer_generic_trust_mark_answer_does_not_render_removal(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Was bedeutet das sichtbare Wallet-Vertrauenszeichen fuer Nutzer?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="trust_mark_meaning",
                    claim_id="dynamic_cluster_1_trust_mark_meaning",
                    cluster_id="cluster_trust_mark",
                    answer_role="core_answer_support",
                    statement=(
                        "The visible EUDI Wallet Trust Mark helps users recognize "
                        "the wallet solution and verify that the mark belongs to the wallet."
                    ),
                    source_ids=["ec_ts01_wallet_trust_mark"],
                    chunk_ids=["ec_ts01_wallet_trust_mark:1.1"],
                    locators=["Specification of EUDI Wallet Trust Mark > 1 Introduction and Overview > 1.1 Purpose"],
                    facet_tags=["trust_mark_meaning"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="loose_openid_context",
                    claim_id="dynamic_cluster_2_openid_context",
                    cluster_id="cluster_openid",
                    answer_role="background",
                    statement="OpenID material mentions wallet users but does not define the visible wallet trust mark.",
                    source_ids=["openid4vp_1_0_official"],
                    chunk_ids=["openid4vp:privacy"],
                    locators=["OpenID for Verifiable Presentations 1.0 > 15 Privacy Considerations"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Was bedeutet das sichtbare Wallet-Vertrauenszeichen fuer Nutzer?",
            [
                _project_entry(
                    "dynamic_cluster_1_trust_mark_meaning",
                    "Raw Trust-Mark meaning passage.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        details_index = bundle.rendered_answer.index("Pruefdetails:")
        short_answer = bundle.rendered_answer[:details_index]
        self.assertIn("Trust-Hinweis", short_answer)
        self.assertIn("ec_ts01_wallet_trust_mark", short_answer)
        self.assertNotIn("OpenID", short_answer)
        self.assertNotIn("Aufhebung", short_answer)
        self.assertNotIn("entfernen", short_answer.lower())
        self.assertNotIn("Removal", short_answer)

    def test_vnext_renderer_generic_trust_mark_keeps_schema_context_secondary(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Was bedeutet das sichtbare Wallet-Vertrauenszeichen fuer Nutzer?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="celex_trust_mark_meaning",
                    claim_id="dynamic_cluster_1_celex_meaning",
                    cluster_id="cluster_celex_trust_mark",
                    answer_role="normative_basis",
                    statement=(
                        "The EU Digital Identity Wallet Trust Mark should be used to "
                        "indicate in a clear, simple and recognisable manner that a "
                        "wallet has been provided in accordance with Regulation (EU) "
                        "No 910/2014."
                    ),
                    source_ids=["celex_32024R2981_fulltext_en"],
                    chunk_ids=["celex_32024R2981:recital_15"],
                    locators=["Commission Implementing Regulation (EU) 2024/2981 > Recital 15"],
                    facet_tags=["trust_mark_meaning"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="ec_ts01_schema",
                    claim_id="dynamic_cluster_2_ec_ts01_schema",
                    cluster_id="cluster_ec_ts01_schema",
                    answer_role="core_answer_support",
                    statement="A.1 WalletTrustMarkInformation JSON Schema (normative).",
                    source_ids=["ec_ts01_wallet_trust_mark"],
                    chunk_ids=["ec_ts01_wallet_trust_mark:annex_a"],
                    locators=["Specification of EUDI Wallet Trust Mark > Annex A > A.1 WalletTrustMarkInformation JSON Schema"],
                    facet_tags=["trust_mark_meaning"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Was bedeutet das sichtbare Wallet-Vertrauenszeichen fuer Nutzer?",
            [
                _project_entry(
                    "dynamic_cluster_1_celex_meaning",
                    "Trust-Mark meaning support.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer[: bundle.rendered_answer.index("Pruefdetails:")]
        first_bullet = short_answer.splitlines()[1]
        self.assertIn("celex_32024R2981_fulltext_en", short_answer)
        self.assertNotIn("ec_ts01_wallet_trust_mark", first_bullet)
        self.assertIn("ec_ts01_wallet_trust_mark", short_answer)
        self.assertIn("Technischer Kontext", short_answer)

    def test_vnext_renderer_pseudonym_sources_require_matching_facets(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Wann kann ein Wallet-Use-Case pseudonyme Authentifizierung nutzen?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="pseudonym_legal",
                    claim_id="dynamic_cluster_1_pseudonym_legal",
                    cluster_id="cluster_pseudonym",
                    answer_role="normative_basis",
                    statement="Relying parties shall not refuse pseudonyms where identification is not legally required.",
                    source_ids=["celex_32024R1183_fulltext_en"],
                    chunk_ids=["celex:5b"],
                    locators=["Article 5b"],
                    facet_tags=["pseudonym_legal_permission"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="loose_account_background",
                    claim_id="dynamic_cluster_2_loose_account",
                    cluster_id="cluster_account",
                    answer_role="background",
                    statement="A nearby source mentions account handling but does not answer pseudonym account binding.",
                    source_ids=["loose_account_source"],
                    chunk_ids=["loose:1"],
                    locators=["Loose account context"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Wann kann ein Wallet-Use-Case pseudonyme Authentifizierung nutzen?",
            [
                _entry(
                    "dynamic_cluster_1_pseudonym_legal",
                    "Pseudonym legal support.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer[: bundle.rendered_answer.index("Pruefdetails:")]
        self.assertIn("celex_32024R1183_fulltext_en", short_answer)
        self.assertNotIn("loose_account_source", short_answer)

    def test_synthesis_matrix_rejects_references_and_table_notes_as_core_answer(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Welche Informationen muss die Nutzeranzeige bei Intermediaeren zeigen?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="references",
                    claim_id="references_claim",
                    cluster_id="cluster_refs",
                    answer_role="core_answer",
                    statement="References: [1] Generic registration API. [2] Annex table.",
                    source_ids=["references_source"],
                    chunk_ids=["references_chunk"],
                    locators=["References"],
                    facet_tags=["user_display"],
                    quality_flags=["references_only"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="display",
                    claim_id="display_claim",
                    cluster_id="cluster_display",
                    answer_role="core_answer",
                    statement=(
                        "The user display shows the intermediary, the intermediated "
                        "Wallet-Relying Party, requested attributes, intended use, and privacy policy."
                    ),
                    source_ids=["eudi_arf_main_markdown"],
                    chunk_ids=["display_chunk"],
                    locators=["ARF 6.6.5"],
                    facet_tags=[
                        "actor_boundary",
                        "user_display",
                        "purpose_or_intended_use",
                        "requested_attributes",
                        "privacy_policy_or_dpa",
                    ],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck, Attribute und Datenschutzinformationen auseinanderhalten?",
            [_entry("display_claim", "Display claim.", ClaimState.CONFIRMED)],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer.split("Pruefdetails:", 1)[0]
        self.assertIn("eudi_arf_main_markdown", short_answer)
        self.assertNotIn("References:", short_answer)

    def test_vnext_renderer_rp_intermediary_product_answer(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="RP intermediary disclosure",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="actor",
                    claim_id="actor_claim",
                    cluster_id="cluster_actor",
                    answer_role="core_answer",
                    statement=(
                        "The intermediary authenticates technically to the Wallet Unit "
                        "with its access certificate while acting for an intermediated Wallet-Relying Party."
                    ),
                    source_ids=["eudi_arf_main_markdown"],
                    chunk_ids=["actor_chunk"],
                    locators=["ARF 6.6.5"],
                    facet_tags=["actor_boundary", "technical_requester", "end_relying_party"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="registry",
                    claim_id="registry_claim",
                    cluster_id="cluster_registry",
                    answer_role="core_answer",
                    statement=(
                        "The registration certificate contains Relying Party information "
                        "for the service and must preserve the intermediated Wallet-Relying Party."
                    ),
                    source_ids=["ec_ts05_rp_registration_api"],
                    chunk_ids=["registry_chunk"],
                    locators=["TS05 WalletRelyingParty.usesIntermediary"],
                    facet_tags=["registry_information", "certificate_or_trust_anchor", "end_relying_party"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="display",
                    claim_id="display_claim",
                    cluster_id="cluster_display",
                    answer_role="core_answer",
                    statement=(
                        "The information set shown to the user includes intended use, "
                        "requested attributes, request context, privacy policy, and the relevant Relying Party."
                    ),
                    source_ids=["ec_ts06_rp_information_set"],
                    chunk_ids=["display_chunk"],
                    locators=["TS06 RP information set"],
                    facet_tags=[
                        "user_display",
                        "purpose_or_intended_use",
                        "requested_attributes",
                        "privacy_policy_or_dpa",
                    ],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck, Attribute und Datenschutzinformationen auseinanderhalten?",
            [
                _entry("actor_claim", "Actor claim.", ClaimState.CONFIRMED),
                _entry("registry_claim", "Registry claim.", ClaimState.CONFIRMED),
                _entry("display_claim", "Display claim.", ClaimState.CONFIRMED),
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer.split("Pruefdetails:", 1)[0]
        self.assertTrue(bundle.rendered_answer.startswith("Kurzantwort:"))
        for heading in [
            "Registrierung / Zertifikate:",
            "Nutzeranzeige / Request-Kontext:",
            "Zweck, Attribute und Datenschutz:",
            "Grenzen / offene Punkte:",
        ]:
            self.assertIn(heading, short_answer)
        self.assertIn("Intermediaer", short_answer)
        self.assertIn("Wallet-Relying Party", short_answer)
        self.assertIn("Attribute", short_answer)
        self.assertIn("Datenschutz", short_answer)
        self.assertIn("eudi_arf_main_markdown", short_answer)
        self.assertIn("ARF 6.6.5", short_answer)

    def test_vnext_renderer_demotes_off_topic_verified_claims(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question="Wallet trust mark boundary?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="trust_mark_scope",
                    claim_id="dynamic_cluster_1_trust_mark_scope",
                    cluster_id="cluster_trust_mark",
                    answer_role="core_answer_support",
                    statement=(
                        "The visible EUDI Wallet Trust Mark is scoped to the Wallet "
                        "solution; it does not certify Relying Party service quality "
                        "or Attestation Provider qualifications."
                    ),
                    source_ids=["ec_ts01_wallet_trust_mark"],
                    chunk_ids=["ec_ts01_wallet_trust_mark:1.2"],
                    locators=["Section 1.2 Scope for the Trust Mark Requirements and Design"],
                    verification_status=ClaimState.CONFIRMED,
                )
            ],
        )
        generic_wrp_claim = (
            "Governing EU sources define a wallet-relying party access certificate "
            "as authenticating and validating the wallet-relying party in wallet interactions."
        )
        generic_certificate_claim = (
            "Governing EU sources describe access certificates as part of the relying-party "
            "trust infrastructure."
        )

        bundle = compose_answer_bundle(
            "Bewertet das sichtbare Wallet-Vertrauenszeichen auch Relying Parties oder Attestation Provider?",
            [
                _entry(
                    "generic_wrp_access_certificate",
                    generic_wrp_claim,
                    ClaimState.CONFIRMED,
                ),
                _entry(
                    "generic_access_certificate_ledger_claim",
                    generic_certificate_claim,
                    ClaimState.CONFIRMED,
                ),
                _project_entry(
                    "dynamic_cluster_1_trust_mark_scope",
                    "Trust-Mark Section 1.2 gives the specific answer boundary.",
                    ClaimState.CONFIRMED,
                ),
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        details_index = bundle.rendered_answer.index("Pruefdetails:")
        short_answer = bundle.rendered_answer[:details_index]
        details = bundle.rendered_answer[details_index:]
        self.assertIn("ec_ts01_wallet_trust_mark", short_answer)
        self.assertNotIn(generic_wrp_claim, short_answer)
        self.assertNotIn(generic_certificate_claim, short_answer)
        self.assertIn(generic_wrp_claim, details)
        self.assertIn(generic_certificate_claim, details)
        self.assertLess(
            bundle.rendered_answer.index("ec_ts01_wallet_trust_mark"),
            bundle.rendered_answer.index(generic_wrp_claim),
        )

    def test_vnext_renderer_excludes_not_answer_eligible_matrix_records(self) -> None:
        blocked_statement = (
            "The blocked matrix record is tempting, specific, and should never appear "
            "in the user-facing answer."
        )
        allowed_statement = "Allowed evidence remains available for the short answer."
        matrix = EvidenceSynthesisMatrix(
            question="Synthetic verification question?",
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="blocked_synthesis",
                    claim_id="blocked_dynamic_claim",
                    cluster_id="blocked_cluster",
                    answer_role="core_answer",
                    statement=blocked_statement,
                    source_ids=["blocked_source"],
                    chunk_ids=["blocked_chunk"],
                    locators=["Blocked locator"],
                    verification_status=ClaimState.OPEN,
                    caveats=["verification does not allow answer use"],
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="allowed_synthesis",
                    claim_id="allowed_dynamic_claim",
                    cluster_id="allowed_cluster",
                    answer_role="core_answer",
                    statement=allowed_statement,
                    source_ids=["allowed_source"],
                    chunk_ids=["allowed_chunk"],
                    locators=["Allowed locator"],
                    verification_status=ClaimState.INTERPRETIVE,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            "Synthetic verification question?",
            [
                _entry("allowed_dynamic_claim", "Allowed ledger fallback.", ClaimState.CONFIRMED)
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        details_index = bundle.rendered_answer.index("Pruefdetails:")
        short_answer = bundle.rendered_answer[:details_index]
        self.assertIn(allowed_statement, short_answer)
        self.assertNotIn(blocked_statement, short_answer)

    def test_vnext_wua_pid_question_uses_matrix_instead_of_student_binding_template(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question=(
                "Welche Informationen und Pruefungen rund um die Wallet Unit Attestation "
                "braucht ein PID- oder Attribut-Aussteller?"
            ),
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="wua_provider_responsibilities",
                    claim_id="dynamic_cluster_wua_transport",
                    cluster_id="cluster_wua",
                    answer_role="core_answer_support",
                    statement=(
                        "A PID Provider or an Attestation Provider issuing device-bound "
                        "attestations SHALL indicate `proof_types_supported` support for "
                        "key attestations in its Issuer Credential Metadata and verify the "
                        "WUA signature, x5c trust anchor chain, attested key binding, and "
                        "c_nonce freshness."
                    ),
                    source_ids=["ec_ts03_wallet_unit_attestation"],
                    chunk_ids=["ec_ts03:2.2.2.2"],
                    locators=[
                        "2 Solution Description > 2.2 Transport > 2.2.2.2 PID Providers and Attestation Providers Responsibilities for Transport of WUAs"
                    ],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.INTERPRETIVE,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="wua_scope_boundary",
                    claim_id="dynamic_cluster_wua_scope",
                    cluster_id="cluster_wua",
                    answer_role="scope_boundary",
                    statement=(
                        "How Wallet Providers issue WUAs to the Wallet Unit is out of scope "
                        "for this technical specification."
                    ),
                    source_ids=["ec_ts03_wallet_unit_attestation"],
                    chunk_ids=["ec_ts03:1.2"],
                    locators=["Specification of Wallet Unit Attestations > 1.2 Scope"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.INTERPRETIVE,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            (
                "Welche Informationen und Pruefungen rund um die Wallet Unit Attestation "
                "braucht ein PID- oder Attribut-Aussteller?"
            ),
            [
                _project_entry(
                    "dynamic_cluster_wua_transport",
                    "Raw WUA passage.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer[: bundle.rendered_answer.index("Pruefdetails:")]
        self.assertIn("ec_ts03_wallet_unit_attestation", short_answer)
        self.assertIn("Wallet Unit Attestation", short_answer)
        self.assertIn("Issuer Credential Metadata", short_answer)
        self.assertIn("Trust-Anchor", short_answer)
        self.assertIn("c_nonce", short_answer)
        self.assertIn("Ausserhalb", short_answer)
        self.assertNotIn("SHALL indicate", short_answer)
        self.assertNotIn("Note that *how*", short_answer)
        self.assertNotIn("Immatrikulationsbescheinigungen", short_answer)
        self.assertNotIn("Studierendenausweise", short_answer)

    def test_vnext_wallet_certification_answer_prefers_normative_certification_records(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question=(
                "Was regelt die Durchfuehrungsverordnung zur Zertifizierung von "
                "EUDI-Wallet-Loesungen ueber Zertifikate?"
            ),
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="certification_scheme",
                    claim_id="dynamic_certification_2981",
                    cluster_id="cluster_celex_2981",
                    answer_role="normative_basis",
                    statement=(
                        "National certification schemes shall include governance rules, "
                        "certificate issuance timelines, and evaluation activities for the "
                        "wallet solution."
                    ),
                    source_ids=["celex_32024R2981_fulltext_en"],
                    chunk_ids=["celex_2981:article_6"],
                    locators=["Article 6"],
                    facet_tags=["wallet_solution_certification", "certificate_or_trust_anchor"],
                    quality_flags=["snippet_like"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="arf_noise",
                    claim_id="dynamic_arf_noise",
                    cluster_id="cluster_arf",
                    answer_role="technical_spec_context",
                    statement=(
                        "Topic 10 in Annex 2 calls this method once-only attestations "
                        "and requires Wallet Solutions to support this method."
                    ),
                    source_ids=["eudi_arf_main_markdown"],
                    chunk_ids=["arf:topic_10"],
                    locators=["ARF > 7 Wallet Solution Certification and Risk Management"],
                    facet_tags=["wallet_solution_certification"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.INTERPRETIVE,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            (
                "Was regelt die Durchfuehrungsverordnung zur Zertifizierung von "
                "EUDI-Wallet-Loesungen ueber Zertifikate?"
            ),
            [
                _entry(
                    "dynamic_certification_2981",
                    "Raw certification support.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer[: bundle.rendered_answer.index("Pruefdetails:")]
        self.assertIn("celex_32024R2981_fulltext_en", short_answer)
        self.assertIn("Zertifizierungs-Durchfuehrungsverordnung", short_answer)
        self.assertNotIn("once-only attestations", short_answer)

    def test_vnext_openidvp_state_nonce_answer_uses_protocol_parameter_records(self) -> None:
        matrix = EvidenceSynthesisMatrix(
            question=(
                "Welche Rolle spielen state und nonce in OpenID4VP beim Schutz von "
                "Wallet-Interaktionen gegen CSRF, Replay oder falsche Response-Zuordnung?"
            ),
            records=[
                EvidenceSynthesisRecord(
                    synthesis_id="openidvp_state_response",
                    claim_id="dynamic_openidvp_state",
                    cluster_id="cluster_openidvp",
                    answer_role="normative_basis",
                    statement=(
                        "The Wallet sends the Authorization Response with the parameters "
                        "vp_token and state to the response_uri of the Verifier; the "
                        "Response URI checks whether the state value is a valid request-id."
                    ),
                    source_ids=["openid4vp_1_0_official"],
                    chunk_ids=["openid4vp:13.3"],
                    locators=["OpenID4VP > 13.3 Response Mode direct_post"],
                    facet_tags=["protocol_security_parameter"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="openidvp_nonce_replay",
                    claim_id="dynamic_openidvp_nonce",
                    cluster_id="cluster_openidvp",
                    answer_role="normative_basis",
                    statement=(
                        "The cryptographic proof of possession in a Verifiable Presentation "
                        "MUST be bound to the respective transaction identified by the nonce "
                        "parameter; the Verifier MUST reject a response that does not contain "
                        "the correct nonce value."
                    ),
                    source_ids=["openid4vp_1_0_official"],
                    chunk_ids=["openid4vp:14.1"],
                    locators=["OpenID4VP > 14.1 Preventing Replay of Verifiable Presentations"],
                    facet_tags=["protocol_security_parameter"],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
                EvidenceSynthesisRecord(
                    synthesis_id="notification_noise",
                    claim_id="dynamic_notification_noise",
                    cluster_id="cluster_celex_2980",
                    answer_role="normative_basis",
                    statement="The Commission shall make available a secure electronic notification system.",
                    source_ids=["celex_32024R2980_fulltext_en"],
                    chunk_ids=["celex_2980:article_3"],
                    locators=["Article 3"],
                    facet_tags=[],
                    quality_flags=["answer_ready"],
                    verification_status=ClaimState.CONFIRMED,
                ),
            ],
        )

        bundle = compose_answer_bundle(
            (
                "Welche Rolle spielen state und nonce in OpenID4VP beim Schutz von "
                "Wallet-Interaktionen gegen CSRF, Replay oder falsche Response-Zuordnung?"
            ),
            [
                _entry(
                    "dynamic_openidvp_state",
                    "Raw state support.",
                    ClaimState.CONFIRMED,
                )
            ],
            query_intent=_generic_intent("wallet_requirements_summary"),
            composer_mode="vnext",
            evidence_synthesis_matrix=matrix,
        )

        short_answer = bundle.rendered_answer[: bundle.rendered_answer.index("Pruefdetails:")]
        self.assertIn("`state`", short_answer)
        self.assertIn("`nonce`", short_answer)
        self.assertIn("Replay", short_answer)
        self.assertIn("openid4vp_1_0_official", short_answer)
        self.assertNotIn("notification system", short_answer)

    def test_eubw_structured_answer_uses_parity_sections(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic EUBW role question?",
            [
                _entry(
                    "eubw_registrar_boundary",
                    "Registrars manage national registers.",
                    ClaimState.CONFIRMED,
                ),
                _project_entry(
                    "eubw_project_context",
                    "Project artifacts add implementation context.",
                    ClaimState.INTERPRETIVE,
                ),
                _entry(
                    "eubw_open_boundary",
                    "A later specification boundary remains open.",
                    ClaimState.OPEN,
                ),
            ],
            query_intent=_generic_intent("eubw_role_boundary_analysis"),
        )

        self.assertIn("Kurzantwort:", bundle.rendered_answer)
        self.assertIn("Normative evidence:", bundle.rendered_answer)
        self.assertIn("Interpretation/context:", bundle.rendered_answer)
        self.assertIn("Open issues:", bundle.rendered_answer)
        self.assertNotIn("Confirmed:", bundle.rendered_answer)
        self.assertFalse(bundle.answer_alignment_report.has_blocking_violations())

    def test_eubw_architecture_answer_renders_three_buckets(self) -> None:
        bundle = compose_answer_bundle(
            "Synthetic EUBW architecture question?",
            [
                _entry(
                    "eubw_direct_architecture_constraints",
                    "Proposal-stage sources directly support a secure channel constraint.",
                    ClaimState.INTERPRETIVE,
                ),
                _entry(
                    "eubw_identifier_delegated_specs",
                    "Identifier structure is delegated to implementing acts.",
                    ClaimState.INTERPRETIVE,
                ),
                _entry(
                    "eubw_trust_model_still_open",
                    "The concrete trust model remains open.",
                    ClaimState.OPEN,
                ),
            ],
            query_intent=_generic_intent("eubw_architecture_bucket_analysis"),
        )

        self.assertIn("Kurzantwort:", bundle.rendered_answer)
        self.assertIn("direkt ableitbar:", bundle.rendered_answer)
        self.assertIn("delegiert:", bundle.rendered_answer)
        self.assertIn("plausible Annahme:", bundle.rendered_answer)
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
