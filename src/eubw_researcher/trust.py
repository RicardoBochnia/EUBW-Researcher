from __future__ import annotations

from typing import Optional, Protocol, Sequence

from eubw_researcher.models import (
    AnswerAlignmentReport,
    BlindValidationReport,
    CitationQuality,
    ClaimState,
    FacetCoverageReport,
    PinpointEvidenceReport,
    QueryIntent,
)


class LedgerEvidenceLike(Protocol):
    anchor_audit_note: Optional[str]


class LedgerEntryLike(Protocol):
    claim_id: str
    final_claim_state: ClaimState
    citation_quality: CitationQuality
    governing_evidence: Sequence[LedgerEvidenceLike]


class TrustResultLike(Protocol):
    question: str
    query_intent: QueryIntent
    rendered_answer: str
    ledger_entries: Sequence[LedgerEntryLike]
    facet_coverage_report: Optional[FacetCoverageReport]
    pinpoint_evidence_report: Optional[PinpointEvidenceReport]
    answer_alignment_report: Optional[AnswerAlignmentReport]


def _topology_structure_missing_facets(result: TrustResultLike) -> list[str]:
    report = result.answer_alignment_report
    if report is None:
        return [
            "missing_answer_structure:term_status_scan",
            "missing_answer_structure:Interpretive",
            "missing_answer_structure:Open",
        ]

    sections = {record.answer_section for record in report.records}
    wording_categories = {record.wording_category for record in report.records}
    missing: list[str] = []

    if "term_status_scan" not in wording_categories:
        missing.append("missing_answer_structure:term_status_scan")
    if "Interpretive" not in sections:
        missing.append("missing_answer_structure:Interpretive")
    if "Open" not in sections:
        missing.append("missing_answer_structure:Open")
    return missing


def _audit_confirmable_document_only_claim_ids(result: TrustResultLike) -> set[str]:
    claim_ids: set[str] = set()
    for entry in result.ledger_entries:
        if entry.final_claim_state != ClaimState.CONFIRMED:
            continue
        if entry.citation_quality != CitationQuality.DOCUMENT_ONLY:
            continue
        if any(
            evidence.anchor_audit_note
            and "technical extraction failure" in evidence.anchor_audit_note.lower()
            for evidence in entry.governing_evidence
        ):
            claim_ids.add(entry.claim_id)
    return claim_ids


def _allowed_approximate_answer_claim_ids(
    result: TrustResultLike,
    approximate_only_claim_ids: set[str],
) -> set[str]:
    audit_confirmable_claim_ids = _audit_confirmable_document_only_claim_ids(result)
    allowed_answer_claim_ids = approximate_only_claim_ids & audit_confirmable_claim_ids

    report = result.answer_alignment_report
    if report is None:
        return allowed_answer_claim_ids

    for record in report.records:
        if record.answer_claim_id not in approximate_only_claim_ids:
            continue
        if record.claim_ids and set(record.claim_ids).issubset(audit_confirmable_claim_ids):
            allowed_answer_claim_ids.add(record.answer_claim_id)
    return allowed_answer_claim_ids


def pinpoint_traceability_status(result: TrustResultLike) -> tuple[bool, str]:
    report = result.pinpoint_evidence_report
    if report is None:
        return False, "pinpoint_evidence.json was not produced."
    if not report.all_cited_evidence_mapped:
        return (
            False,
            "Some answer claims are missing pinpoint mapping: "
            + ", ".join(report.missing_citation_claim_ids),
        )
    if not report.records:
        return False, "No pinpoint evidence records were produced."
    precise_claim_ids = {
        record.answer_claim_id
        for record in report.records
        if record.locator_precision != "approximate"
    }
    all_claim_ids = {record.answer_claim_id for record in report.records}
    approximate_only_claim_ids = all_claim_ids - precise_claim_ids
    allowed_approximate_claim_ids = _allowed_approximate_answer_claim_ids(
        result,
        approximate_only_claim_ids,
    )
    blocking_approximate_claim_ids = sorted(
        approximate_only_claim_ids - allowed_approximate_claim_ids
    )
    if blocking_approximate_claim_ids:
        return (
            False,
            "Some answer claims still have only approximate document-level locators: "
            + ", ".join(blocking_approximate_claim_ids),
        )
    return (
        True,
        f"{len(report.records)} pinpoint evidence record(s) map answer claims to reviewer-usable locators.",
    )


def answer_alignment_status(result: TrustResultLike) -> tuple[bool, str]:
    report = result.answer_alignment_report
    if report is None:
        return False, "answer_alignment.json was not produced."
    if report.has_blocking_violations():
        return (
            False,
            "Blocking alignment violations were recorded: "
            + "; ".join(report.blocking_violations),
        )
    return (
        True,
        f"{len(report.records)} answer-alignment record(s) passed without blocking violations.",
    )


def build_blind_validation_report(result: TrustResultLike) -> BlindValidationReport:
    artifacts_used = [
        "final_answer.txt",
        "approved_ledger.json",
        "pinpoint_evidence.json",
        "answer_alignment.json",
    ]
    if result.facet_coverage_report is not None:
        artifacts_used.append("facet_coverage.json")

    missing_facets: list[str] = []
    if not result.rendered_answer.strip():
        missing_facets.append("final_answer")
    pinpoint_ok, _ = pinpoint_traceability_status(result)
    if not pinpoint_ok:
        missing_facets.append("pinpoint_traceability")
    alignment_ok, _ = answer_alignment_status(result)
    if not alignment_ok:
        missing_facets.append("answer_evidence_alignment")
    if result.query_intent.intent_type == "certificate_topology_analysis":
        if result.facet_coverage_report is None or not result.facet_coverage_report.all_addressed():
            missing_facets.append("topology_facet_coverage")
        missing_facets.extend(_topology_structure_missing_facets(result))

    passed = not missing_facets
    raw_document_dependency = "none" if passed else "central_reconstruction"
    summary = (
        "Product-output-first blind validation passes: the generated answer and trust artifacts "
        "cover the central reasoning path without raw-document reconstruction."
        if passed
        else "Product-output-first blind validation fails: a validator would need raw-document reconstruction "
        "because central product facets are missing."
    )
    return BlindValidationReport(
        question=result.question,
        intent_type=result.query_intent.intent_type,
        validation_mode="structural_product_output_contract_check",
        artifacts_used=artifacts_used,
        raw_document_reads=[],
        raw_document_dependency=raw_document_dependency,
        product_output_self_sufficient=passed,
        passed=passed,
        summary=summary,
        missing_facets=missing_facets,
    )
