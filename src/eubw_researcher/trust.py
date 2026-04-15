from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, Sequence

from eubw_researcher.answering import supports_relation_hints
from eubw_researcher.models import (
    AnswerAlignmentReport,
    BlindValidationReport,
    CitationQuality,
    ClaimState,
    FacetCoverageReport,
    PinpointEvidenceReport,
    QueryIntent,
    SpawnedValidatorResult,
)


class LedgerEvidenceLike(Protocol):
    anchor_audit_note: Optional[str]


class CitationLike(Protocol):
    source_id: str
    source_role_level: object
    source_kind: object
    jurisdiction: Optional[str]
    citation_quality: object
    document_path: Optional[Path]
    canonical_url: Optional[str]
    document_status: object
    source_origin: object
    anchor_label: Optional[str]
    structure_poor: bool
    anchor_audit_note: Optional[str]
    document_title: str


class LedgerEntryLike(Protocol):
    claim_id: str
    final_claim_state: ClaimState
    citation_quality: CitationQuality
    governing_evidence: Sequence[LedgerEvidenceLike]
    citations: Sequence[CitationLike]


class RelationHintEvidencePartitionLike(Protocol):
    partition_label: str
    source_ids: Sequence[str]
    citations: Sequence[CitationLike]


class RelationHintRecordLike(Protocol):
    hint_id: str
    supporting_source_ids: Sequence[str]
    evidence_partitions: Sequence[RelationHintEvidencePartitionLike]
    rendered_in_answer: bool


class RelationHintReportLike(Protocol):
    intent_type: str
    records: Sequence[RelationHintRecordLike]


class TrustResultLike(Protocol):
    question: str
    query_intent: QueryIntent
    rendered_answer: str
    ledger_entries: Sequence[LedgerEntryLike]
    approved_entries: Sequence[LedgerEntryLike]
    relation_hint_report: Optional[RelationHintReportLike]
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


def _citation_fingerprint(citation: CitationLike) -> tuple[object, ...]:
    return (
        getattr(citation, "source_id", None),
        getattr(citation, "document_title", None),
        getattr(citation, "source_role_level", None),
        getattr(citation, "source_kind", None),
        getattr(citation, "jurisdiction", None),
        getattr(citation, "citation_quality", None),
        str(getattr(citation, "document_path", None))
        if getattr(citation, "document_path", None) is not None
        else None,
        getattr(citation, "canonical_url", None),
        getattr(citation, "document_status", None),
        getattr(citation, "source_origin", None),
        getattr(citation, "anchor_label", None),
        getattr(citation, "structure_poor", None),
        getattr(citation, "anchor_audit_note", None),
    )


def relation_hint_integrity_status(
    result: TrustResultLike,
) -> tuple[bool, str, list[str]]:
    if not supports_relation_hints(result.query_intent.intent_type):
        return True, "Relation hints are not applicable for this intent.", []

    report = getattr(result, "relation_hint_report", None)
    if report is None:
        return (
            False,
            "relation_hints.json should be present for this supported intent, but no relation-hint report was built.",
            ["relation_hint_integrity"],
        )

    if report.intent_type != result.query_intent.intent_type:
        return (
            False,
            "Relation-hint report intent does not match the result intent.",
            ["relation_hint_integrity"],
        )

    approved_source_ids = {
        citation.source_id
        for entry in result.approved_entries
        for citation in entry.citations
    }
    approved_citation_fingerprints = {
        _citation_fingerprint(citation)
        for entry in result.approved_entries
        for citation in entry.citations
    }
    alignment_ids = {
        record.answer_claim_id
        for record in (result.answer_alignment_report.records if result.answer_alignment_report else [])
    }
    pinpoint_ids = {
        record.answer_claim_id
        for record in (result.pinpoint_evidence_report.records if result.pinpoint_evidence_report else [])
    }

    missing_facets: list[str] = []
    issues: list[str] = []
    for record in report.records:
        missing_source_ids = sorted(
            set(record.supporting_source_ids) - approved_source_ids
        )
        if missing_source_ids:
            missing_facets.append("relation_hint_integrity")
            issues.append(
                f"{record.hint_id} references source ids outside approved_ledger.json: {', '.join(missing_source_ids)}."
            )
        for partition in record.evidence_partitions:
            for citation in partition.citations:
                if _citation_fingerprint(citation) not in approved_citation_fingerprints:
                    missing_facets.append("relation_hint_integrity")
                    issues.append(
                        f"{record.hint_id} contains citation drift in partition `{partition.partition_label}`."
                    )
                    break
        if record.rendered_in_answer:
            answer_claim_id = f"relation_hint:{record.hint_id}"
            if answer_claim_id not in alignment_ids or answer_claim_id not in pinpoint_ids:
                missing_facets.append(f"rendered_relation_hint_contract:{record.hint_id}")
                issues.append(
                    f"{record.hint_id} is marked rendered_in_answer but is not fully mirrored in answer_alignment.json and pinpoint_evidence.json."
                )

    deduped_missing = list(dict.fromkeys(missing_facets))
    if deduped_missing:
        return False, " ".join(dict.fromkeys(issues)), deduped_missing
    return (
        True,
        f"{len(report.records)} relation-hint record(s) stayed bound to approved-ledger citations and rendered-contract coverage.",
        [],
    )


def build_blind_validation_report(result: TrustResultLike) -> BlindValidationReport:
    artifacts_used = [
        "final_answer.txt",
        "approved_ledger.json",
        "pinpoint_evidence.json",
        "answer_alignment.json",
    ]
    if supports_relation_hints(result.query_intent.intent_type):
        artifacts_used.append("relation_hints.json")
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
    relation_hints_ok, _relation_hints_message, relation_hint_missing_facets = (
        relation_hint_integrity_status(result)
    )
    if not relation_hints_ok:
        missing_facets.extend(relation_hint_missing_facets)
    if result.query_intent.intent_type == "certificate_topology_analysis":
        if result.facet_coverage_report is None or not result.facet_coverage_report.all_addressed():
            missing_facets.append("topology_facet_coverage")
        missing_facets.extend(_topology_structure_missing_facets(result))
    missing_facets = list(dict.fromkeys(missing_facets))

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
        structural_passed=passed,
        product_output_self_sufficient=passed,
        passed=passed,
        summary=summary,
        missing_facets=missing_facets,
    )


def merge_spawned_validator_result(
    structural_report: BlindValidationReport,
    spawned_validator: SpawnedValidatorResult,
    *,
    validation_mode: str = "structural_plus_spawned_validator_closeout",
) -> BlindValidationReport:
    # Older structural reports may predate the explicit structural_passed field,
    # so preserve backwards compatibility by falling back to the original
    # top-level passed flag when needed.
    structural_passed = structural_report.structural_passed or structural_report.passed
    spawned_validator_passed = (
        spawned_validator.passed
        and not spawned_validator.context_inherited
        and spawned_validator.raw_document_dependency != "central_reconstruction"
        and spawned_validator.product_output_self_sufficient
    )
    combined_passed = structural_passed and spawned_validator_passed
    raw_document_dependency = (
        "central_reconstruction"
        if not structural_passed
        else spawned_validator.raw_document_dependency
    )
    artifacts_used = list(
        dict.fromkeys(structural_report.artifacts_used + spawned_validator.artifacts_used)
    )
    failure_reasons: list[str] = []
    if not structural_passed:
        failure_reasons.append("the structural blind-validation precondition did not pass")
    if spawned_validator.context_inherited:
        failure_reasons.append("the spawned validator reported inherited context")
    if spawned_validator.raw_document_dependency == "central_reconstruction":
        failure_reasons.append("the spawned validator required central raw-document reconstruction")
    if not spawned_validator.product_output_self_sufficient:
        failure_reasons.append("the spawned validator did not judge the product output self-sufficient")
    if not spawned_validator.passed:
        failure_reasons.append("the spawned validator returned a failing result")
    if spawned_validator.error:
        failure_reasons.append(spawned_validator.error)
    summary = (
        "Product-output-first blind validation passes: the structural contract and the spawned no-context "
        "validator both support reuse from the generated bundle."
        if combined_passed
        else "Product-output-first blind validation fails: "
        + "; ".join(dict.fromkeys(failure_reasons))
        + "."
    )
    return BlindValidationReport(
        question=structural_report.question,
        intent_type=structural_report.intent_type,
        validation_mode=validation_mode,
        artifacts_used=artifacts_used,
        raw_document_reads=spawned_validator.raw_document_reads,
        raw_document_dependency=raw_document_dependency,
        structural_passed=structural_passed,
        product_output_self_sufficient=combined_passed,
        passed=combined_passed,
        summary=summary,
        missing_facets=list(structural_report.missing_facets),
        spawned_validator=spawned_validator,
    )
