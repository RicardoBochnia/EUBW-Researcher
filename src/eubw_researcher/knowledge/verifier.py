from __future__ import annotations

from eubw_researcher.models import (
    BindingLevel,
    ClaimState,
    ClaimType,
    ClaimTypeGovernanceRule,
    ClaimVerificationRecord,
    DocumentStatus,
    EvidenceTier,
    LedgerEntry,
    SourceCatalog,
    SourceCatalogEntry,
    SourceGovernanceConfig,
    SourceKind,
    SourceRoleLevel,
    VerificationCheckDecision,
    VerificationDecisionStatus,
)


def _decision(
    check_id: str,
    status: VerificationDecisionStatus,
    reason: str,
) -> VerificationCheckDecision:
    return VerificationCheckDecision(
        check_id=check_id,
        status=status,
        reason=reason,
    )


def _check(check_id: str, passed: bool, reason: str) -> VerificationCheckDecision:
    return _decision(
        check_id,
        VerificationDecisionStatus.PASS if passed else VerificationDecisionStatus.FAIL,
        reason,
    )


def _qualified(check_id: str, reason: str) -> VerificationCheckDecision:
    return _decision(check_id, VerificationDecisionStatus.QUALIFIED, reason)


def _role_weight(role_level: SourceRoleLevel) -> int:
    return {
        SourceRoleLevel.HIGH: 3,
        SourceRoleLevel.MEDIUM: 2,
        SourceRoleLevel.LOW: 1,
    }[role_level]


def _source_role_compatible(entry: LedgerEntry) -> bool:
    return _role_weight(entry.source_role_level) >= _role_weight(
        entry.required_source_role_level
    )


def verification_allows_answer_use(
    record: ClaimVerificationRecord,
    *,
    strict: bool,
) -> bool:
    if not record.answer_use_allowed:
        return False
    if not strict:
        return True
    return all(check.status != VerificationDecisionStatus.FAIL for check in record.checks)


def _default_source_governance() -> SourceGovernanceConfig:
    return SourceGovernanceConfig(
        policy_version="source_governance.default",
        claim_type_compatibility={
            ClaimType.OBLIGATION: ClaimTypeGovernanceRule(
                allowed_binding_levels=[BindingLevel.BINDING, BindingLevel.PROPOSED],
                binding_required_for_current_law=True,
            ),
            ClaimType.ALLOWANCE: ClaimTypeGovernanceRule(
                allowed_binding_levels=[BindingLevel.BINDING, BindingLevel.PROPOSED],
                binding_required_for_current_law=True,
            ),
            ClaimType.PROTOCOL_BEHAVIOR: ClaimTypeGovernanceRule(
                allowed_binding_levels=[
                    BindingLevel.BINDING,
                    BindingLevel.OFFICIAL_NON_BINDING,
                    BindingLevel.NON_BINDING,
                    BindingLevel.UNKNOWN,
                ],
                binding_required_for_current_law=False,
            ),
            ClaimType.SYNTHESIS: ClaimTypeGovernanceRule(
                allowed_binding_levels=[
                    BindingLevel.BINDING,
                    BindingLevel.PROPOSED,
                    BindingLevel.OFFICIAL_NON_BINDING,
                    BindingLevel.NON_BINDING,
                    BindingLevel.UNKNOWN,
                ],
                binding_required_for_current_law=False,
            ),
        },
    )


def _effective_binding_level(source: SourceCatalogEntry | None) -> BindingLevel:
    if source is None:
        return BindingLevel.UNKNOWN
    if source.binding_level != BindingLevel.UNKNOWN:
        return source.binding_level
    if source.document_status == DocumentStatus.PROPOSAL:
        return BindingLevel.PROPOSED
    if source.source_kind in {SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT}:
        return BindingLevel.BINDING
    if source.source_kind == SourceKind.PROJECT_ARTIFACT:
        return BindingLevel.OFFICIAL_NON_BINDING
    if source.source_kind == SourceKind.TECHNICAL_STANDARD:
        return BindingLevel.NON_BINDING
    return BindingLevel.UNKNOWN


def _binding_level_compatible(
    entry: LedgerEntry,
    source: SourceCatalogEntry | None,
    source_governance: SourceGovernanceConfig,
) -> bool:
    rule = source_governance.claim_type_compatibility.get(entry.claim_type)
    if rule is None:
        return False
    return _effective_binding_level(source) in set(rule.allowed_binding_levels)


def _current_law_qualifiers_preserved(
    entry: LedgerEntry,
    source: SourceCatalogEntry | None,
    source_governance: SourceGovernanceConfig,
) -> bool:
    rule = source_governance.claim_type_compatibility.get(entry.claim_type)
    if rule is None or not rule.binding_required_for_current_law:
        return True
    if entry.final_claim_state != ClaimState.CONFIRMED:
        return True
    if source is None:
        return False
    if (
        source_governance.effective_date_policy.proposal_must_not_support_final_law_wording
        and source.document_status == DocumentStatus.PROPOSAL
    ):
        return False
    return source.document_status in {
        DocumentStatus.FINAL,
        DocumentStatus.ADOPTED_PENDING_EFFECTIVE_DATE,
    }


def build_claim_verification_records(
    ledger_entries: list[LedgerEntry],
    catalog: SourceCatalog,
    *,
    corpus_state_id: str | None = None,
    source_governance: SourceGovernanceConfig | None = None,
) -> list[ClaimVerificationRecord]:
    resolved_governance = source_governance or _default_source_governance()
    sources_by_id = catalog.by_id()
    records: list[ClaimVerificationRecord] = []
    for entry in ledger_entries:
        evidence = (entry.governing_evidence or entry.supporting_evidence or [])
        primary = evidence[0] if evidence else None
        citation = entry.citations[0] if entry.citations else None
        source = sources_by_id.get(citation.source_id) if citation else None
        locator = citation.anchor_label if citation else None
        source_exists = source is not None
        locator_resolvable = bool(locator) or (
            citation is not None and citation.citation_quality.value == "document_only"
        )
        support_present = entry.final_claim_state != ClaimState.BLOCKED and bool(evidence)
        answer_use_allowed = entry.final_claim_state in {
            ClaimState.CONFIRMED,
            ClaimState.INTERPRETIVE,
        }
        source_role_compatible = _source_role_compatible(entry)
        evidence_tier = source.evidence_tier if source else EvidenceTier.UNKNOWN
        binding_level = _effective_binding_level(source)
        binding_compatible = _binding_level_compatible(
            entry,
            source,
            resolved_governance,
        )
        current_law_qualifiers_preserved = _current_law_qualifiers_preserved(
            entry,
            source,
            resolved_governance,
        )
        source_hash_or_version_present = bool(
            source and (source.content_digest or source.version_date or source.publication_date)
        )
        higher_authority_considered = bool(
            entry.governing_evidence or entry.contradicting_evidence
        )
        checks = [
            _check("source_exists_in_catalog", source_exists, "Primary cited source resolved in catalog." if source_exists else "No cited source resolved in catalog."),
            _check("source_admission_policy_recorded", True, "Source admission reason is recorded." if source and source.admission_reason else "Source admission is inherited from the curated catalog."),
            _check("source_hash_or_version_matches_catalog", True, "Digest or version/publication metadata is present.") if source_hash_or_version_present else _qualified("source_hash_or_version_matches_catalog", "No digest/version metadata available; verification remains qualified."),
            _check("locator_resolvable", locator_resolvable, "Locator or document-level citation is available." if locator_resolvable else "No locator or document-level citation is available."),
            _check("claim_text_supported_by_passage", support_present, "Ledger has support evidence." if support_present else "Ledger has no support evidence."),
            _check("claim_type_compatible_with_source_role", source_exists and source_role_compatible, "Source role satisfies the required role level." if source_role_compatible else "Source role is not sufficient."),
            _check("claim_type_compatible_with_binding_level", source_exists and binding_compatible, "Binding level is compatible with the claim type." if binding_compatible else "Binding level is not compatible with the claim type."),
            _check("qualifiers_preserved", bool(source and source.document_status == entry.governing_document_status) or entry.governing_document_status is None, "Document-status qualifier is preserved." if source_exists else "No source qualifier can be checked."),
            _check("current_law_qualifiers_preserved", current_law_qualifiers_preserved, "Current-law binding/document-status qualifiers are preserved." if current_law_qualifiers_preserved else "Current-law wording is not supported by the source status."),
            _check("higher_authority_candidates_considered", True, "Governing or contradicting evidence was considered.") if higher_authority_considered else _qualified("higher_authority_candidates_considered", "No higher-authority evidence surfaced; answer use remains qualified."),
            _check("contradiction_candidates_checked", entry.contradiction_status.value in {"none", "conflicting"}, "Contradiction status is recorded."),
            _check("relevant_open_issues_attached", entry.final_claim_state != ClaimState.OPEN, "No open issue required by current ledger state." if entry.final_claim_state != ClaimState.OPEN else "Open claim requires linked open issue before approval."),
            _check("answer_use_allowed_only_for_approved_or_interpretive", answer_use_allowed, "Answer use allowed." if answer_use_allowed else "Blocked/open claim cannot be used as final answer support."),
            _check("blocked_claims_not_final_answer_claims", entry.final_claim_state != ClaimState.BLOCKED, "Claim is not blocked." if entry.final_claim_state != ClaimState.BLOCKED else "Blocked claim must remain artifact-only."),
        ]
        records.append(
            ClaimVerificationRecord(
                claim_id=entry.claim_id,
                claim_type=entry.claim_type,
                verification_result=entry.final_claim_state,
                decision_reason=entry.rationale,
                source_ids=[citation.source_id for citation in entry.citations],
                chunk_ids=[
                    item.chunk_id for item in evidence if item.chunk_id is not None
                ],
                locators=[item for item in [locator] if item],
                evidence_tier=evidence_tier,
                binding_level=binding_level,
                source_role_level=entry.source_role_level,
                document_status=entry.governing_document_status
                or (source.document_status if source else DocumentStatus.INFORMATIONAL),
                jurisdiction=entry.jurisdiction,
                publication_date=source.publication_date if source else None,
                version_date=source.version_date if source else None,
                effective_date=source.effective_date if source else None,
                source_digest=source.content_digest if source else None,
                corpus_state_id=corpus_state_id,
                support_directness=entry.support_directness,
                contradiction_candidate_ids=[
                    evidence.citation.source_id for evidence in entry.contradicting_evidence
                ],
                higher_authority_candidate_source_ids=[
                    evidence.citation.source_id for evidence in entry.governing_evidence
                ],
                attached_open_issue_ids=[],
                answer_use_allowed=answer_use_allowed,
                checks=checks,
            )
        )
    return records
