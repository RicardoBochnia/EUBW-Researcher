from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.evidence import build_ledger
from eubw_researcher.models import (
    AnchorAudit,
    AnchorQuality,
    Citation,
    CitationQuality,
    ClaimState,
    ClaimTarget,
    ClaimType,
    QueryIntent,
    RetrievalCandidate,
    SourceChunk,
    SourceHierarchyConfig,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    HierarchyRule,
)


def make_candidate(
    source_id: str,
    text: str,
    source_kind: SourceKind,
    source_role_level: SourceRoleLevel,
    citation_quality: CitationQuality,
    anchor_label: str = "Section 1",
    anchor_audit: AnchorAudit = None,
    anchor_quality: AnchorQuality = None,
) -> RetrievalCandidate:
    citation = Citation(
        source_id=source_id,
        document_title=source_id,
        source_role_level=source_role_level,
        source_kind=source_kind,
        jurisdiction="EU",
        citation_quality=citation_quality,
        document_path=Path(f"/tmp/{source_id}.md"),
        canonical_url=None,
        anchor_label=anchor_label if citation_quality == CitationQuality.ANCHOR_GROUNDED else None,
        structure_poor=citation_quality == CitationQuality.DOCUMENT_ONLY,
        anchor_audit_note=anchor_audit.audit_note if anchor_audit else None,
    )
    chunk = SourceChunk(
        source_id=source_id,
        chunk_id=f"{source_id}::chunk",
        title=source_id,
        source_kind=source_kind,
        source_role_level=source_role_level,
        source_origin=SourceOrigin.LOCAL,
        jurisdiction="EU",
        text=text,
        citation=citation,
        technical_anchor_failure=False,
        anchor_quality=anchor_quality
        or (
            AnchorQuality.STRONG
            if citation_quality == CitationQuality.ANCHOR_GROUNDED
            else AnchorQuality.WEAK
        ),
        extracted_anchor_label=anchor_label if citation_quality == CitationQuality.ANCHOR_GROUNDED else None,
        anchor_audit=anchor_audit,
    )
    return RetrievalCandidate(
        chunk=chunk,
        lexical_score=1.0,
        semantic_score=1.0,
        combined_score=1.0,
    )


def make_target() -> ClaimTarget:
    return ClaimTarget(
        target_id="authorization_server_rule",
        claim_text="The protocol requires an authorization server for the scoped flow.",
        claim_type=ClaimType.PROTOCOL_BEHAVIOR,
        required_source_role_level=SourceRoleLevel.HIGH,
        preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        scope_terms=["presentation", "verifier"],
        primary_terms=["authorization", "server"],
        support_groups=[["authorization server", "presentation request"]],
        contradiction_groups=[["does not define", "authorization server"]],
    )


def make_regulation_target() -> ClaimTarget:
    return ClaimTarget(
        target_id="regulatory_certificate_rule",
        claim_text="The regulation requires a registration certificate for the regulated access flow.",
        claim_type=ClaimType.OBLIGATION,
        required_source_role_level=SourceRoleLevel.HIGH,
        preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
        scope_terms=["registration", "certificate"],
        primary_terms=["regulation", "certificate", "access"],
        support_groups=[["regulation", "registration certificate"]],
        contradiction_groups=[["does not require", "registration certificate"]],
    )


def make_hierarchy() -> SourceHierarchyConfig:
    return SourceHierarchyConfig(
        rules=[
            HierarchyRule(SourceKind.REGULATION, SourceRoleLevel.HIGH, 1),
            HierarchyRule(SourceKind.IMPLEMENTING_ACT, SourceRoleLevel.HIGH, 2),
            HierarchyRule(SourceKind.TECHNICAL_STANDARD, SourceRoleLevel.HIGH, 3),
            HierarchyRule(SourceKind.PROJECT_ARTIFACT, SourceRoleLevel.MEDIUM, 4),
            HierarchyRule(SourceKind.SCIENTIFIC_LITERATURE, SourceRoleLevel.MEDIUM, 5),
            HierarchyRule(SourceKind.NATIONAL_IMPLEMENTATION, SourceRoleLevel.MEDIUM, 6),
            HierarchyRule(SourceKind.COMMENTARY, SourceRoleLevel.LOW, 7),
        ]
    )


class LedgerControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hierarchy = make_hierarchy()

    def test_confirmed_state_uses_high_rank_anchor_grounded_support(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        candidate = make_candidate(
            "high_standard",
            "Verifier presentation request uses an Authorization Server for this flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.ANCHOR_GROUNDED,
        )

        ledger = build_ledger(intent, {"step_1": [candidate]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.CONFIRMED)

    def test_interpretive_state_downgrades_medium_rank_support(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        candidate = make_candidate(
            "project_note",
            "Verifier presentation request may use an Authorization Server in practice.",
            SourceKind.PROJECT_ARTIFACT,
            SourceRoleLevel.MEDIUM,
            CitationQuality.ANCHOR_GROUNDED,
        )

        ledger = build_ledger(intent, {"step_1": [candidate]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.INTERPRETIVE)

    def test_blocked_state_rejects_low_rank_only_support(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        candidate = make_candidate(
            "commentary_blog",
            "Verifier presentation request uses an Authorization Server everywhere.",
            SourceKind.COMMENTARY,
            SourceRoleLevel.LOW,
            CitationQuality.DOCUMENT_ONLY,
        )

        ledger = build_ledger(intent, {"step_1": [candidate]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.BLOCKED)

    def test_open_state_preserves_same_rank_conflict(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        support = make_candidate(
            "supporting_standard",
            "Verifier presentation request uses an Authorization Server for this flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.ANCHOR_GROUNDED,
        )
        contradiction = make_candidate(
            "contradicting_standard",
            "Verifier presentation request does not define an Authorization Server for this flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.ANCHOR_GROUNDED,
        )

        ledger = build_ledger(intent, {"step_1": [support, contradiction]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.OPEN)
        self.assertEqual(len(ledger[0].supporting_evidence), 1)
        self.assertEqual(len(ledger[0].contradicting_evidence), 1)

    def test_document_only_support_stays_interpretive_without_confirmable_anchor_audit(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        candidate = make_candidate(
            "document_only_standard",
            "Verifier presentation request uses an Authorization Server for this flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.DOCUMENT_ONLY,
            anchor_audit=AnchorAudit(
                expected_anchorable=True,
                content_retrievable=True,
                parser_or_structure_limitation=True,
                structure_poor=True,
                audit_note="No usable anchors; still not confirmation-grade.",
            ),
        )

        ledger = build_ledger(intent, {"step_1": [candidate]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.INTERPRETIVE)

    def test_document_only_support_can_confirm_when_anchor_audit_is_technical_not_epistemic(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        candidate = make_candidate(
            "document_only_confirmable_standard",
            "Verifier presentation request uses an Authorization Server for this flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.DOCUMENT_ONLY,
            anchor_audit=AnchorAudit(
                expected_anchorable=True,
                content_retrievable=True,
                parser_or_structure_limitation=True,
                structure_poor=False,
                audit_note="Expected anchors were not recoverable; treat this as a technical extraction failure because the governing source remains directly readable.",
            ),
            anchor_quality=AnchorQuality.MISSING,
        )

        ledger = build_ledger(intent, {"step_1": [candidate]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.CONFIRMED)

    def test_high_rank_support_is_not_reopened_by_lower_rank_contradiction(self) -> None:
        target = make_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )
        support = make_candidate(
            "supporting_standard",
            "Verifier presentation request uses an Authorization Server for this flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.ANCHOR_GROUNDED,
        )
        contradiction = make_candidate(
            "project_note",
            "Verifier presentation request does not define an Authorization Server for this flow.",
            SourceKind.PROJECT_ARTIFACT,
            SourceRoleLevel.MEDIUM,
            CitationQuality.ANCHOR_GROUNDED,
        )

        ledger = build_ledger(intent, {"step_1": [support, contradiction]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.CONFIRMED)
        self.assertEqual(ledger[0].source_role_level, SourceRoleLevel.HIGH)

    def test_high_precedence_regulation_is_not_reopened_by_lower_precedence_high_standard(self) -> None:
        target = make_regulation_target()
        intent = QueryIntent(
            question="test",
            intent_type="test",
            eu_first=True,
            claim_targets=[target],
            preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
        )
        support = make_candidate(
            "governing_regulation",
            "This regulation requires a registration certificate for the access flow.",
            SourceKind.REGULATION,
            SourceRoleLevel.HIGH,
            CitationQuality.ANCHOR_GROUNDED,
        )
        contradiction = make_candidate(
            "lower_precedence_standard",
            "This technical standard does not require a registration certificate for the access flow.",
            SourceKind.TECHNICAL_STANDARD,
            SourceRoleLevel.HIGH,
            CitationQuality.ANCHOR_GROUNDED,
        )

        ledger = build_ledger(intent, {"step_1": [support, contradiction]}, self.hierarchy)
        self.assertEqual(ledger[0].final_claim_state, ClaimState.CONFIRMED)
        self.assertEqual(ledger[0].citations[0].source_kind, SourceKind.REGULATION)


if __name__ == "__main__":
    unittest.main()
