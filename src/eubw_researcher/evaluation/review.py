from __future__ import annotations

from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple

from eubw_researcher.answering import TOPOLOGY_FACET_IDS, supports_relation_hints
from eubw_researcher.models import (
    ApprovedFetchedSourceEvidence,
    ClaimState,
    ManualReviewArtifact,
    ManualReviewCheck,
    ManualReviewReport,
    SourceRoleLevel,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching
from eubw_researcher.trust import (
    answer_alignment_status,
    pinpoint_traceability_status,
    relation_hint_integrity_status,
)

GENERIC_RETRIEVAL_TERMS = {
    "attestation",
    "eidas",
    "eudi",
    "party",
    "parties",
    "provider",
    "providers",
    "relying",
    "service",
    "services",
    "unit",
    "wallet",
    "wallets",
}
GENERIC_RETRIEVAL_PHRASES = {
    "business wallet",
    "european business wallet",
    "wallet unit",
}


EUBW_STRUCTURED_INTENT_TYPES = {
    "eubw_role_boundary_analysis",
    "eubw_lifecycle_analysis",
    "eubw_audit_trail_analysis",
    "eubw_identity_authority_analysis",
    "eubw_architecture_bucket_analysis",
}
EUBW_ARCHITECTURE_BUCKET_CLAIMS = {
    "direkt ableitbar:": {
        "eubw_direct_architecture_constraints",
        "eubw_arf_subordination",
    },
    "delegiert:": {
        "eubw_identifier_delegated_specs",
        "eubw_access_control_delegated_specs",
    },
    "plausible Annahme:": {
        "eubw_trust_model_still_open",
    },
}

ROLE_BOUNDARY_REQUIRED_FACETS = {
    "actor_boundary": ["intermediaer", "intermediary", "wallet-relying party", "relying party"],
    "registry_information": ["registrierung", "registration", "register", "zertifikat", "certificate"],
    "user_display": ["nutzeranzeige", "anzeige", "display", "request"],
    "purpose_or_intended_use": ["zweck", "purpose", "intended use"],
    "requested_attributes": ["attribute", "attributes"],
    "privacy_policy_or_dpa": ["datenschutz", "privacy", "dpa"],
}


def _is_eubw_structured_intent(intent_type: str) -> bool:
    return intent_type in EUBW_STRUCTURED_INTENT_TYPES


def _approved_claim_ids(result) -> set[str]:
    return {
        claim_id
        for claim_id in (
            getattr(entry, "claim_id", None)
            for entry in getattr(result, "approved_entries", [])
        )
        if isinstance(claim_id, str) and claim_id
    }


def _fetch_record_allowlist_ok(record) -> bool:
    if record.record_type != "fetch":
        return True
    if record.allowed:
        return True
    reason = getattr(record, "reason", "") or ""
    return bool(getattr(record, "policy_id", None)) and reason.startswith("Fetch failed:")


def _has_eubw_parity_question_signal(question: str) -> bool:
    lowered = question.casefold()
    return any(
        marker in lowered
        for marker in [
            "eubw",
            "ebw",
            "business wallet",
            "verantwortungsgrenzen",
            "registerdaten",
            "vertretungsrechte",
            "unternehmensstatus",
            "ereignisspuren",
            "vollprotokollierung",
            "handlungsbefugnis",
            "juristische person",
            "proposal und annex",
            "plausible architekturannahmen",
        ]
    )


def _is_eubw_broad_fallback(result) -> bool:
    intent_type = result.query_intent.intent_type
    approved_claim_ids = _approved_claim_ids(result)
    parity_signal = _is_eubw_structured_intent(intent_type) or _has_eubw_parity_question_signal(
        result.question
    )
    if not parity_signal:
        return False
    if "broad_regulatory_answer" in approved_claim_ids:
        return True
    dynamic_claim_used = any(
        claim_id.startswith("dynamic_") for claim_id in approved_claim_ids
    )
    return intent_type == "broad_regulation_question" and not dynamic_claim_used


def _eubw_architecture_bucket_visibility(result) -> bool:
    approved_claim_ids = _approved_claim_ids(result)
    return all(
        marker in result.rendered_answer
        for marker, claim_ids in EUBW_ARCHITECTURE_BUCKET_CLAIMS.items()
        if approved_claim_ids & claim_ids
    )


def _claim_state_visibility_ok(result) -> bool:
    intent_type = result.query_intent.intent_type
    visible_entries = [
        entry
        for entry in result.approved_entries
        if not (
            entry.claim_id.startswith(("CLM-", "CLMSEED-"))
            and not any(citation.anchor_label for citation in entry.citations)
        )
    ]
    if intent_type == "eubw_architecture_bucket_analysis":
        return _eubw_architecture_bucket_visibility(result)
    if _is_eubw_structured_intent(intent_type):
        state_markers = {
            "Normative evidence:": any(
                entry.final_claim_state != ClaimState.OPEN
                and entry.source_role_level != SourceRoleLevel.MEDIUM
                for entry in visible_entries
            ),
            "Interpretation/context:": any(
                entry.final_claim_state != ClaimState.OPEN
                and entry.source_role_level == SourceRoleLevel.MEDIUM
                for entry in visible_entries
            ),
            "Open issues:": any(
                entry.final_claim_state == ClaimState.OPEN
                for entry in visible_entries
            ),
        }
    else:
        state_markers = {
            "Confirmed:": any(
                entry.final_claim_state == ClaimState.CONFIRMED
                for entry in visible_entries
            ),
            "Interpretive:": any(
                entry.final_claim_state == ClaimState.INTERPRETIVE
                for entry in visible_entries
            ),
            "Open:": any(
                entry.final_claim_state == ClaimState.OPEN
                for entry in visible_entries
            ),
        }
    return all(
        (not expected) or marker in result.rendered_answer
        for marker, expected in state_markers.items()
    )


def _topology_facet_status(result, facet_id: str) -> tuple[bool, str]:
    if result.facet_coverage_report is None:
        return False, "facet_coverage.json was not produced for the topology intent."
    facet = result.facet_coverage_report.by_id().get(facet_id)
    if facet is None:
        return False, f"Required topology facet `{facet_id}` is missing from facet_coverage.json."
    evidence = ", ".join(facet.evidence) if facet.evidence else "No structural evidence recorded."
    return facet.addressed, evidence


def _diagnostic_candidates(result) -> list[dict]:
    diagnostics = getattr(result, "knowledge_retrieval_diagnostics", None) or {}
    candidates = diagnostics.get("top_source_candidates", [])
    return [candidate for candidate in candidates if isinstance(candidate, dict)]


def _candidate_distinctive_values(candidate: dict) -> List[str]:
    matched_terms = [
        str(term)
        for term in candidate.get("matched_terms", [])
        if str(term) not in GENERIC_RETRIEVAL_TERMS and len(str(term)) > 3
    ]
    matched_phrases = [
        str(phrase)
        for phrase in candidate.get("matched_phrases", [])
        if len(str(phrase)) > 3
        and normalize_text_for_matching(str(phrase)) not in GENERIC_RETRIEVAL_PHRASES
    ]
    return [*matched_phrases, *matched_terms]


def _candidate_score(candidate: dict) -> float:
    try:
        return float(candidate.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _channel_score(candidate: dict, channel: str) -> float:
    channel_scores = candidate.get("channel_scores", {})
    if not isinstance(channel_scores, dict):
        return 0.0
    try:
        return float(channel_scores.get(channel, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _required_diagnostic_candidates(result) -> list[dict]:
    candidates = _diagnostic_candidates(result)
    if not candidates:
        return []
    required: list[dict] = []
    for candidate in candidates:
        if _candidate_score(candidate) >= 0.72:
            required.append(candidate)
    top_candidate = candidates[0]
    second_score = _candidate_score(candidates[1]) if len(candidates) > 1 else 0.0
    top_score = _candidate_score(top_candidate)
    top_reasons = {str(reason) for reason in top_candidate.get("reasons", [])}
    has_source_title_signal = (
        "distinctive_source_phrase" in top_reasons
        or _channel_score(top_candidate, "unique_title_phrase_bonus") > 0
        or _channel_score(top_candidate, "source_title_or_path_phrase") > 0
    )
    if (
        top_score >= 0.45
        and top_score >= second_score + 0.15
        and has_source_title_signal
        and _candidate_distinctive_values(top_candidate)
    ):
        required.append(top_candidate)
    deduped: list[dict] = []
    seen: set[str] = set()
    for candidate in required:
        source_id = str(candidate.get("source_id", ""))
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        deduped.append(candidate)
    return deduped


def _surface_contains_any(surface: str, values: List[str]) -> bool:
    normalized = normalize_text_for_matching(surface)
    return any(
        normalize_text_for_matching(value) in normalized
        for value in values
        if value
    )


def _topic_drift_status(result) -> tuple[bool, str]:
    diagnostics = getattr(result, "knowledge_retrieval_diagnostics", None)
    if not diagnostics:
        return True, "Knowledge retrieval diagnostics were not produced; topic-drift guard not exercised."
    strong_candidates = _required_diagnostic_candidates(result)
    if not strong_candidates:
        return True, "No high-confidence source candidate required topic-drift gating."

    opened_source_ids = {
        passage.source_id for passage in getattr(result, "opened_passages", [])
    }
    if getattr(result, "reading_plan", None) is not None:
        opened_source_ids.update(item.source_id for item in result.reading_plan.items)
    matrix = getattr(result, "evidence_synthesis_matrix", None)
    matrix_source_ids = {
        source_id
        for record in (matrix.records if matrix is not None else [])
        for source_id in record.source_ids
    }
    final_answer = getattr(result, "rendered_answer", "")
    matrix_surface = " ".join(
        " ".join(
            [
                getattr(record, "statement", ""),
                " ".join(getattr(record, "source_ids", []) or []),
                " ".join(getattr(record, "locators", []) or []),
            ]
        )
        for record in (matrix.records if matrix is not None else [])
    )

    for candidate in strong_candidates[:3]:
        source_id = str(candidate.get("source_id", ""))
        distinctive_values = _candidate_distinctive_values(candidate)
        if source_id and source_id not in opened_source_ids:
            return (
                False,
                f"High-confidence source candidate `{source_id}` was discovered but not opened in the reading plan.",
            )
        if source_id and source_id not in matrix_source_ids:
            return (
                False,
                f"High-confidence source candidate `{source_id}` is absent from evidence_synthesis_matrix.json.",
            )
        if distinctive_values and not _surface_contains_any(final_answer, distinctive_values):
            return (
                False,
                "The final answer does not surface the distinctive concept that drove the top source candidate.",
            )
        if distinctive_values and not _surface_contains_any(matrix_surface, distinctive_values):
            return (
                False,
                "The synthesis matrix does not retain the distinctive concept that drove the top source candidate.",
            )

    return True, "High-confidence source candidates were opened and retained in the answer surface."


def _vnext_product_answer_expected(result) -> bool:
    return any(
        getattr(result, attribute, None) is not None
        for attribute in [
            "evidence_synthesis_matrix",
            "reading_plan",
            "knowledge_retrieval_diagnostics",
        ]
    ) or bool(getattr(result, "opened_passages", []))


def _role_boundary_facets(result) -> set[str]:
    facets: set[str] = set()
    diagnostics = getattr(result, "knowledge_retrieval_diagnostics", None) or {}
    if isinstance(diagnostics, dict):
        facets.update(str(facet) for facet in diagnostics.get("question_facets", []) or [])
    matrix = getattr(result, "evidence_synthesis_matrix", None)
    for record in (matrix.records if matrix is not None else []):
        facets.update(str(facet) for facet in (getattr(record, "facet_tags", []) or []))
    normalized_question = normalize_text_for_matching(getattr(result, "question", "") or "")
    if any(term in normalized_question for term in ["intermediaer", "intermediary", "auseinanderhalten"]):
        facets.add("actor_boundary")
    for facet_id, terms in ROLE_BOUNDARY_REQUIRED_FACETS.items():
        if any(term in normalized_question for term in terms):
            facets.add(facet_id)
    return facets


def _role_boundary_semantic_status(result) -> tuple[bool, str]:
    facets = _role_boundary_facets(result)
    if "actor_boundary" not in facets or len(facets & set(ROLE_BOUNDARY_REQUIRED_FACETS)) < 4:
        return True, "No role-boundary semantic gate was required for this answer."

    answer_before_details = (getattr(result, "rendered_answer", "") or "").split("Pruefdetails:", 1)[0]
    normalized_answer = normalize_text_for_matching(answer_before_details)
    missing_facets = [
        facet_id
        for facet_id, terms in ROLE_BOUNDARY_REQUIRED_FACETS.items()
        if facet_id in facets and not any(term in normalized_answer for term in terms)
    ]
    if missing_facets:
        return (
            False,
            "Role-boundary answer is missing distinctive facets before Pruefdetails: "
            + ", ".join(missing_facets)
            + ".",
        )
    if not re.search(
        r"\b(?:SRC-[A-Z0-9_-]+|[a-z0-9]+(?:_[a-z0-9]+){2,})\b",
        answer_before_details,
        flags=re.IGNORECASE,
    ):
        return (
            False,
            "Role-boundary user-facing answer has no source anchor before Pruefdetails.",
        )
    first_section = normalized_answer.split("\n", 3)[0:3]
    first_surface = " ".join(first_section)
    generic_hits = sum(
        1
        for term in [
            "subject matter",
            "scope",
            "article 1",
            "euid",
            "write method",
            "api",
        ]
        if term in first_surface
    )
    distinctive_hits = sum(
        1
        for terms in ROLE_BOUNDARY_REQUIRED_FACETS.values()
        if any(term in first_surface for term in terms)
    )
    if generic_hits >= 2 and distinctive_hits < 3:
        return (
            False,
            "Role-boundary Kurzantwort is dominated by generic scope or registration text.",
        )
    matrix = getattr(result, "evidence_synthesis_matrix", None)
    if matrix is not None:
        driving_records = [
            record
            for record in matrix.records
            if any(source_id in answer_before_details for source_id in getattr(record, "source_ids", []) or [])
        ]
        weak_drivers = [
            record
            for record in driving_records
            if getattr(record, "answer_role", "") in {"background", "definition_only"}
            or set(getattr(record, "quality_flags", []) or []).intersection(
                {"references_only", "table_note", "title_only", "definition_only"}
            )
        ]
        if driving_records and len(weak_drivers) == len(driving_records):
            return (
                False,
                "Role-boundary user answer is driven only by background or definition-like evidence rows.",
            )
    return True, "Role-boundary answer covers distinctive facets with a user-facing source anchor."


def _answer_usability_status(result) -> tuple[bool, str]:
    rendered_answer = getattr(result, "rendered_answer", "") or ""
    normalized = normalize_text_for_matching(rendered_answer)
    if "passage supports" in normalized:
        return (
            False,
            "final_answer.txt leaks the internal `Passage supports` template marker.",
        )
    first_non_empty_line = next(
        (line.strip() for line in rendered_answer.splitlines() if line.strip()),
        "",
    )
    if first_non_empty_line.lower().startswith(("source supports:", "evidence supports:")):
        return (
            False,
            "final_answer.txt starts with an internal evidence-support template marker.",
        )
    if _vnext_product_answer_expected(result) or "Pruefdetails:" in rendered_answer:
        if not rendered_answer.lstrip().startswith("Kurzantwort:"):
            return (
                False,
                "vNext answer bundle does not start with a user-facing Kurzantwort section.",
            )
        if "Pruefdetails:" not in rendered_answer:
            return (
                False,
                "vNext answer bundle has no separated Pruefdetails section.",
            )
        if rendered_answer.index("Pruefdetails:") < rendered_answer.index("Kurzantwort:"):
            return (
                False,
                "Pruefdetails appear before the user-facing Kurzantwort.",
            )
    strong_candidates = _required_diagnostic_candidates(result)
    if strong_candidates:
        answer_before_details = rendered_answer.split("Pruefdetails:", 1)[0]
        for candidate in strong_candidates[:2]:
            source_id = str(candidate.get("source_id", ""))
            if source_id and source_id not in answer_before_details:
                return (
                    False,
                    f"High-confidence source candidate `{source_id}` is absent from the user-facing answer before Pruefdetails.",
                )
    role_boundary_ok, role_boundary_evidence = _role_boundary_semantic_status(result)
    if not role_boundary_ok:
        return False, role_boundary_evidence
    return True, "The final answer starts with reusable product prose and keeps template/detail leakage out of the user-facing section."


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

    states_visible = _claim_state_visibility_ok(result)
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

    web_allowed = all(
        _fetch_record_allowlist_ok(record) for record in result.web_fetch_records
    )
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

    grouped_ok = bool(getattr(result, "provisional_grouping", [])) or not any(
        target.grouping_label
        for target in getattr(result.query_intent, "claim_targets", [])
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

    eubw_fallback_ok = not _is_eubw_broad_fallback(result)
    checks.append(
        ManualReviewCheck(
            check_id="eubw_parity_fallback_not_accepted",
            status="pass" if eubw_fallback_ok else "fail",
            evidence=(
                "EUBW parity answer did not use the broad regulatory fallback."
                if eubw_fallback_ok
                else "EUBW parity-shaped question approved a broad regulatory fallback claim."
            ),
        )
    )

    pinpoint_ok, pinpoint_evidence = pinpoint_traceability_status(result)
    checks.append(
        ManualReviewCheck(
            check_id="pinpoint_traceability",
            status="pass" if pinpoint_ok else "fail",
            evidence=pinpoint_evidence,
        )
    )

    alignment_ok, alignment_evidence = answer_alignment_status(result)
    checks.append(
        ManualReviewCheck(
            check_id="answer_evidence_alignment",
            status="pass" if alignment_ok else "fail",
            evidence=alignment_evidence,
        )
    )

    topic_drift_ok, topic_drift_evidence = _topic_drift_status(result)
    checks.append(
        ManualReviewCheck(
            check_id="topic_drift_guard",
            status="pass" if topic_drift_ok else "fail",
            evidence=topic_drift_evidence,
        )
    )

    answer_usability_ok, answer_usability_evidence = _answer_usability_status(result)
    checks.append(
        ManualReviewCheck(
            check_id="answer_usability_surface",
            status="pass" if answer_usability_ok else "fail",
            evidence=answer_usability_evidence,
        )
    )

    blind_validation_report = getattr(result, "blind_validation_report", None)
    blind_validation_ok = blind_validation_report is not None and blind_validation_report.passed
    checks.append(
        ManualReviewCheck(
            check_id="product_output_self_sufficiency",
            status="pass" if blind_validation_ok else "fail",
            evidence=(
                blind_validation_report.summary
                if blind_validation_report is not None
                else "blind_validation_report.json was not produced."
            ),
        )
    )

    relation_hints_ok, relation_hints_evidence, _relation_hint_missing_facets = (
        relation_hint_integrity_status(result)
    )
    checks.append(
        ManualReviewCheck(
            check_id="relation_hints_artifact",
            status="pass" if relation_hints_ok else "fail",
            evidence=relation_hints_evidence,
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
    fetch_records_by_source_id: Dict[str, object] = {
        record.source_id: record
        for record in result.web_fetch_records
        if record.record_type == "fetch" and record.source_id
    }
    fetch_records_by_url_and_kind: Dict[Tuple[str, object], object] = {
        (record.canonical_url, record.source_kind): record
        for record in result.web_fetch_records
        if record.record_type == "fetch" and record.canonical_url and record.source_kind is not None
    }
    evidence_items: Dict[Tuple[str, str], ApprovedFetchedSourceEvidence] = {}

    for entry in result.approved_entries:
        for citation in entry.citations:
            if citation.source_origin.value != "web" or not citation.canonical_url:
                continue
            fetch_record = fetch_records_by_source_id.get(citation.source_id)
            if fetch_record is None:
                citation_source_kind = getattr(citation, "source_kind", None)
                if citation_source_kind is None:
                    continue
                fetch_record = fetch_records_by_url_and_kind.get(
                    (citation.canonical_url, citation_source_kind)
                )
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
                policy_id=fetch_record.policy_id,
                entrypoint_id=fetch_record.entrypoint_id,
                discovery_strategy=fetch_record.discovery_strategy,
                admission_rule=fetch_record.admission_rule,
                discovery_query=fetch_record.discovery_query,
            )
            evidence_items[(evidence.source_id, evidence.canonical_url)] = evidence

    return sorted(
        evidence_items.values(),
        key=lambda item: (item.source_id, item.canonical_url),
    )


def _germany_dependency_summary(result) -> dict[str, list[str]]:
    if result.query_intent.intent_type != "germany_wallet_implementation_status":
        return {}

    used_source_ids: set[str] = set()
    claims_with_de_support: set[str] = set()
    medium_rank_only_claim_ids: set[str] = set()

    for entry in result.approved_entries:
        de_citations = [citation for citation in entry.citations if citation.jurisdiction == "DE"]
        if not de_citations:
            continue
        used_source_ids.update(citation.source_id for citation in de_citations)
        claims_with_de_support.add(entry.claim_id)
        if all(citation.source_role_level == SourceRoleLevel.MEDIUM for citation in de_citations):
            medium_rank_only_claim_ids.add(entry.claim_id)

    return {
        "used_source_ids": sorted(used_source_ids),
        "claims_with_de_support": sorted(claims_with_de_support),
        "medium_rank_only_claim_ids": sorted(medium_rank_only_claim_ids),
    }


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
    eubw_fallback_ok = not _is_eubw_broad_fallback(result)
    hierarchy_ok = all(
        entry.citations
        and all(
            citation.source_role_level.value in {"high", "medium", "low"}
            for citation in entry.citations
        )
        for entry in result.approved_entries
    )
    uncertainty_ok = not blocked_visible and _claim_state_visibility_ok(result)
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
    pinpoint_ok, _ = pinpoint_traceability_status(result)
    alignment_ok, _ = answer_alignment_status(result)
    topic_drift_ok, topic_drift_evidence = _topic_drift_status(result)
    answer_usability_ok, answer_usability_evidence = _answer_usability_status(result)
    blind_validation_report = getattr(result, "blind_validation_report", None)
    blind_validation_ok = blind_validation_report is not None and blind_validation_report.passed
    relation_hints_ok, _relation_hints_evidence, _relation_hint_missing_facets = (
        relation_hint_integrity_status(result)
    )
    relation_hint_report = getattr(result, "relation_hint_report", None)
    rendered_relation_hint_ids = (
        [
            record.hint_id
            for record in relation_hint_report.records
            if record.rendered_in_answer
        ]
        if relation_hint_report is not None
        else []
    )
    bundle_only_relation_hint_ids = (
        [
            record.hint_id
            for record in relation_hint_report.records
            if not record.rendered_in_answer
        ]
        if relation_hint_report is not None
        else []
    )
    source_bound_ok = has_approved_entries and not blocked_visible and eubw_fallback_ok
    correctness_verdict = "acceptable" if verdict.passed else "needs_follow_up"
    usefulness_verdict = (
        "acceptable"
        if has_approved_entries and topology_facets_ok and eubw_fallback_ok and answer_usability_ok
        else "needs_follow_up"
    )
    hierarchy_verdict = "acceptable" if hierarchy_ok else "needs_follow_up"
    uncertainty_verdict = "acceptable" if uncertainty_ok else "needs_follow_up"
    discovery_verdict = (
        "acceptable" if gap_ok else "needs_follow_up"
    ) if gap_exercised else "not_exercised"
    source_bound_verdict = "acceptable" if source_bound_ok else "needs_follow_up"
    pinpoint_verdict = "acceptable" if pinpoint_ok else "needs_follow_up"
    alignment_verdict = "acceptable" if alignment_ok else "needs_follow_up"
    topic_drift_verdict = "acceptable" if topic_drift_ok else "needs_follow_up"
    self_sufficiency_verdict = (
        "acceptable" if blind_validation_ok else "needs_follow_up"
    )
    final_judgment = (
        "accept"
        if all(
            verdict_value == "acceptable"
            for verdict_value in [
                correctness_verdict,
                usefulness_verdict,
                hierarchy_verdict,
                uncertainty_verdict,
                source_bound_verdict,
                pinpoint_verdict,
                alignment_verdict,
                topic_drift_verdict,
                self_sufficiency_verdict,
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
    if not eubw_fallback_ok:
        open_follow_ups.append(
            "EUBW parity-shaped question fell back to the broad regulatory answer; inspect intent routing and approved_ledger.json before reuse."
        )
    if not pinpoint_ok:
        open_follow_ups.append(
            "Pinpoint traceability is incomplete; inspect pinpoint_evidence.json before relying on this run."
        )
    if not alignment_ok:
        open_follow_ups.append(
            "Answer wording and cited evidence are not structurally aligned; inspect answer_alignment.json."
        )
    if not topic_drift_ok:
        open_follow_ups.append(topic_drift_evidence)
    if not answer_usability_ok:
        open_follow_ups.append(answer_usability_evidence)
    if not blind_validation_ok:
        open_follow_ups.append(
            "The product-output-first blind-validation gate did not pass; inspect blind_validation_report.json."
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
        source_bound_verdict=source_bound_verdict,
        pinpoint_traceability_verdict=pinpoint_verdict,
        answer_evidence_alignment_verdict=alignment_verdict,
        product_output_self_sufficiency_verdict=self_sufficiency_verdict,
        approved_fetched_source_evidence=_approved_fetched_source_evidence(result),
        germany_dependency_summary=_germany_dependency_summary(result),
        relation_hints_artifact_present=relation_hint_report is not None,
        relation_hint_integrity_verdict=(
            "acceptable"
            if relation_hints_ok
            else "needs_follow_up"
        )
        if supports_relation_hints(result.query_intent.intent_type)
        else "not_applicable",
        relation_hint_families_considered=(
            list(relation_hint_report.families_considered)
            if relation_hint_report is not None
            else []
        ),
        relation_hint_rendered_ids=rendered_relation_hint_ids,
        relation_hint_bundle_only_ids=bundle_only_relation_hint_ids,
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
        "## Trust Surface",
        "",
        f"- Source-bound verdict: `{report.source_bound_verdict}`",
        f"- Pinpoint traceability verdict: `{report.pinpoint_traceability_verdict}`",
        f"- Answer / evidence alignment verdict: `{report.answer_evidence_alignment_verdict}`",
        f"- Reusable without raw-document reconstruction: `{report.product_output_self_sufficiency_verdict}`",
        "",
        "## Relation Hints",
        "",
        f"- Artifact present: `{str(report.relation_hints_artifact_present).lower()}`",
        f"- Integrity verdict: `{report.relation_hint_integrity_verdict}`",
        "- Families considered: "
        + (
            ", ".join(f"`{item}`" for item in report.relation_hint_families_considered)
            if report.relation_hint_families_considered
            else "none"
        ),
        "- Rendered hint ids: "
        + (
            ", ".join(f"`{item}`" for item in report.relation_hint_rendered_ids)
            if report.relation_hint_rendered_ids
            else "none"
        ),
        "- Bundle-only hint ids: "
        + (
            ", ".join(f"`{item}`" for item in report.relation_hint_bundle_only_ids)
            if report.relation_hint_bundle_only_ids
            else "none"
        ),
        "- Relation hints remain supplemental and do not replace the approved-ledger model.",
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
                f"provenance=`{evidence.provenance_record}`, "
                f"policy_id=`{evidence.policy_id or 'n/a'}`, "
                f"entrypoint_id=`{evidence.entrypoint_id or 'n/a'}`, "
                f"strategy=`{evidence.discovery_strategy or 'n/a'}`, "
                f"admission_rule=`{evidence.admission_rule or 'n/a'}`, "
                f"discovery_query=`{evidence.discovery_query or 'n/a'}`)"
            )
    else:
        lines.append("- No approved fetched web sources in this run.")
    if report.germany_dependency_summary:
        lines.extend(
            [
                "",
                "## Germany Dependency Summary",
                "",
                "- Used DE source ids: "
                + (
                    ", ".join(
                        f"`{item}`" for item in report.germany_dependency_summary["used_source_ids"]
                    )
                    or "none"
                ),
                "- Claims with DE support: "
                + (
                    ", ".join(
                        f"`{item}`"
                        for item in report.germany_dependency_summary["claims_with_de_support"]
                    )
                    or "none"
                ),
                "- Claims relying only on medium-rank DE sources: "
                + (
                    ", ".join(
                        f"`{item}`"
                        for item in report.germany_dependency_summary["medium_rank_only_claim_ids"]
                    )
                    or "none"
                ),
            ]
        )
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
