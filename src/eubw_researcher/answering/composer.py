from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from eubw_researcher.models import (
    ClaimState,
    FacetCoverageFacet,
    FacetCoverageReport,
    LedgerEntry,
    QueryIntent,
    SourceDocument,
    SourceKind,
    SourceRoleLevel,
)

TOPOLOGY_FACET_IDS = [
    "multiplicity_single_certificate",
    "derived_certificate_term_status",
    "registration_certificate_role",
    "access_certificate_role",
    "unresolved_or_interpretive_status",
]
TOPOLOGY_NOT_DEFINED_LABEL = "Not explicitly defined:"
TOPOLOGY_NOT_DEFINED_PREFIX = "No governing EU source in the current corpus explicitly defines"
TOPOLOGY_SCOPING_SENTENCE = (
    "The governing EU texts point toward intended-use / service scoping rather than a "
    "single undifferentiated organisation-level certificate, but they do not explicitly "
    "say that a wallet-relying party is limited to exactly one certificate or entitled "
    "to multiple certificates."
)
TOPOLOGY_UNRESOLVED_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law; it remains interpretive or medium-rank supported."
)


def _render_citations(entry: LedgerEntry) -> str:
    citations = entry.governing_evidence or entry.supporting_evidence or entry.contradicting_evidence
    if not citations:
        return "no admissible citation"
    return "; ".join(evidence.citation.render() for evidence in citations)


def _render_citations_from_entries(entries: Iterable[Optional[LedgerEntry]]) -> str:
    rendered: List[str] = []
    seen = set()
    for entry in entries:
        if entry is None:
            continue
        citation = _render_citations(entry)
        if citation == "no admissible citation" or citation in seen:
            continue
        seen.add(citation)
        rendered.append(citation)
    return "; ".join(rendered) if rendered else "no admissible citation"


def _section(title: str, entries: List[LedgerEntry]) -> List[str]:
    if not entries:
        return []
    lines = [title + ":"]
    for entry in entries:
        lines.append(f"- {entry.claim_text}")
        lines.append(f"  Rationale: {entry.rationale}")
        lines.append(f"  Evidence: {_render_citations(entry)}")
    return lines


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


def _compose_certificate_topology_answer(
    entries: List[LedgerEntry],
    query_intent: QueryIntent,
    clarification_note: Optional[str],
    documents: Sequence[SourceDocument],
) -> str:
    if not entries:
        if clarification_note:
            return (
                f"First-pass note: {clarification_note}\n"
                "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
            )
        return "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."

    entry_by_id = {entry.claim_id: entry for entry in entries}
    governing_documents, governing_term_hits = _governing_term_hits(query_intent, documents)
    summary = (
        "Source-bound answer: the reviewed sources support a more explicit topology answer "
        "than a flat certificate-role summary."
    )
    lines: List[str] = [summary]
    if clarification_note:
        lines.append(f"First-pass note: {clarification_note}")

    lines.append(TOPOLOGY_NOT_DEFINED_LABEL)
    if governing_term_hits:
        lines.append(
            "- Governing EU sources in the current corpus use derivative wording for the "
            "requested certificate terminology, so this term-status point needs manual review."
        )
        lines.append(
            "  Evidence: exact governing-source term hits were found in "
            + "; ".join(governing_term_hits)
        )
    else:
        searched_terms = ", ".join(f'"{term}"' for term in query_intent.undefined_terms)
        lines.append(
            f"- {TOPOLOGY_NOT_DEFINED_PREFIX} a wallet-relying-party "
            '\"derived certificate\" term for access or registration certificates.'
        )
        lines.append(
            "  Evidence: searched "
            f"{len(governing_documents)} governing EU source(s) in the local corpus for "
            f"{searched_terms} and found no exact match."
        )

    confirmed = [entry for entry in entries if entry.final_claim_state == ClaimState.CONFIRMED]
    lines.extend(_section("Confirmed", confirmed))

    interpretive = [entry for entry in entries if entry.final_claim_state == ClaimState.INTERPRETIVE]
    interpretive_lines: List[str] = []
    governing_scope_evidence = _render_citations_from_entries(
        [
            entry_by_id.get("topology_registration_certificate_role"),
            entry_by_id.get("topology_access_certificate_role"),
            entry_by_id.get("topology_registration_access_linkage"),
        ]
    )
    if governing_scope_evidence != "no admissible citation":
        interpretive_lines.extend(
            [
                "Interpretive:",
                f"- {TOPOLOGY_SCOPING_SENTENCE}",
                "  Rationale: This is the narrower conclusion the governing texts support "
                "directly; they describe role, intended use, and certificate linkage, but "
                "they do not expressly settle multiplicity.",
                f"  Evidence: {governing_scope_evidence}",
            ]
        )
    if interpretive:
        if not interpretive_lines:
            interpretive_lines.append("Interpretive:")
        for entry in interpretive:
            interpretive_lines.append(f"- {entry.claim_text}")
            interpretive_lines.append(f"  Rationale: {entry.rationale}")
            interpretive_lines.append(f"  Evidence: {_render_citations(entry)}")
    lines.extend(interpretive_lines)

    open_entries = [entry for entry in entries if entry.final_claim_state == ClaimState.OPEN]
    unresolved_evidence = _render_citations_from_entries(
        [
            entry_by_id.get("topology_project_artifact_multiplicity"),
            entry_by_id.get("topology_project_intended_use_scoping"),
            entry_by_id.get("topology_registration_certificate_role"),
            entry_by_id.get("topology_access_certificate_role"),
        ]
    )
    lines.extend(
        [
            "Open:",
            f"- {TOPOLOGY_UNRESOLVED_SENTENCE}",
            "  Rationale: The product can separate the governing role statements from the "
            "broader multiplicity interpretation, but the broader topology conclusion is "
            "still not explicit governing law in the local corpus.",
            f"  Evidence: {unresolved_evidence}",
        ]
    )
    for entry in open_entries:
        lines.append(f"- {entry.claim_text}")
        lines.append(f"  Rationale: {entry.rationale}")
        lines.append(f"  Evidence: {_render_citations(entry)}")

    return "\n".join(lines)


def compose_answer(
    question: str,
    entries: List[LedgerEntry],
    *,
    query_intent: Optional[QueryIntent] = None,
    clarification_note: Optional[str] = None,
    documents: Sequence[SourceDocument] = (),
) -> str:
    if (
        query_intent is not None
        and query_intent.answer_pattern == "certificate_topology"
    ):
        return _compose_certificate_topology_answer(
            entries,
            query_intent,
            clarification_note,
            documents,
        )

    if not entries:
        if clarification_note:
            return (
                f"First-pass note: {clarification_note}\n"
                "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
            )
        return "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."

    summary = "Source-bound answer:"
    if len(entries) >= 2:
        summary += " the reviewed sources support a differentiated answer rather than a flat yes/no."

    confirmed = [entry for entry in entries if entry.final_claim_state == ClaimState.CONFIRMED]
    interpretive = [
        entry for entry in entries if entry.final_claim_state == ClaimState.INTERPRETIVE
    ]
    open_entries = [entry for entry in entries if entry.final_claim_state == ClaimState.OPEN]

    lines: List[str] = [summary]
    if clarification_note:
        lines.append(f"First-pass note: {clarification_note}")
    lines.extend(_section("Confirmed", confirmed))
    lines.extend(_section("Interpretive", interpretive))
    lines.extend(_section("Open", open_entries))

    return "\n".join(lines)


def build_facet_coverage_report(
    question: str,
    query_intent: QueryIntent,
    rendered_answer: str,
    entries: Sequence[LedgerEntry],
) -> Optional[FacetCoverageReport]:
    if query_intent.intent_type != "certificate_topology_analysis":
        return None

    entry_ids = {entry.claim_id for entry in entries}
    lowered_answer = rendered_answer.lower()

    def facet(facet_id: str, addressed: bool, evidence: List[str]) -> FacetCoverageFacet:
        return FacetCoverageFacet(
            facet_id=facet_id,
            addressed=addressed,
            evidence=evidence,
        )

    multiplicity_evidence: List[str] = []
    if "topology_project_artifact_multiplicity" in entry_ids:
        multiplicity_evidence.append("claim_id:topology_project_artifact_multiplicity")
    if "topology_project_intended_use_scoping" in entry_ids:
        multiplicity_evidence.append("claim_id:topology_project_intended_use_scoping")
    if "single undifferentiated organisation-level certificate" in lowered_answer:
        multiplicity_evidence.append("answer:organisation-level-scope")

    derived_term_evidence: List[str] = []
    if TOPOLOGY_NOT_DEFINED_LABEL.lower() in lowered_answer:
        derived_term_evidence.append("answer:not-explicitly-defined-section")
    if "derived certificate" in lowered_answer:
        derived_term_evidence.append("answer:derived-certificate")

    registration_evidence: List[str] = []
    if "topology_registration_certificate_role" in entry_ids:
        registration_evidence.append("claim_id:topology_registration_certificate_role")

    access_evidence: List[str] = []
    if "topology_access_certificate_role" in entry_ids:
        access_evidence.append("claim_id:topology_access_certificate_role")

    unresolved_evidence: List[str] = []
    if "interpretive:" in lowered_answer:
        unresolved_evidence.append("answer:interpretive-section")
    if "open:" in lowered_answer:
        unresolved_evidence.append("answer:open-section")
    if TOPOLOGY_UNRESOLVED_SENTENCE.lower() in lowered_answer:
        unresolved_evidence.append("answer:topology-unresolved")

    facets = [
        facet(
            "multiplicity_single_certificate",
            bool(multiplicity_evidence),
            multiplicity_evidence,
        ),
        facet(
            "derived_certificate_term_status",
            "answer:not-explicitly-defined-section" in derived_term_evidence
            and "answer:derived-certificate" in derived_term_evidence,
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
    ]
    return FacetCoverageReport(
        question=question,
        intent_type=query_intent.intent_type,
        facets=facets,
    )
