from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from eubw_researcher.answering import TOPOLOGY_FACET_IDS
from eubw_researcher.models import (
    ApprovedFetchedSourceEvidence,
    ClaimState,
    ManualReviewArtifact,
    ManualReviewCheck,
    ManualReviewReport,
)


def _topology_facet_status(result, facet_id: str) -> tuple[bool, str]:
    if result.facet_coverage_report is None:
        return False, "facet_coverage.json was not produced for the topology intent."
    facet = result.facet_coverage_report.by_id().get(facet_id)
    if facet is None:
        return False, f"Required topology facet `{facet_id}` is missing from facet_coverage.json."
    evidence = ", ".join(facet.evidence) if facet.evidence else "No structural evidence recorded."
    return facet.addressed, evidence


def build_manual_review_artifact(result, scenario_id: Optional[str] = None) -> ManualReviewArtifact:
    checks: List[ManualReviewCheck] = []

    blocked_visible = "Blocked:" in result.rendered_answer
    checks.append(
        ManualReviewCheck(
            check_id="blocked_claims_hidden",
            status="pass" if not blocked_visible else "fail",
            evidence=(
                "Blocked claims do not surface in the rendered answer."
                if not blocked_visible
                else "Blocked content is visible in final_answer.txt."
            ),
        )
    )

    approved_have_citations = all(entry.citations for entry in result.approved_entries)
    checks.append(
        ManualReviewCheck(
            check_id="approved_entries_have_citations",
            status="pass" if approved_have_citations else "fail",
            evidence=(
                f"{len(result.approved_entries)} approved entries each carry at least one citation."
                if approved_have_citations
                else "At least one approved entry lacks citation support."
            ),
        )
    )

    state_markers = {
        "Confirmed:": any(entry.final_claim_state == ClaimState.CONFIRMED for entry in result.approved_entries),
        "Interpretive:": any(entry.final_claim_state == ClaimState.INTERPRETIVE for entry in result.approved_entries),
        "Open:": any(entry.final_claim_state == ClaimState.OPEN for entry in result.approved_entries),
    }
    states_visible = all(
        (not expected) or marker in result.rendered_answer
        for marker, expected in state_markers.items()
    )
    checks.append(
        ManualReviewCheck(
            check_id="claim_state_visibility",
            status="pass" if states_visible else "fail",
            evidence="Visible state markers are aligned with the approved ledger entries.",
        )
    )

    weak_anchor_document_only = all(
        report.anchor_quality.value != "weak" or report.citation_quality.value == "document_only"
        for report in result.ingestion_report
    )
    checks.append(
        ManualReviewCheck(
            check_id="weak_anchors_degrade_to_document_only",
            status="pass" if weak_anchor_document_only else "fail",
            evidence="Weak-anchor sources in the ingestion report do not claim anchor-grounded citation quality.",
        )
    )

    web_allowed = all(record.allowed for record in result.web_fetch_records if record.record_type == "fetch")
    checks.append(
        ManualReviewCheck(
            check_id="allowlisted_web_only",
            status="pass" if web_allowed else "fail",
            evidence=(
                "All fetched web records are allowlisted."
                if web_allowed
                else "At least one fetched web record is not allowlisted."
            ),
        )
    )

    grouped_ok = bool(result.provisional_grouping) or not any(
        target.grouping_label for target in result.query_intent.claim_targets
    )
    checks.append(
        ManualReviewCheck(
            check_id="provisional_grouping_present_when_applicable",
            status="pass" if grouped_ok else "fail",
            evidence=(
                "Grouping artifact is present for grouping-capable intent."
                if grouped_ok
                else "Grouping-capable intent produced no provisional grouping."
            ),
        )
    )

    if result.query_intent.intent_type == "certificate_topology_analysis":
        facet_artifact_present = result.facet_coverage_report is not None
        checks.append(
            ManualReviewCheck(
                check_id="topology_facet_coverage_present",
                status="pass" if facet_artifact_present else "fail",
                evidence=(
                    "Topology facet coverage artifact is present."
                    if facet_artifact_present
                    else "Topology intent produced no facet_coverage.json artifact."
                ),
            )
        )
        for facet_id in TOPOLOGY_FACET_IDS:
            addressed, evidence = _topology_facet_status(result, facet_id)
            checks.append(
                ManualReviewCheck(
                    check_id=f"topology_{facet_id}",
                    status="pass" if addressed else "fail",
                    evidence=evidence,
                )
            )

    passed = sum(1 for check in checks if check.status == "pass")
    summary = f"Automated review prefill completed with {passed}/{len(checks)} checks passing."
    return ManualReviewArtifact(
        question=result.question,
        scenario_id=scenario_id,
        artifact_scope=result.query_intent.intent_type,
        filled=False,
        checks=checks,
        summary=summary,
        artifact_type="automated_review_prefill",
        human_reviewed=False,
    )


def _approved_fetched_source_evidence(result) -> List[ApprovedFetchedSourceEvidence]:
    fetch_records_by_url: Dict[str, object] = {
        record.canonical_url: record
        for record in result.web_fetch_records
        if record.record_type == "fetch" and record.canonical_url
    }
    evidence_items: Dict[Tuple[str, str], ApprovedFetchedSourceEvidence] = {}

    for entry in result.approved_entries:
        for citation in entry.citations:
            if citation.source_origin.value != "web" or not citation.canonical_url:
                continue
            fetch_record = fetch_records_by_url.get(citation.canonical_url)
            if fetch_record is None:
                continue
            evidence = ApprovedFetchedSourceEvidence(
                source_id=citation.source_id,
                canonical_url=citation.canonical_url,
                content_type=fetch_record.content_type or "unknown",
                content_digest=fetch_record.content_digest or "",
                provenance_record=fetch_record.provenance_record or "",
                normalization_status=fetch_record.normalization_status,
                citation_quality=citation.citation_quality,
                discovered_from=fetch_record.discovered_from,
                retrieval_timestamp=fetch_record.retrieval_timestamp,
            )
            evidence_items[(evidence.source_id, evidence.canonical_url)] = evidence

    return sorted(
        evidence_items.values(),
        key=lambda item: (item.source_id, item.canonical_url),
    )


def build_manual_review_report(
    result,
    verdict,
    *,
    scenario_id: Optional[str],
    catalog_path: Optional[str],
    corpus_state_id: Optional[str],
    reviewer_name: str = "Codex",
) -> ManualReviewReport:
    has_approved_entries = bool(result.approved_entries)
    blocked_visible = "Blocked:" in result.rendered_answer
    hierarchy_ok = all(
        entry.citations
        and all(
            citation.source_role_level.value in {"high", "medium", "low"}
            for citation in entry.citations
        )
        for entry in result.approved_entries
    )
    uncertainty_ok = not blocked_visible and all(
        (
            entry.final_claim_state != ClaimState.CONFIRMED
            or "Confirmed:" in result.rendered_answer
        )
        for entry in result.approved_entries
    )
    gap_exercised = any(gap.next_allowed_action == "official_web_search" for gap in result.gap_records)
    gap_ok = (
        all(
            gap.reason_local_evidence_insufficient and gap.local_source_layers_searched
            for gap in result.gap_records
        )
        if result.gap_records
        else True
    )
    topology_facets_ok = (
        result.facet_coverage_report is not None
        and result.facet_coverage_report.all_addressed()
    ) if result.query_intent.intent_type == "certificate_topology_analysis" else True
    correctness_verdict = "acceptable" if verdict.passed else "needs_follow_up"
    usefulness_verdict = (
        "acceptable" if has_approved_entries and topology_facets_ok else "needs_follow_up"
    )
    hierarchy_verdict = "acceptable" if hierarchy_ok else "needs_follow_up"
    uncertainty_verdict = "acceptable" if uncertainty_ok else "needs_follow_up"
    discovery_verdict = (
        "acceptable" if gap_ok else "needs_follow_up"
    ) if gap_exercised else "not_exercised"
    final_judgment = (
        "accept"
        if all(
            verdict_value == "acceptable"
            for verdict_value in [
                correctness_verdict,
                usefulness_verdict,
                hierarchy_verdict,
                uncertainty_verdict,
            ]
        )
        and discovery_verdict in {"acceptable", "not_exercised"}
        else "reject"
    )

    open_follow_ups: List[str] = []
    if not verdict.passed:
        open_follow_ups.append(
            "Scenario verdict did not fully pass; inspect verdict.json and failed checks before reuse."
        )
    if not has_approved_entries:
        open_follow_ups.append(
            "No approved entries were available; the answer is not yet reusable for research notes."
        )
    if gap_exercised and not gap_ok:
        open_follow_ups.append(
            "Discovery or gap handling needs manual inspection before this run can be trusted."
        )
    if not topology_facets_ok:
        open_follow_ups.append(
            "Topology facet coverage is incomplete; inspect facet_coverage.json before treating this run as reusable."
        )
    if not open_follow_ups:
        open_follow_ups.append("No blocking follow-up from this review pass.")

    return ManualReviewReport(
        scenario_id=scenario_id,
        corpus_selection=catalog_path or "fixture_catalog",
        corpus_state_id=corpus_state_id,
        reviewer_name=reviewer_name,
        review_date=datetime.utcnow().date().isoformat(),
        correctness_verdict=correctness_verdict,
        usefulness_verdict=usefulness_verdict,
        source_role_hierarchy_verdict=hierarchy_verdict,
        uncertainty_handling_verdict=uncertainty_verdict,
        discovery_gap_handling_verdict=discovery_verdict,
        open_follow_ups=open_follow_ups,
        final_judgment=final_judgment,
        approved_fetched_source_evidence=_approved_fetched_source_evidence(result),
    )


def build_manual_review_report_markdown(report: ManualReviewReport) -> str:
    lines = [
        "# Manual Review Report",
        "",
        f"- Scenario id: `{report.scenario_id or 'direct_run'}`",
        f"- Corpus selection: `{report.corpus_selection}`",
        f"- Corpus state id: `{report.corpus_state_id or 'n/a'}`",
        f"- Reviewer: `{report.reviewer_name}`",
        f"- Date: `{report.review_date}`",
        f"- Report type: `{report.report_type}`",
        f"- Human reviewed: `{str(report.human_reviewed).lower()}`",
        "",
        "## Judgments",
        "",
        f"- Correctness verdict: `{report.correctness_verdict}`",
        f"- Usefulness verdict: `{report.usefulness_verdict}`",
        f"- Source-role / hierarchy verdict: `{report.source_role_hierarchy_verdict}`",
        f"- Uncertainty-handling verdict: `{report.uncertainty_handling_verdict}`",
        f"- Discovery / gap-handling verdict: `{report.discovery_gap_handling_verdict}`",
        "",
        "## Open Follow-Ups",
        "",
    ]
    for follow_up in report.open_follow_ups:
        lines.append(f"- {follow_up}")
    lines.extend(
        [
            "",
            "## Approved Fetched-Source Evidence",
            "",
        ]
    )
    if report.approved_fetched_source_evidence:
        for evidence in report.approved_fetched_source_evidence:
            lines.append(
                "- "
                f"`{evidence.source_id}` "
                f"`{evidence.canonical_url}` "
                f"(type=`{evidence.content_type}`, "
                f"digest=`{evidence.content_digest}`, "
                f"normalization=`{evidence.normalization_status.value}`, "
                f"provenance=`{evidence.provenance_record}`)"
            )
    else:
        lines.append("- No approved fetched web sources in this run.")
    lines.extend(
        [
            "",
            "## Final Judgment",
            "",
            f"- Final accept / reject: `{report.final_judgment}`",
            "",
        ]
    )
    return "\n".join(lines)
