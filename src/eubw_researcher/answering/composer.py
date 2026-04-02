from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

from eubw_researcher.models import (
    AnswerAlignmentRecord,
    AnswerAlignmentReport,
    Citation,
    CitationQuality,
    ClaimState,
    FacetCoverageFacet,
    FacetCoverageReport,
    LedgerEntry,
    PinpointEvidenceRecord,
    PinpointEvidenceReport,
    QueryIntent,
    SourceDocument,
    SourceKind,
    SourceRoleLevel,
    SupportDirectness,
)

TOPOLOGY_FACET_IDS = [
    "multiplicity_single_certificate",
    "derived_certificate_term_status",
    "registration_certificate_role",
    "access_certificate_role",
    "unresolved_or_interpretive_status",
]
TOPOLOGY_NOT_DEFINED_LABEL = "Not explicitly defined"
TOPOLOGY_NOT_DEFINED_PREFIX = "No governing EU source in the current corpus explicitly defines"
TOPOLOGY_SCOPING_SENTENCE = (
    "The governing EU material supports intended-use / service scoping: registration "
    "certificates are tied to intended use and requested attributes, access certificates "
    "authenticate the wallet-relying party, and registration-certificate issuance depends "
    "on a valid access certificate. But the governing texts do not expressly resolve "
    "whether one wallet-relying party is limited to a single organisation-level certificate."
)
TOPOLOGY_UNRESOLVED_WITH_PROJECT_SUPPORT_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. The current run can justify only a non-governing reading: "
    "governing EU text supports the boundary conditions, while medium-rank project "
    "artifacts make the multi-certificate interpretation more explicit."
)
TOPOLOGY_UNRESOLVED_GOVERNING_ONLY_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. This run preserves the governing boundary conditions, but it does "
    "not surface approved medium-rank project-artifact support that would make a "
    "multi-certificate interpretation more explicit."
)
TOPOLOGY_UNRESOLVED_PROJECT_ONLY_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. In this run, only medium-rank project artifacts make the "
    "multi-certificate interpretation more explicit; governing EU boundary support for "
    "that interpretation is not approved here."
)
TOPOLOGY_UNRESOLVED_NO_APPROVED_SUPPORT_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. This run does not surface approved governing-boundary support or "
    "approved medium-rank project-artifact support for that interpretation."
)


@dataclass
class _EvidenceLine:
    label: str
    citations: List[Citation] = field(default_factory=list)


@dataclass
class _AnswerBullet:
    bullet_id: str
    section: str
    text: str
    rationale: Optional[str] = None
    wording_category: str = "state_forwarded"
    claim_ids: List[str] = field(default_factory=list)
    claim_states: List[ClaimState] = field(default_factory=list)
    evidence_lines: List[_EvidenceLine] = field(default_factory=list)
    explicit_role_partitioning: bool = False


@dataclass
class ComposedAnswerBundle:
    rendered_answer: str
    facet_coverage_report: Optional[FacetCoverageReport]
    pinpoint_evidence_report: PinpointEvidenceReport
    answer_alignment_report: AnswerAlignmentReport


def _role_weight(role_level: SourceRoleLevel) -> int:
    return {
        SourceRoleLevel.HIGH: 3,
        SourceRoleLevel.MEDIUM: 2,
        SourceRoleLevel.LOW: 1,
    }[role_level]


def _citation_weight(citation_quality: CitationQuality) -> int:
    return 2 if citation_quality == CitationQuality.ANCHOR_GROUNDED else 1


def _dedupe_citations(citations: Iterable[Citation]) -> List[Citation]:
    unique: List[Citation] = []
    seen = set()
    for citation in citations:
        key = (
            citation.source_id,
            citation.anchor_label,
            citation.canonical_url,
            citation.document_title,
            citation.source_kind,
            citation.source_role_level,
            citation.source_origin,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique


def _render_citations(citations: Iterable[Citation]) -> str:
    deduped = _dedupe_citations(citations)
    if not deduped:
        return "no admissible citation"
    return "; ".join(citation.render() for citation in deduped)


def _render_bullets(
    summary: str,
    bullets: Sequence[_AnswerBullet],
    clarification_note: Optional[str],
) -> str:
    lines: List[str] = [summary]
    if clarification_note:
        lines.append(f"First-pass note: {clarification_note}")

    section_order = [TOPOLOGY_NOT_DEFINED_LABEL, "Confirmed", "Interpretive", "Open"]
    present_sections = []
    for section in section_order:
        if any(bullet.section == section for bullet in bullets):
            present_sections.append(section)
    for bullet in bullets:
        if bullet.section not in present_sections:
            present_sections.append(bullet.section)

    for section in present_sections:
        section_bullets = [bullet for bullet in bullets if bullet.section == section]
        if not section_bullets:
            continue
        lines.append(f"{section}:")
        for bullet in section_bullets:
            lines.append(f"- {bullet.text}")
            if bullet.rationale:
                lines.append(f"  Rationale: {bullet.rationale}")
            for evidence_line in bullet.evidence_lines:
                lines.append(
                    f"  {evidence_line.label}: {_render_citations(evidence_line.citations)}"
                )
    return "\n".join(lines)


def _evidence_pool(entry: LedgerEntry):
    return [
        *entry.supporting_evidence,
        *entry.governing_evidence,
        *entry.contradicting_evidence,
    ]


def _select_citations(
    entry: LedgerEntry,
    *,
    role_levels: Optional[Sequence[SourceRoleLevel]] = None,
    source_kinds: Optional[Sequence[SourceKind]] = None,
    require_direct: bool = False,
    limit: int = 3,
    strict_filters: bool = False,
) -> List[Citation]:
    matches = list(_evidence_pool(entry))
    if role_levels is not None:
        allowed_roles = set(role_levels)
        filtered = [item for item in matches if item.source_role_level in allowed_roles]
        if filtered:
            matches = filtered
        elif strict_filters and matches:
            return []
    if source_kinds is not None:
        allowed_kinds = set(source_kinds)
        filtered = [item for item in matches if item.source_kind in allowed_kinds]
        if filtered:
            matches = filtered
        elif strict_filters and matches:
            return []
    if require_direct:
        filtered = [
            item for item in matches if item.support_directness == SupportDirectness.DIRECT
        ]
        if filtered:
            matches = filtered
        elif strict_filters and matches:
            return []
    matches.sort(
        key=lambda item: (
            _role_weight(item.source_role_level),
            1 if item.support_directness == SupportDirectness.DIRECT else 0,
            _citation_weight(item.citation_quality),
            -item.source_kind_rank,
            item.on_point_score,
        ),
        reverse=True,
    )
    citations = _dedupe_citations(item.citation for item in matches)
    if citations:
        return citations[:limit]
    if strict_filters:
        # Strict mode means "no qualifying evidence, no topology evidence line", even if
        # the ledger still carries broad entry-level citations as a last-resort fallback.
        return []
    fallback_citations = list(_dedupe_citations(entry.citations))
    if role_levels is not None:
        allowed_roles = set(role_levels)
        fallback_citations = [
            citation for citation in fallback_citations if citation.source_role_level in allowed_roles
        ]
    if source_kinds is not None:
        allowed_kinds = set(source_kinds)
        fallback_citations = [
            citation for citation in fallback_citations if citation.source_kind in allowed_kinds
        ]
    return fallback_citations[:limit]


def _governing_term_hits(
    query_intent: QueryIntent,
    documents: Sequence[SourceDocument],
) -> tuple[List[SourceDocument], List[str]]:
    governing_documents = [
        document
        for document in documents
        if document.entry.source_role_level == SourceRoleLevel.HIGH
        and document.entry.source_kind in {SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT}
        and document.entry.jurisdiction == "EU"
    ]
    lowered_terms = [term.lower() for term in query_intent.undefined_terms]
    hit_titles: List[str] = []
    for document in governing_documents:
        lowered_text = document.text.lower()
        if any(term in lowered_text for term in lowered_terms):
            hit_titles.append(document.entry.title)
    return governing_documents, sorted(set(hit_titles))


def _document_citations(documents: Sequence[SourceDocument], *, limit: Optional[int] = None) -> List[Citation]:
    citations: List[Citation] = []
    for document in documents:
        if document.chunks:
            citations.append(document.chunks[0].citation)
        else:
            citations.append(
                Citation(
                    source_id=document.entry.source_id,
                    document_title=document.entry.title,
                    source_role_level=document.entry.source_role_level,
                    source_kind=document.entry.source_kind,
                    jurisdiction=document.entry.jurisdiction,
                    citation_quality=CitationQuality.DOCUMENT_ONLY,
                    document_path=document.entry.local_path,
                    canonical_url=document.entry.canonical_url,
                    source_origin=document.entry.source_origin,
                    structure_poor=document.structure_poor,
                    anchor_audit_note=(
                        document.anchor_audit.audit_note if document.anchor_audit is not None else None
                    ),
                )
            )
    deduped = _dedupe_citations(citations)
    if limit is not None:
        return deduped[:limit]
    return deduped


def _generic_entry_bullet(entry: LedgerEntry, section: str) -> _AnswerBullet:
    if section == "Confirmed":
        wording_category = (
            "governing_confirmed"
            if entry.source_role_level == SourceRoleLevel.HIGH
            else "confirmed_non_governing"
        )
    else:
        wording_category = {
            "Interpretive": "interpretive_state_forwarded",
            "Open": "open_state_forwarded",
        }.get(section, "state_forwarded")
    return _AnswerBullet(
        bullet_id=entry.claim_id,
        section=section,
        text=entry.claim_text,
        rationale=entry.rationale,
        wording_category=wording_category,
        claim_ids=[entry.claim_id],
        claim_states=[entry.final_claim_state],
        evidence_lines=[_EvidenceLine(label="Evidence", citations=_dedupe_citations(entry.citations))],
    )


def _compose_certificate_topology_bullets(
    entries: Sequence[LedgerEntry],
    query_intent: QueryIntent,
    documents: Sequence[SourceDocument],
) -> List[_AnswerBullet]:
    entry_by_id = {entry.claim_id: entry for entry in entries}
    governing_documents, governing_term_hits = _governing_term_hits(query_intent, documents)
    bullets: List[_AnswerBullet] = []
    covered_claim_ids = set()

    term_status_text = (
        "Governing EU sources in the current corpus use derivative wording for the "
        "requested certificate terminology, so this term-status point needs manual review."
        if governing_term_hits
        else f'{TOPOLOGY_NOT_DEFINED_PREFIX} a wallet-relying-party "derived certificate" '
        "term for access or registration certificates."
    )
    term_status_rationale = (
        "Exact governing-source term hits were found in "
        + "; ".join(governing_term_hits)
        if governing_term_hits
        else "Corpus-wide governing term scan across "
        f"{len(governing_documents)} governing EU source(s) found no exact match for "
        + ", ".join(f'"{term}"' for term in query_intent.undefined_terms)
        + "."
    )
    bullets.append(
        _AnswerBullet(
            bullet_id="topology_undefined_term_status",
            section=TOPOLOGY_NOT_DEFINED_LABEL,
            text=term_status_text,
            rationale=term_status_rationale,
            wording_category="term_status_scan",
            evidence_lines=[
                _EvidenceLine(
                    label="Evidence",
                    citations=_document_citations(governing_documents),
                )
            ],
        )
    )

    access_entry = entry_by_id.get("topology_access_certificate_role")
    if access_entry is not None and access_entry.final_claim_state == ClaimState.CONFIRMED:
        bullets.append(
            _AnswerBullet(
                bullet_id=access_entry.claim_id,
                section="Confirmed",
                text=access_entry.claim_text,
                rationale=access_entry.rationale,
                wording_category="governing_confirmed",
                claim_ids=[access_entry.claim_id],
                claim_states=[access_entry.final_claim_state],
                evidence_lines=[
                    _EvidenceLine(
                        label="Evidence",
                        citations=_select_citations(
                            access_entry,
                            role_levels=[SourceRoleLevel.HIGH],
                            require_direct=True,
                            strict_filters=True,
                        ),
                    )
                ],
            )
        )
        covered_claim_ids.add(access_entry.claim_id)

    linkage_entry = entry_by_id.get("topology_registration_access_linkage")
    if linkage_entry is not None and linkage_entry.final_claim_state == ClaimState.CONFIRMED:
        bullets.append(
            _AnswerBullet(
                bullet_id=linkage_entry.claim_id,
                section="Confirmed",
                text=linkage_entry.claim_text,
                rationale=linkage_entry.rationale,
                wording_category="governing_confirmed",
                claim_ids=[linkage_entry.claim_id],
                claim_states=[linkage_entry.final_claim_state],
                evidence_lines=[
                    _EvidenceLine(
                        label="Evidence",
                        citations=_select_citations(
                            linkage_entry,
                            role_levels=[SourceRoleLevel.HIGH],
                            strict_filters=True,
                        ),
                    )
                ],
            )
        )
        covered_claim_ids.add(linkage_entry.claim_id)

    scope_claim_ids = [
        claim_id
        for claim_id in [
            "topology_registration_certificate_role",
            "topology_access_certificate_role",
            "topology_registration_access_linkage",
        ]
        if claim_id in entry_by_id
        and entry_by_id[claim_id].final_claim_state != ClaimState.OPEN
    ]
    full_scope_claim_ids = [
        "topology_registration_certificate_role",
        "topology_access_certificate_role",
        "topology_registration_access_linkage",
    ]
    if scope_claim_ids == full_scope_claim_ids:
        scope_citations: List[Citation] = []
        scope_states: List[ClaimState] = []
        for claim_id in scope_claim_ids:
            scope_entry = entry_by_id[claim_id]
            scope_states.append(scope_entry.final_claim_state)
            scope_citations.extend(
                    _select_citations(
                        scope_entry,
                        role_levels=[SourceRoleLevel.HIGH],
                        require_direct=True,
                        strict_filters=True,
                    )
                )
        bullets.append(
            _AnswerBullet(
                bullet_id="topology_governing_scope_interpretation",
                section="Interpretive",
                text=TOPOLOGY_SCOPING_SENTENCE,
                rationale=(
                    "This is the narrower conclusion the governing texts support directly; "
                    "they describe role, intended use, and certificate linkage, but they "
                    "do not expressly settle multiplicity."
                ),
                wording_category="interpretive_governing_boundary",
                claim_ids=scope_claim_ids,
                claim_states=scope_states,
                evidence_lines=[
                    _EvidenceLine(
                        label="Evidence",
                        citations=_dedupe_citations(scope_citations),
                    )
                ],
            )
        )
        for claim_id in scope_claim_ids:
            scope_entry = entry_by_id[claim_id]
            if scope_entry.final_claim_state == ClaimState.INTERPRETIVE:
                covered_claim_ids.add(claim_id)

    project_multiplicity_entry = entry_by_id.get("topology_project_artifact_multiplicity")
    project_scoping_entry = entry_by_id.get("topology_project_intended_use_scoping")
    approved_project_entries = [
        project_entry
        for project_entry in [project_multiplicity_entry, project_scoping_entry]
        if project_entry is not None and project_entry.final_claim_state != ClaimState.OPEN
    ]
    boundary_entries = [
        entry_by_id[claim_id]
        for claim_id in [
            "topology_registration_certificate_role",
            "topology_access_certificate_role",
            "topology_registration_access_linkage",
        ]
        if claim_id in entry_by_id
        and entry_by_id[claim_id].final_claim_state != ClaimState.OPEN
    ]
    if boundary_entries or project_multiplicity_entry or project_scoping_entry:
        boundary_citations: List[Citation] = []
        boundary_states: List[ClaimState] = []
        for boundary_entry in boundary_entries:
            boundary_states.append(boundary_entry.final_claim_state)
            boundary_citations.extend(
                    _select_citations(
                        boundary_entry,
                        role_levels=[SourceRoleLevel.HIGH],
                        require_direct=True,
                        strict_filters=True,
                    )
                )
        project_citations: List[Citation] = []
        supported_project_entries: List[LedgerEntry] = []
        supported_project_states: List[ClaimState] = []
        for project_entry in approved_project_entries:
            selected_citations = _select_citations(
                project_entry,
                role_levels=[SourceRoleLevel.MEDIUM],
                source_kinds=[SourceKind.PROJECT_ARTIFACT],
                require_direct=False,
                strict_filters=True,
            )
            if not selected_citations:
                continue
            supported_project_entries.append(project_entry)
            supported_project_states.append(project_entry.final_claim_state)
            project_citations.extend(selected_citations)
            covered_claim_ids.add(project_entry.claim_id)
        has_boundary_support = bool(boundary_entries and _dedupe_citations(boundary_citations))
        has_project_support = bool(
            supported_project_entries
            and _dedupe_citations(project_citations)
        )
        unresolved_text = TOPOLOGY_UNRESOLVED_NO_APPROVED_SUPPORT_SENTENCE
        unresolved_rationale = (
            "The broader topology conclusion is still not explicit governing law in the local corpus, and this run does not surface approved supporting evidence for multiplicity."
        )
        wording_category = "unresolved_no_approved_support"
        evidence_lines: List[_EvidenceLine] = []
        explicit_role_partitioning = False

        if has_boundary_support and has_project_support:
            unresolved_text = TOPOLOGY_UNRESOLVED_WITH_PROJECT_SUPPORT_SENTENCE
            unresolved_rationale = (
                "The product can separate the governing role statements from the broader "
                "multiplicity interpretation, but the broader topology conclusion is still "
                "not explicit governing law in the local corpus."
            )
            wording_category = "unresolved_partitioned_support"
            evidence_lines = [
                _EvidenceLine(
                    label="Evidence (governing boundary)",
                    citations=_dedupe_citations(boundary_citations),
                ),
                _EvidenceLine(
                    label="Evidence (medium-rank project support)",
                    citations=_dedupe_citations(project_citations),
                ),
            ]
            explicit_role_partitioning = True
        elif has_boundary_support:
            unresolved_text = TOPOLOGY_UNRESOLVED_GOVERNING_ONLY_SENTENCE
            unresolved_rationale = (
                "The product can preserve the governing boundary statements, but the broader "
                "multiplicity interpretation remains unresolved because no approved medium-rank "
                "project support survives this run."
            )
            wording_category = "unresolved_governing_boundary_only"
            evidence_lines = [
                _EvidenceLine(
                    label="Evidence (governing boundary)",
                    citations=_dedupe_citations(boundary_citations),
                )
            ]
        elif has_project_support:
            unresolved_text = TOPOLOGY_UNRESOLVED_PROJECT_ONLY_SENTENCE
            unresolved_rationale = (
                "The run surfaces only non-governing project-artifact support for multiplicity, "
                "so the broader topology conclusion remains unresolved and cannot be framed as "
                "governing EU law."
            )
            wording_category = "unresolved_medium_rank_only"
            evidence_lines = [
                _EvidenceLine(
                    label="Evidence (medium-rank project support)",
                    citations=_dedupe_citations(project_citations),
                )
            ]
        else:
            evidence_lines = []

        bullets.append(
            _AnswerBullet(
                bullet_id="topology_unresolved_multiplicity",
                section="Open",
                text=unresolved_text,
                rationale=unresolved_rationale,
                wording_category=wording_category,
                claim_ids=[
                    *(entry.claim_id for entry in boundary_entries),
                    *(
                        project_entry.claim_id
                        for project_entry in supported_project_entries
                    ),
                ],
                claim_states=[*boundary_states, *supported_project_states],
                evidence_lines=evidence_lines,
                explicit_role_partitioning=explicit_role_partitioning,
            )
        )

    for entry in entries:
        if entry.claim_id in covered_claim_ids:
            continue
        if entry.final_claim_state == ClaimState.CONFIRMED:
            bullets.append(_generic_entry_bullet(entry, "Confirmed"))
        elif entry.final_claim_state == ClaimState.INTERPRETIVE:
            bullets.append(_generic_entry_bullet(entry, "Interpretive"))
        elif entry.final_claim_state == ClaimState.OPEN:
            bullets.append(_generic_entry_bullet(entry, "Open"))

    return bullets


def _compose_generic_bullets(entries: Sequence[LedgerEntry]) -> List[_AnswerBullet]:
    bullets: List[_AnswerBullet] = []
    for state, section in [
        (ClaimState.CONFIRMED, "Confirmed"),
        (ClaimState.INTERPRETIVE, "Interpretive"),
        (ClaimState.OPEN, "Open"),
    ]:
        for entry in entries:
            if entry.final_claim_state == state:
                bullets.append(_generic_entry_bullet(entry, section))
    return bullets


def _classify_locator(citation: Citation) -> tuple[str, str, str, Optional[str]]:
    if citation.anchor_label:
        anchor_path = citation.anchor_label.strip()
        segments = [segment.strip() for segment in anchor_path.split(">") if segment.strip()]
        provision_segments = [
            segment
            for segment in segments
            if segment.lower().startswith(("article", "section", "clause", "annex", "chapter"))
        ]
        precision = "provision_level" if provision_segments else "section_level"
        return (
            "heading_path",
            anchor_path,
            precision,
            "Exact line-level pinpoint is not available; this run exposes the nearest heading anchor.",
        )
    if citation.document_path is not None:
        return (
            "document_path",
            str(citation.document_path),
            "approximate",
            "Only document-level traceability is available for this citation; broader manual navigation may still be required.",
        )
    if citation.canonical_url:
        return (
            "canonical_url",
            citation.canonical_url,
            "approximate",
            "Only document-level traceability is available for this citation; broader manual navigation may still be required.",
        )
    return (
        "document_title",
        citation.document_title,
        "approximate",
        "Only document-title traceability is available for this citation.",
    )


def _build_pinpoint_evidence_report(
    question: str,
    intent_type: str,
    bullets: Sequence[_AnswerBullet],
) -> PinpointEvidenceReport:
    records: List[PinpointEvidenceRecord] = []
    missing_citation_claim_ids: List[str] = []

    for bullet in bullets:
        bullet_citations = _dedupe_citations(
            citation
            for evidence_line in bullet.evidence_lines
            for citation in evidence_line.citations
        )
        if not bullet_citations:
            missing_citation_claim_ids.append(bullet.bullet_id)
            continue
        for citation in bullet_citations:
            locator_type, locator_value, locator_precision, limitation_note = _classify_locator(
                citation
            )
            if not locator_value:
                missing_citation_claim_ids.append(bullet.bullet_id)
                continue
            records.append(
                PinpointEvidenceRecord(
                    answer_claim_id=bullet.bullet_id,
                    answer_section=bullet.section,
                    answer_claim_text=bullet.text,
                    source_id=citation.source_id,
                    source_role_level=citation.source_role_level,
                    citation_quality=citation.citation_quality,
                    locator_type=locator_type,
                    locator_value=locator_value,
                    locator_precision=locator_precision,
                    document_path=citation.document_path,
                    canonical_url=citation.canonical_url,
                    limitation_note=limitation_note,
                )
            )

    return PinpointEvidenceReport(
        question=question,
        intent_type=intent_type,
        records=records,
        all_cited_evidence_mapped=not missing_citation_claim_ids,
        missing_citation_claim_ids=sorted(set(missing_citation_claim_ids)),
    )


def _build_answer_alignment_report(
    question: str,
    intent_type: str,
    bullets: Sequence[_AnswerBullet],
) -> AnswerAlignmentReport:
    records: List[AnswerAlignmentRecord] = []
    blocking_violations: List[str] = []

    for bullet in bullets:
        cited_citations = _dedupe_citations(
            citation
            for evidence_line in bullet.evidence_lines
            for citation in evidence_line.citations
        )
        cited_roles = [citation.source_role_level for citation in cited_citations]
        notes: List[str] = []
        status = "pass"

        if bullet.wording_category == "governing_confirmed":
            if bullet.section != "Confirmed":
                notes.append("Governing-confirmed wording is not placed in the Confirmed section.")
            if bullet.claim_states and any(
                claim_state != ClaimState.CONFIRMED for claim_state in bullet.claim_states
            ):
                notes.append("Confirmed wording is attached to a non-confirmed claim-state.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Confirmed governing wording cites non-governing evidence.")
        elif bullet.wording_category == "confirmed_non_governing":
            if bullet.section != "Confirmed":
                notes.append("Confirmed non-governing wording is not placed in the Confirmed section.")
            if bullet.claim_states and any(
                claim_state != ClaimState.CONFIRMED for claim_state in bullet.claim_states
            ):
                notes.append("Confirmed non-governing wording is attached to a non-confirmed claim-state.")
            if cited_roles and any(role == SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Confirmed non-governing wording mixes governing evidence without explicit partitioning.")
            if cited_roles and all(role == SourceRoleLevel.LOW for role in cited_roles):
                notes.append("Confirmed non-governing wording relies only on low-rank evidence.")
        elif bullet.wording_category == "term_status_scan":
            if bullet.section != TOPOLOGY_NOT_DEFINED_LABEL:
                notes.append("Undefined-term status was not surfaced in the dedicated term-status section.")
        elif bullet.wording_category == "interpretive_governing_boundary":
            if bullet.section != "Interpretive":
                notes.append("Interpretive governing-boundary wording is not in the Interpretive section.")
            if bullet.claim_states and any(
                claim_state == ClaimState.OPEN for claim_state in bullet.claim_states
            ):
                notes.append("Interpretive governing-boundary wording rests on open claim-state evidence.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Interpretive governing-boundary wording cites non-governing evidence.")
        elif bullet.wording_category == "unresolved_partitioned_support":
            if bullet.section != "Open":
                notes.append("Unresolved mixed-support wording is not in the Open section.")
            if not bullet.explicit_role_partitioning:
                notes.append("Mixed governing and medium-rank support is not partitioned explicitly.")
            if SourceRoleLevel.HIGH not in cited_roles:
                notes.append("Unresolved mixed-support wording is missing governing boundary evidence.")
            if SourceRoleLevel.MEDIUM not in cited_roles:
                notes.append("Unresolved mixed-support wording is missing medium-rank evidence.")
        elif bullet.wording_category == "unresolved_governing_boundary_only":
            if bullet.section != "Open":
                notes.append("Unresolved governing-boundary wording is not in the Open section.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Governing-boundary-only unresolved wording cites non-governing evidence.")
        elif bullet.wording_category == "unresolved_medium_rank_only":
            if bullet.section != "Open":
                notes.append("Unresolved medium-rank wording is not in the Open section.")
            if cited_roles and any(role != SourceRoleLevel.MEDIUM for role in cited_roles):
                notes.append("Medium-rank-only unresolved wording cites governing evidence.")
        elif bullet.wording_category == "unresolved_no_approved_support":
            if bullet.section != "Open":
                notes.append("Unresolved no-approved-support wording is not in the Open section.")
            if cited_roles:
                notes.append("No-approved-support wording should not cite supporting evidence.")
        elif bullet.wording_category == "interpretive_state_forwarded":
            if bullet.section != "Interpretive":
                notes.append("Interpretive claim-state is not surfaced in the Interpretive section.")
            if any(claim_state == ClaimState.CONFIRMED for claim_state in bullet.claim_states) and (
                SourceRoleLevel.MEDIUM in cited_roles and not bullet.explicit_role_partitioning
            ):
                notes.append("Mixed governing and medium-rank support needs explicit partitioning.")
        elif bullet.wording_category == "open_state_forwarded":
            if bullet.section != "Open":
                notes.append("Open claim-state is not surfaced in the Open section.")

        if notes:
            status = "fail"
            blocking_violations.extend(
                f"{bullet.bullet_id}: {note}" for note in notes
            )

        records.append(
            AnswerAlignmentRecord(
                answer_claim_id=bullet.bullet_id,
                answer_section=bullet.section,
                wording_category=bullet.wording_category,
                claim_ids=list(bullet.claim_ids),
                claim_states=list(bullet.claim_states),
                cited_source_ids=[citation.source_id for citation in cited_citations],
                cited_source_roles=cited_roles,
                evidence_partition_labels=[
                    evidence_line.label for evidence_line in bullet.evidence_lines
                ],
                alignment_status=status,
                notes=notes,
            )
        )

    return AnswerAlignmentReport(
        question=question,
        intent_type=intent_type,
        records=records,
        blocking_violations=blocking_violations,
    )


def _build_topology_facet_coverage_report(
    question: str,
    query_intent: QueryIntent,
    bullets: Sequence[_AnswerBullet],
) -> FacetCoverageReport:
    bullet_ids = {bullet.bullet_id for bullet in bullets}
    claim_ids = {
        claim_id
        for bullet in bullets
        for claim_id in bullet.claim_ids
    }

    def facet(facet_id: str, addressed: bool, evidence: List[str]) -> FacetCoverageFacet:
        return FacetCoverageFacet(
            facet_id=facet_id,
            addressed=addressed,
            evidence=evidence,
        )

    multiplicity_evidence: List[str] = []
    if "topology_unresolved_multiplicity" in bullet_ids:
        multiplicity_evidence.append("bullet_id:topology_unresolved_multiplicity")
    if "topology_project_artifact_multiplicity" in claim_ids:
        multiplicity_evidence.append("claim_id:topology_project_artifact_multiplicity")
    if "topology_project_intended_use_scoping" in claim_ids:
        multiplicity_evidence.append("claim_id:topology_project_intended_use_scoping")

    derived_term_evidence: List[str] = []
    if "topology_undefined_term_status" in bullet_ids:
        derived_term_evidence.append("bullet_id:topology_undefined_term_status")

    registration_evidence: List[str] = []
    if "topology_registration_certificate_role" in claim_ids:
        registration_evidence.append("claim_id:topology_registration_certificate_role")
    if "topology_governing_scope_interpretation" in bullet_ids:
        registration_evidence.append("bullet_id:topology_governing_scope_interpretation")

    access_evidence: List[str] = []
    if "topology_access_certificate_role" in claim_ids:
        access_evidence.append("claim_id:topology_access_certificate_role")
    if "topology_access_certificate_role" in bullet_ids:
        access_evidence.append("bullet_id:topology_access_certificate_role")
    if "topology_governing_scope_interpretation" in bullet_ids:
        access_evidence.append("bullet_id:topology_governing_scope_interpretation")

    unresolved_evidence: List[str] = []
    if "topology_governing_scope_interpretation" in bullet_ids:
        unresolved_evidence.append("bullet_id:topology_governing_scope_interpretation")
    if "topology_unresolved_multiplicity" in bullet_ids:
        unresolved_evidence.append("bullet_id:topology_unresolved_multiplicity")

    return FacetCoverageReport(
        question=question,
        intent_type=query_intent.intent_type,
        facets=[
            facet(
                "multiplicity_single_certificate",
                bool(multiplicity_evidence),
                multiplicity_evidence,
            ),
            facet(
                "derived_certificate_term_status",
                bool(derived_term_evidence),
                derived_term_evidence,
            ),
            facet(
                "registration_certificate_role",
                bool(registration_evidence),
                registration_evidence,
            ),
            facet(
                "access_certificate_role",
                bool(access_evidence),
                access_evidence,
            ),
            facet(
                "unresolved_or_interpretive_status",
                bool(unresolved_evidence),
                unresolved_evidence,
            ),
        ],
    )


def compose_answer_bundle(
    question: str,
    entries: List[LedgerEntry],
    *,
    query_intent: Optional[QueryIntent] = None,
    clarification_note: Optional[str] = None,
    documents: Sequence[SourceDocument] = (),
) -> ComposedAnswerBundle:
    if not entries:
        facet_coverage_report = (
            _build_topology_facet_coverage_report(question, query_intent, [])
            if query_intent is not None
            and query_intent.intent_type == "certificate_topology_analysis"
            else None
        )
        rendered_answer = (
            f"First-pass note: {clarification_note}\n"
            "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
            if clarification_note
            else "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
        )
        return ComposedAnswerBundle(
            rendered_answer=rendered_answer,
            facet_coverage_report=facet_coverage_report,
            pinpoint_evidence_report=PinpointEvidenceReport(
                question=question,
                intent_type=query_intent.intent_type if query_intent is not None else "unknown",
                records=[],
            ),
            answer_alignment_report=AnswerAlignmentReport(
                question=question,
                intent_type=query_intent.intent_type if query_intent is not None else "unknown",
                records=[],
            ),
        )

    if (
        query_intent is not None
        and query_intent.intent_type == "certificate_topology_analysis"
    ):
        summary = (
            "Source-bound answer: the reviewed sources support a more explicit topology answer "
            "than a flat certificate-role summary."
        )
        bullets = _compose_certificate_topology_bullets(entries, query_intent, documents)
        facet_coverage_report = _build_topology_facet_coverage_report(
            question,
            query_intent,
            bullets,
        )
    else:
        summary = "Source-bound answer:"
        if len(entries) >= 2:
            summary += " the reviewed sources support a differentiated answer rather than a flat yes/no."
        bullets = _compose_generic_bullets(entries)
        facet_coverage_report = None

    rendered_answer = _render_bullets(summary, bullets, clarification_note)
    pinpoint_evidence_report = _build_pinpoint_evidence_report(
        question,
        query_intent.intent_type if query_intent is not None else "unknown",
        bullets,
    )
    answer_alignment_report = _build_answer_alignment_report(
        question,
        query_intent.intent_type if query_intent is not None else "unknown",
        bullets,
    )
    return ComposedAnswerBundle(
        rendered_answer=rendered_answer,
        facet_coverage_report=facet_coverage_report,
        pinpoint_evidence_report=pinpoint_evidence_report,
        answer_alignment_report=answer_alignment_report,
    )


def compose_answer(
    question: str,
    entries: List[LedgerEntry],
    *,
    query_intent: Optional[QueryIntent] = None,
    clarification_note: Optional[str] = None,
    documents: Sequence[SourceDocument] = (),
) -> str:
    return compose_answer_bundle(
        question,
        entries,
        query_intent=query_intent,
        clarification_note=clarification_note,
        documents=documents,
    ).rendered_answer


def build_facet_coverage_report(
    question: str,
    query_intent: QueryIntent,
    *args,
    documents: Sequence[SourceDocument] = (),
) -> Optional[FacetCoverageReport]:
    if query_intent.intent_type != "certificate_topology_analysis":
        return None
    if len(args) == 1:
        entry_list = list(args[0])
    elif len(args) == 2 and isinstance(args[0], str):
        # Backward-compatibility path: the legacy rendered_answer argument is now ignored
        # because topology coverage is derived from structured bullets rather than answer text.
        entry_list = list(args[1])
    else:
        raise TypeError(
            "build_facet_coverage_report expects either "
            "(question, query_intent, entries) or "
            "(question, query_intent, rendered_answer, entries)."
        )

    bullets = _compose_certificate_topology_bullets(
        entry_list,
        query_intent,
        documents,
    )
    return _build_topology_facet_coverage_report(
        question,
        query_intent,
        bullets,
    )
