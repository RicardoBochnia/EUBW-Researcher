from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from eubw_researcher.models import (
    AnchorQuality,
    CitationQuality,
    ClaimState,
    ClaimTarget,
    ContradictionStatus,
    EvidenceMatch,
    LedgerEntry,
    LedgerEvidence,
    QueryIntent,
    RetrievalCandidate,
    SourceHierarchyConfig,
    SourceRoleLevel,
    SupportDirectness,
)

OPEN_MARGIN = 1


def _contains_group(text: str, group: Sequence[str]) -> bool:
    lowered = text.lower()
    return all(item.lower() in lowered for item in group)


def _classify_candidate(
    target: ClaimTarget,
    candidate: RetrievalCandidate,
) -> EvidenceMatch:
    text = candidate.chunk.text.lower()
    scope_overlap = sum(1 for token in target.scope_terms if token in text)
    support_signal_count = sum(
        1
        for group in target.support_groups
        for term in group
        if term.lower() in text
    )
    direct_support = scope_overlap > 0 and any(
        _contains_group(text, group) for group in target.support_groups
    )
    contradiction = scope_overlap > 0 and any(
        _contains_group(text, group) for group in target.contradiction_groups
    )
    overlap = sum(1 for token in target.primary_terms if token in text)
    return EvidenceMatch(
        claim_target=target,
        candidate=candidate,
        support_directness=SupportDirectness.DIRECT
        if direct_support or contradiction
        else SupportDirectness.INDIRECT,
        contradiction=contradiction,
        term_overlap=overlap,
        scope_overlap=scope_overlap,
        support_signal_count=support_signal_count,
    )


def _is_admissible(role_level: SourceRoleLevel) -> bool:
    return role_level in (SourceRoleLevel.HIGH, SourceRoleLevel.MEDIUM)


def _role_weight(role_level: SourceRoleLevel) -> int:
    return {
        SourceRoleLevel.HIGH: 3,
        SourceRoleLevel.MEDIUM: 2,
        SourceRoleLevel.LOW: 1,
    }[role_level]


def _satisfies_required_role(
    actual_role: SourceRoleLevel,
    required_role: SourceRoleLevel,
) -> bool:
    return _role_weight(actual_role) >= _role_weight(required_role)


def _citation_weight(citation_quality: CitationQuality) -> int:
    return 2 if citation_quality == CitationQuality.ANCHOR_GROUNDED else 1


def _on_point_score(match: EvidenceMatch, target: ClaimTarget) -> int:
    direct_bonus = 2 if match.support_directness == SupportDirectness.DIRECT else 0
    kind_bonus = 1 if match.candidate.chunk.source_kind in target.preferred_kinds else 0
    return (
        direct_bonus
        + _citation_weight(match.candidate.chunk.citation_quality)
        + kind_bonus
        + match.term_overlap
        + match.scope_overlap
    )


def _preferred_kind_weight(match: EvidenceMatch, target: ClaimTarget) -> int:
    return 1 if match.candidate.chunk.source_kind in target.preferred_kinds else 0


def _kind_precedence_weight(match: EvidenceMatch, hierarchy: SourceHierarchyConfig) -> int:
    # Lower configured rank means stronger precedence.
    return 100 - hierarchy.rank_for(match.candidate.chunk.source_kind)


def _precedence_key(
    match: EvidenceMatch,
    target: ClaimTarget,
    hierarchy: SourceHierarchyConfig,
) -> Tuple[int, int, int]:
    return (
        _role_weight(match.candidate.chunk.source_role_level),
        _preferred_kind_weight(match, target),
        _kind_precedence_weight(match, hierarchy),
    )


def _sort_key(
    match: EvidenceMatch,
    target: ClaimTarget,
    hierarchy: SourceHierarchyConfig,
) -> Tuple[int, int, int, int, int, int]:
    return (
        *_precedence_key(match, target, hierarchy),
        1 if match.support_directness == SupportDirectness.DIRECT else 0,
        _citation_weight(match.candidate.chunk.citation_quality),
        _on_point_score(match, target),
    )


def _to_ledger_evidence(
    match: EvidenceMatch,
    target: ClaimTarget,
    hierarchy: SourceHierarchyConfig,
) -> LedgerEvidence:
    return LedgerEvidence(
        citation=match.candidate.chunk.citation,
        source_role_level=match.candidate.chunk.source_role_level,
        source_kind=match.candidate.chunk.source_kind,
        source_kind_rank=hierarchy.rank_for(match.candidate.chunk.source_kind),
        source_origin=match.candidate.chunk.source_origin,
        jurisdiction=match.candidate.chunk.jurisdiction,
        support_directness=match.support_directness,
        term_overlap=match.term_overlap,
        scope_overlap=match.scope_overlap,
        on_point_score=_on_point_score(match, target),
        admissible=_is_admissible(match.candidate.chunk.source_role_level),
        citation_quality=match.candidate.chunk.citation_quality,
        anchor_audit_note=(
            match.candidate.chunk.anchor_audit.audit_note
            if match.candidate.chunk.anchor_audit is not None
            else None
        ),
    )


def _sort_matches(
    target: ClaimTarget,
    matches: Sequence[EvidenceMatch],
    hierarchy: SourceHierarchyConfig,
) -> List[EvidenceMatch]:
    return sorted(matches, key=lambda item: _sort_key(item, target, hierarchy), reverse=True)


def collect_target_evidence(
    target: ClaimTarget,
    candidates: Sequence[RetrievalCandidate],
    hierarchy: SourceHierarchyConfig,
) -> Tuple[List[EvidenceMatch], List[EvidenceMatch]]:
    classified = [_classify_candidate(target, candidate) for candidate in candidates]
    support_matches = [
        match
        for match in classified
        if not match.contradiction
        and (
            match.support_directness == SupportDirectness.DIRECT
            or (match.scope_overlap > 0 and match.support_signal_count > 0)
        )
    ]
    contradiction_matches = [match for match in classified if match.contradiction]
    return (
        _sort_matches(target, support_matches, hierarchy),
        _sort_matches(target, contradiction_matches, hierarchy),
    )


def has_direct_admissible_support(
    target: ClaimTarget,
    candidates: Sequence[RetrievalCandidate],
    hierarchy: SourceHierarchyConfig,
) -> bool:
    support_matches, _ = collect_target_evidence(target, candidates, hierarchy)
    return any(
        match.support_directness == SupportDirectness.DIRECT
        and _satisfies_required_role(
            match.candidate.chunk.source_role_level,
            target.required_source_role_level,
        )
        for match in support_matches
    )


def _document_only_confirmable(match: EvidenceMatch) -> bool:
    chunk = match.candidate.chunk
    audit = chunk.anchor_audit
    return (
        chunk.citation_quality == CitationQuality.DOCUMENT_ONLY
        and audit is not None
        and audit.is_document_only_confirmable()
        and match.support_directness == SupportDirectness.DIRECT
        and chunk.source_role_level == SourceRoleLevel.HIGH
        and chunk.anchor_quality == AnchorQuality.MISSING
    )


def _admissible_matches(
    target: ClaimTarget,
    matches: Sequence[EvidenceMatch],
) -> List[EvidenceMatch]:
    return [
        match
        for match in matches
        if _is_admissible(match.candidate.chunk.source_role_level)
    ]


def _relevant_contradictions(
    target: ClaimTarget,
    best_support: EvidenceMatch,
    contradiction_matches: Sequence[EvidenceMatch],
    hierarchy: SourceHierarchyConfig,
) -> List[EvidenceMatch]:
    support_precedence = _precedence_key(best_support, target, hierarchy)
    return [
        match
        for match in _admissible_matches(target, contradiction_matches)
        if _precedence_key(match, target, hierarchy) >= support_precedence
    ]


def _same_rank_conflict_requires_open(
    target: ClaimTarget,
    best_support: EvidenceMatch,
    contradiction_matches: Sequence[EvidenceMatch],
    hierarchy: SourceHierarchyConfig,
) -> bool:
    support_precedence = _precedence_key(best_support, target, hierarchy)
    for contradiction in _relevant_contradictions(
        target,
        best_support,
        contradiction_matches,
        hierarchy,
    ):
        if _precedence_key(contradiction, target, hierarchy) != support_precedence:
            continue
        score_delta = _on_point_score(best_support, target) - _on_point_score(contradiction, target)
        if score_delta <= OPEN_MARGIN:
            return True
    return False


def _choose_governing_matches(
    target: ClaimTarget,
    support_matches: Sequence[EvidenceMatch],
    contradiction_matches: Sequence[EvidenceMatch],
    hierarchy: SourceHierarchyConfig,
) -> List[EvidenceMatch]:
    admissible_supports = _admissible_matches(target, support_matches)
    if not admissible_supports:
        return []
    best_support = admissible_supports[0]
    if _same_rank_conflict_requires_open(target, best_support, contradiction_matches, hierarchy):
        same_rank_conflicts = [
            match
            for match in _relevant_contradictions(
                target,
                best_support,
                contradiction_matches,
                hierarchy,
            )
            if _precedence_key(match, target, hierarchy)
            == _precedence_key(best_support, target, hierarchy)
        ]
        return [best_support, same_rank_conflicts[0]]
    return [best_support]


def _final_claim_state(
    target: ClaimTarget,
    support_matches: Sequence[EvidenceMatch],
    contradiction_matches: Sequence[EvidenceMatch],
    hierarchy: SourceHierarchyConfig,
) -> ClaimState:
    admissible_supports = _admissible_matches(target, support_matches)
    if not admissible_supports:
        return ClaimState.BLOCKED

    best_support = admissible_supports[0]
    if _same_rank_conflict_requires_open(target, best_support, contradiction_matches, hierarchy):
        return ClaimState.OPEN

    if (
        best_support.candidate.chunk.source_role_level == SourceRoleLevel.HIGH
        and best_support.support_directness == SupportDirectness.DIRECT
    ):
        if best_support.candidate.chunk.citation_quality == CitationQuality.ANCHOR_GROUNDED:
            return ClaimState.CONFIRMED
        if _document_only_confirmable(best_support):
            return ClaimState.CONFIRMED
        return ClaimState.INTERPRETIVE

    return ClaimState.INTERPRETIVE


def build_ledger(
    query_intent: QueryIntent,
    candidates_by_step: Dict[str, List[RetrievalCandidate]],
    hierarchy: SourceHierarchyConfig,
) -> List[LedgerEntry]:
    all_candidates = [
        candidate
        for step_candidates in candidates_by_step.values()
        for candidate in step_candidates
    ]
    ledger_entries: List[LedgerEntry] = []

    for target in query_intent.claim_targets:
        support_matches, contradiction_matches = collect_target_evidence(
            target,
            all_candidates,
            hierarchy,
        )
        supporting_evidence = [
            _to_ledger_evidence(match, target, hierarchy) for match in support_matches
        ]
        contradicting_evidence = [
            _to_ledger_evidence(match, target, hierarchy) for match in contradiction_matches
        ]
        governing_evidence = [
            _to_ledger_evidence(match, target, hierarchy)
            for match in _choose_governing_matches(
                target,
                support_matches,
                contradiction_matches,
                hierarchy,
            )
        ]

        final_state = _final_claim_state(
            target,
            support_matches,
            contradiction_matches,
            hierarchy,
        )
        contradiction_status = (
            ContradictionStatus.CONFLICTING
            if contradiction_matches and final_state == ClaimState.OPEN
            else ContradictionStatus.NONE
        )

        if supporting_evidence:
            governing_support = governing_evidence[0] if governing_evidence else supporting_evidence[0]
            source_role_level = governing_support.source_role_level
            jurisdiction = governing_support.jurisdiction
            support_directness = governing_support.support_directness
            citation_quality = governing_support.citation.citation_quality
            citations = [evidence.citation for evidence in governing_evidence] or [
                governing_support.citation
            ]
        else:
            source_role_level = target.required_source_role_level
            jurisdiction = "unknown"
            support_directness = SupportDirectness.INDIRECT
            citation_quality = CitationQuality.DOCUMENT_ONLY
            citations = []

        if final_state == ClaimState.CONFIRMED:
            rationale = "Direct high-rank support survived the hierarchy gate and is anchor-grounded or audit-confirmable."
        elif final_state == ClaimState.INTERPRETIVE:
            rationale = "Support exists, but it stays medium-rank, indirect, or document-only without confirmation-grade anchors."
        elif final_state == ClaimState.OPEN:
            rationale = "Same-rank admissible evidence conflicts closely enough that the structural tie-break leaves the claim unresolved."
        else:
            rationale = "No admissible support exists for the core claim after the inspected ranked search path."

        ledger_entries.append(
            LedgerEntry(
                claim_id=target.target_id,
                claim_text=target.claim_text,
                claim_type=target.claim_type,
                required_source_role_level=target.required_source_role_level,
                source_role_level=source_role_level,
                jurisdiction=jurisdiction,
                support_directness=support_directness,
                citation_quality=citation_quality,
                contradiction_status=contradiction_status,
                final_claim_state=final_state,
                citations=citations,
                supporting_evidence=supporting_evidence,
                contradicting_evidence=contradicting_evidence,
                governing_evidence=governing_evidence,
                rationale=rationale,
            )
        )

    return ledger_entries
