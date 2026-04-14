from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SourceRoleLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceKind(str, Enum):
    REGULATION = "regulation"
    IMPLEMENTING_ACT = "implementing_act"
    TECHNICAL_STANDARD = "technical_standard"
    PROJECT_ARTIFACT = "project_artifact"
    SCIENTIFIC_LITERATURE = "scientific_literature"
    COMMENTARY = "commentary"
    NATIONAL_IMPLEMENTATION = "national_implementation"


class SourceOrigin(str, Enum):
    LOCAL = "local"
    WEB = "web"


class ClaimType(str, Enum):
    OBLIGATION = "obligation"
    ALLOWANCE = "allowance"
    PROTOCOL_BEHAVIOR = "protocol_behavior"
    SYNTHESIS = "synthesis"


class SupportDirectness(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"


class CitationQuality(str, Enum):
    ANCHOR_GROUNDED = "anchor_grounded"
    DOCUMENT_ONLY = "document_only"


class DocumentStatus(str, Enum):
    FINAL = "final"
    ADOPTED_PENDING_EFFECTIVE_DATE = "adopted_pending_effective_date"
    DRAFT = "draft"
    PROPOSAL = "proposal"
    INFORMATIONAL = "informational"


class AnchorQuality(str, Enum):
    STRONG = "strong"
    WEAK = "weak"
    MISSING = "missing"


class ContradictionStatus(str, Enum):
    NONE = "none"
    CONFLICTING = "conflicting"


class ClaimState(str, Enum):
    CONFIRMED = "confirmed"
    INTERPRETIVE = "interpretive"
    OPEN = "open"
    BLOCKED = "blocked"


class NormalizationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class SourceCatalogEntry:
    source_id: str
    title: str
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    jurisdiction: str
    publication_status: Optional[str]
    publication_date: Optional[str]
    local_path: Optional[Path]
    canonical_url: Optional[str]
    document_status: DocumentStatus = DocumentStatus.FINAL
    source_origin: SourceOrigin = SourceOrigin.LOCAL
    anchorability_hints: List[str] = field(default_factory=list)
    admission_reason: Optional[str] = None
    source_family_id: Optional[str] = None


@dataclass
class SourceCatalog:
    entries: List[SourceCatalogEntry]

    def by_id(self) -> Dict[str, SourceCatalogEntry]:
        return {entry.source_id: entry for entry in self.entries}


@dataclass
class AnchorAudit:
    expected_anchorable: bool
    content_retrievable: bool
    parser_or_structure_limitation: bool
    structure_poor: bool
    audit_note: str

    def is_document_only_confirmable(self) -> bool:
        return (
            self.expected_anchorable
            and self.content_retrievable
            and self.parser_or_structure_limitation
            and not self.structure_poor
        )


@dataclass
class Citation:
    source_id: str
    document_title: str
    source_role_level: SourceRoleLevel
    source_kind: SourceKind
    jurisdiction: str
    citation_quality: CitationQuality
    document_path: Optional[Path]
    canonical_url: Optional[str]
    document_status: DocumentStatus = DocumentStatus.FINAL
    source_origin: SourceOrigin = SourceOrigin.LOCAL
    anchor_label: Optional[str] = None
    structure_poor: bool = False
    anchor_audit_note: Optional[str] = None

    def render(self) -> str:
        role_label = self.source_role_level.value
        origin_label = self.source_origin.value
        if self.anchor_label:
            return f"{self.document_title}, {self.anchor_label} [{origin_label}/{role_label}]"
        if self.structure_poor:
            return f"{self.document_title}, full document citation only [{origin_label}/{role_label}]"
        return f"{self.document_title}, document citation only [{origin_label}/{role_label}]"


@dataclass
class SourceChunk:
    source_id: str
    chunk_id: str
    title: str
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    source_origin: SourceOrigin
    jurisdiction: str
    text: str
    citation: Citation
    document_status: DocumentStatus = DocumentStatus.FINAL
    technical_anchor_failure: bool = False
    anchor_quality: AnchorQuality = AnchorQuality.MISSING
    extracted_anchor_label: Optional[str] = None
    anchor_audit: Optional[AnchorAudit] = None

    @property
    def citation_quality(self) -> CitationQuality:
        return self.citation.citation_quality


@dataclass
class SourceDocument:
    entry: SourceCatalogEntry
    text: str
    chunks: List[SourceChunk]
    anchor_quality: AnchorQuality
    structure_poor: bool
    technical_anchor_failure: bool
    anchor_audit: Optional[AnchorAudit]


@dataclass
class IngestionReportEntry:
    source_id: str
    title: str
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    jurisdiction: str
    anchor_quality: AnchorQuality
    structure_poor: bool
    citation_quality: CitationQuality
    technical_anchor_failure: bool
    anchor_audit_note: str
    chunk_count: int
    local_path: Optional[Path]
    document_status: DocumentStatus = DocumentStatus.FINAL
    normalization_status: NormalizationStatus = NormalizationStatus.SUCCESS
    normalization_format: Optional[str] = None
    normalization_note: Optional[str] = None


@dataclass
class IngestionBundle:
    catalog: SourceCatalog
    documents: List[SourceDocument]
    report: List[IngestionReportEntry]


@dataclass
class HierarchyRule:
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    rank: int


@dataclass
class DiscoveryEntrypoint:
    entrypoint_id: str
    url_template: str
    strategy: str

    def __post_init__(self) -> None:
        if self.strategy not in {"index_crawl", "official_search"}:
            raise ValueError(
                f"Unsupported discovery strategy '{self.strategy}' for entrypoint '{self.entrypoint_id}'."
            )
        if self.strategy == "official_search" and "{query}" not in self.url_template:
            raise ValueError(
                f"official_search entrypoint '{self.entrypoint_id}' must contain {{query}} in url_template."
            )


@dataclass
class WebDomainPolicy:
    domain: str
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    jurisdiction: str
    seed_urls: List[str] = field(default_factory=list)
    discovery_entrypoints: List[DiscoveryEntrypoint] = field(default_factory=list)
    crawl_path_prefixes: List[str] = field(default_factory=list)
    admission_path_prefixes: List[str] = field(default_factory=list)
    blocked_url_keywords: List[str] = field(default_factory=list)
    allowed_cross_domain_domains: List[str] = field(default_factory=list)
    allowed_intent_types: List[str] = field(default_factory=list)
    policy_id: Optional[str] = None
    discovery_urls: List[str] = field(default_factory=list)
    allowed_path_prefixes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.policy_id:
            self.policy_id = f"{self.domain}:{self.source_kind.value}"
        if not self.discovery_entrypoints and self.discovery_urls:
            self.discovery_entrypoints = [
                DiscoveryEntrypoint(
                    entrypoint_id=f"{self.policy_id}:legacy:{index + 1}",
                    url_template=url,
                    strategy="index_crawl",
                )
                for index, url in enumerate(self.discovery_urls)
            ]
        if not self.crawl_path_prefixes and self.allowed_path_prefixes:
            self.crawl_path_prefixes = list(self.allowed_path_prefixes)
        if not self.admission_path_prefixes and self.allowed_path_prefixes:
            self.admission_path_prefixes = list(self.allowed_path_prefixes)


@dataclass
class SourceHierarchyConfig:
    rules: List[HierarchyRule]
    default_eu_first: bool = True

    def rank_for(self, source_kind: SourceKind) -> int:
        for rule in self.rules:
            if rule.source_kind == source_kind:
                return rule.rank
        return 999

    def role_for(self, source_kind: SourceKind) -> SourceRoleLevel:
        for rule in self.rules:
            if rule.source_kind == source_kind:
                return rule.source_role_level
        return SourceRoleLevel.LOW


@dataclass
class WebAllowlistConfig:
    allowed_domains: List[str]
    domain_policies: List[WebDomainPolicy] = field(default_factory=list)

    def is_allowed(self, domain: str) -> bool:
        return domain in self.allowed_domains

    def policy_for_domain(self, domain: str) -> Optional[WebDomainPolicy]:
        policies = self.policies_for_domain(domain)
        return policies[0] if policies else None

    def policies_for_domain(self, domain: str) -> List[WebDomainPolicy]:
        return [policy for policy in self.domain_policies if policy.domain == domain]

    def policy_for_domain_and_kind(
        self,
        domain: str,
        source_kind: SourceKind,
    ) -> Optional[WebDomainPolicy]:
        for policy in self.domain_policies:
            if policy.domain == domain and policy.source_kind == source_kind:
                return policy
        return None

    def seed_urls_for_kind(
        self,
        source_kind: SourceKind,
        *,
        intent_type: Optional[str] = None,
    ) -> List[str]:
        urls: List[str] = []
        for policy in self.domain_policies:
            if policy.source_kind != source_kind:
                continue
            if policy.allowed_intent_types and intent_type not in policy.allowed_intent_types:
                continue
            urls.extend(policy.seed_urls)
        return urls

    def discovery_entrypoints_for_kind(
        self,
        source_kind: SourceKind,
        *,
        intent_type: Optional[str] = None,
    ) -> List[DiscoveryEntrypoint]:
        entrypoints: List[DiscoveryEntrypoint] = []
        for policy in self.domain_policies:
            if policy.source_kind != source_kind:
                continue
            if policy.allowed_intent_types and intent_type not in policy.allowed_intent_types:
                continue
            entrypoints.extend(policy.discovery_entrypoints)
        return entrypoints

    def discovery_urls_for_kind(
        self,
        source_kind: SourceKind,
        *,
        intent_type: Optional[str] = None,
    ) -> List[str]:
        urls: List[str] = []
        for policy in self.domain_policies:
            if policy.source_kind != source_kind:
                continue
            if policy.allowed_intent_types and intent_type not in policy.allowed_intent_types:
                continue
            if policy.discovery_urls:
                urls.extend(policy.discovery_urls)
            else:
                urls.extend(entrypoint.url_template for entrypoint in policy.discovery_entrypoints)
        return urls


@dataclass
class ArchiveSourceSelection:
    archive_source_id: str
    source_id: str
    title: str
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    jurisdiction: str
    publication_status: Optional[str]
    publication_date: Optional[str]
    document_status: DocumentStatus = DocumentStatus.FINAL
    source_origin: SourceOrigin = SourceOrigin.LOCAL
    anchorability_hints: List[str] = field(default_factory=list)
    admission_reason: Optional[str] = None
    source_family_id: Optional[str] = None
    successor_candidate_urls: List[str] = field(default_factory=list)


@dataclass
class ArchiveCorpusConfig:
    archive_root: Path
    archive_catalog: Path
    sources: List[ArchiveSourceSelection]


@dataclass
class ArchiveRefreshResult:
    archive_source_id: str
    source_id: str
    title: str
    canonical_url: Optional[str]
    local_path: Optional[str]
    checked_at: str
    status: str
    reason: str
    local_exists: bool
    local_content_digest: Optional[str] = None
    remote_content_digest: Optional[str] = None
    remote_etag: Optional[str] = None
    remote_last_modified: Optional[str] = None
    content_type: Optional[str] = None
    stage_path: Optional[str] = None
    applied: bool = False
    checked_successor_candidate_urls: List[str] = field(default_factory=list)
    matching_successor_candidate_urls: List[str] = field(default_factory=list)
    selected_successor_candidate_url: Optional[str] = None


@dataclass
class ArchiveRefreshReport:
    config_path: str
    archive_catalog_path: str
    stage_root: str
    generated_at: str
    apply_updates: bool
    checked_sources: int
    refreshable_sources: int
    current_sources: int
    changed_sources: int
    staged_sources: int
    applied_sources: int
    skipped_sources: int
    failed_sources: int
    results: List[ArchiveRefreshResult] = field(default_factory=list)


@dataclass
class RuntimeConfig:
    logging_level: str
    retrieval_top_k: int
    lexical_weight: float
    semantic_weight: float
    min_combined_score: float
    semantic_expansions: Dict[str, List[str]]
    web_timeout_seconds: int
    web_discovery_max_depth: int
    web_discovery_max_pages: int
    web_discovery_max_candidates_per_kind: int
    web_max_admitted_per_domain: int
    web_max_admitted_per_run: int
    local_retrieval_backend: str = "sqlite_fts"
    local_index_candidate_pool: int = 5

    def __post_init__(self) -> None:
        if self.local_retrieval_backend not in {"scan", "sqlite_fts"}:
            raise ValueError(
                "Unsupported local_retrieval_backend: "
                f"{self.local_retrieval_backend}"
            )
        if self.local_index_candidate_pool < self.retrieval_top_k:
            raise ValueError(
                "local_index_candidate_pool must be >= retrieval_top_k: "
                f"{self.local_index_candidate_pool} < {self.retrieval_top_k}"
            )


@dataclass
class EvaluationScenario:
    scenario_id: str
    question: str
    expectation: str
    required_intent_type: Optional[str] = None
    required_states: List[ClaimState] = field(default_factory=list)
    allowed_states: List[ClaimState] = field(default_factory=list)
    required_sources: List[str] = field(default_factory=list)
    forbidden_sources: List[str] = field(default_factory=list)
    required_answer_substrings: List[str] = field(default_factory=list)
    forbidden_answer_substrings: List[str] = field(default_factory=list)
    required_gap_reason_substrings: List[str] = field(default_factory=list)
    required_gap_actions: List[str] = field(default_factory=list)
    required_retrieval_prefix_kinds: List[SourceKind] = field(default_factory=list)
    required_clarification_substring: Optional[str] = None
    required_web_discovery_count: int = 0
    required_web_discovered_link_count: int = 0
    required_web_fetch_count: int = 0
    required_web_domains: List[str] = field(default_factory=list)
    require_provisional_grouping: bool = False
    require_manual_review_accept: bool = False
    spawned_validator_gate_eligible: bool = False
    spawned_validator_release_gate: bool = False
    min_gap_records: int = 0
    min_ledger_entries: int = 1


@dataclass
class RealQuestionPackQuestion:
    question_id: str
    title: str
    question: str
    review_focus: str
    expected_intent_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    review_prompts: List[str] = field(default_factory=list)
    seed_from_scenario_id: Optional[str] = None


@dataclass
class RealQuestionPack:
    questions: List[RealQuestionPackQuestion]


@dataclass
class ClaimTarget:
    target_id: str
    claim_text: str
    claim_type: ClaimType
    required_source_role_level: SourceRoleLevel
    preferred_kinds: List[SourceKind]
    scope_terms: List[str]
    primary_terms: List[str]
    support_groups: List[List[str]]
    contradiction_groups: List[List[str]]
    grouping_label: Optional[str] = None


@dataclass(frozen=True)
class TerminologyAlias:
    term: str
    context_aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TerminologyMapping:
    canonical_term: str
    alias_rules: tuple[TerminologyAlias, ...]
    context_aliases: tuple[str, ...] = field(default_factory=tuple)

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(alias.term for alias in self.alias_rules)


@dataclass(frozen=True)
class TerminologyConfig:
    mappings: tuple[TerminologyMapping, ...]
    generator_owned: bool = False
    policy_version: Optional[str] = None
    archive_catalog_path: Optional[str] = None
    curated_catalog_path: Optional[str] = None


@dataclass(frozen=True)
class AppliedTermNormalization:
    source_term: str
    canonical_term: str


@dataclass
class QueryIntent:
    question: str
    intent_type: str
    eu_first: bool
    claim_targets: List[ClaimTarget]
    preferred_kinds: List[SourceKind]
    clarification_note: Optional[str] = None
    answer_pattern: Optional[str] = None
    undefined_terms: List[str] = field(default_factory=list)


@dataclass
class RetrievalPlanStep:
    step_id: str
    required_kind: SourceKind
    required_source_role_level: SourceRoleLevel
    inspection_depth: int
    reason: str


@dataclass
class RetrievalTargetQuery:
    target_id: str
    raw_query: str
    normalized_query: str
    applied_term_normalizations: List[AppliedTermNormalization] = field(default_factory=list)


@dataclass
class RetrievalPlan:
    question: str
    normalized_question: str
    question_term_normalizations: List[AppliedTermNormalization] = field(default_factory=list)
    target_queries: List[RetrievalTargetQuery] = field(default_factory=list)
    steps: List[RetrievalPlanStep] = field(default_factory=list)
    local_retrieval_backend: str = "sqlite_fts"
    local_index_candidate_pool: int = 0
    local_index_cache_status: Optional[str] = None
    local_backend_fallback_used: bool = False


@dataclass
class RetrievalCandidate:
    chunk: SourceChunk
    lexical_score: float
    semantic_score: float
    combined_score: float
    meets_threshold: bool = True


@dataclass
class GapRecord:
    sub_question: str
    required_source_role_level: SourceRoleLevel
    local_source_layers_searched: List[str]
    retrieval_methods_used: List[str]
    candidate_sources_inspected: List[str]
    reason_local_evidence_insufficient: str
    next_allowed_action: str
    web_source_kinds_considered: List[SourceKind] = field(default_factory=list)
    web_discovery_urls_attempted: List[str] = field(default_factory=list)
    web_fetch_urls_attempted: List[str] = field(default_factory=list)


@dataclass
class WebFetchRecord:
    sub_question: str
    canonical_url: str
    domain: str
    allowed: bool
    source_kind: Optional[SourceKind]
    source_role_level: Optional[SourceRoleLevel]
    jurisdiction: Optional[str]
    retrieval_timestamp: str
    citation_quality: Optional[CitationQuality]
    metadata_complete: bool
    reason: str
    record_type: str = "fetch"
    discovered_from: Optional[str] = None
    content_type: Optional[str] = None
    normalization_status: Optional[NormalizationStatus] = None
    content_digest: Optional[str] = None
    provenance_record: Optional[str] = None
    policy_id: Optional[str] = None
    entrypoint_id: Optional[str] = None
    discovery_strategy: Optional[str] = None
    admission_rule: Optional[str] = None
    discovery_query: Optional[str] = None
    source_id: Optional[str] = None


@dataclass
class LedgerEvidence:
    citation: Citation
    source_role_level: SourceRoleLevel
    source_kind: SourceKind
    source_kind_rank: int
    source_origin: SourceOrigin
    jurisdiction: str
    support_directness: SupportDirectness
    term_overlap: int
    scope_overlap: int
    on_point_score: int
    admissible: bool
    citation_quality: CitationQuality
    document_status: DocumentStatus = DocumentStatus.FINAL
    anchor_audit_note: Optional[str] = None


@dataclass
class EvidenceMatch:
    claim_target: ClaimTarget
    candidate: RetrievalCandidate
    support_directness: SupportDirectness
    contradiction: bool
    term_overlap: int
    scope_overlap: int
    support_signal_count: int


@dataclass
class LedgerEntry:
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    required_source_role_level: SourceRoleLevel
    source_role_level: SourceRoleLevel
    jurisdiction: str
    support_directness: SupportDirectness
    citation_quality: CitationQuality
    contradiction_status: ContradictionStatus
    final_claim_state: ClaimState
    citations: List[Citation]
    supporting_evidence: List[LedgerEvidence]
    contradicting_evidence: List[LedgerEvidence]
    governing_evidence: List[LedgerEvidence]
    rationale: str
    governing_document_status: Optional[DocumentStatus] = None
    source_document_statuses: List[DocumentStatus] = field(default_factory=list)


@dataclass
class ProvisionalGroup:
    label: str
    claim_ids: List[str]
    source_ids: List[str]
    provisional: bool = True


@dataclass
class ManualReviewCheck:
    check_id: str
    status: str
    evidence: str


@dataclass
class ManualReviewArtifact:
    question: str
    scenario_id: Optional[str]
    artifact_scope: str
    filled: bool
    checks: List[ManualReviewCheck]
    summary: str
    artifact_type: str = "automated_review_prefill"
    human_reviewed: bool = False


@dataclass
class ApprovedFetchedSourceEvidence:
    source_id: str
    canonical_url: str
    content_type: str
    content_digest: str
    provenance_record: str
    normalization_status: NormalizationStatus
    citation_quality: CitationQuality
    discovered_from: Optional[str] = None
    retrieval_timestamp: Optional[str] = None
    policy_id: Optional[str] = None
    entrypoint_id: Optional[str] = None
    discovery_strategy: Optional[str] = None
    admission_rule: Optional[str] = None
    discovery_query: Optional[str] = None


@dataclass
class ManualReviewReport:
    scenario_id: Optional[str]
    corpus_selection: str
    corpus_state_id: Optional[str]
    reviewer_name: str
    review_date: str
    correctness_verdict: str
    usefulness_verdict: str
    source_role_hierarchy_verdict: str
    uncertainty_handling_verdict: str
    discovery_gap_handling_verdict: str
    open_follow_ups: List[str]
    final_judgment: str
    source_bound_verdict: str = "not_assessed"
    pinpoint_traceability_verdict: str = "not_assessed"
    answer_evidence_alignment_verdict: str = "not_assessed"
    product_output_self_sufficiency_verdict: str = "not_assessed"
    approved_fetched_source_evidence: List[ApprovedFetchedSourceEvidence] = field(default_factory=list)
    germany_dependency_summary: Dict[str, List[str]] = field(default_factory=dict)
    report_type: str = "automated_review_prefill"
    human_reviewed: bool = False


@dataclass
class FacetCoverageFacet:
    facet_id: str
    addressed: bool
    evidence: List[str] = field(default_factory=list)


@dataclass
class FacetCoverageReport:
    question: str
    intent_type: str
    facets: List[FacetCoverageFacet] = field(default_factory=list)

    def by_id(self) -> Dict[str, FacetCoverageFacet]:
        return {facet.facet_id: facet for facet in self.facets}

    def all_addressed(self) -> bool:
        return all(facet.addressed for facet in self.facets)


@dataclass
class PinpointEvidenceRecord:
    answer_claim_id: str
    answer_section: str
    answer_claim_text: str
    source_id: str
    source_role_level: SourceRoleLevel
    citation_quality: CitationQuality
    locator_type: str
    locator_value: str
    locator_precision: str
    document_path: Optional[Path]
    canonical_url: Optional[str]
    document_status: DocumentStatus = DocumentStatus.FINAL
    limitation_note: Optional[str] = None


@dataclass
class PinpointEvidenceReport:
    question: str
    intent_type: str
    records: List[PinpointEvidenceRecord] = field(default_factory=list)
    all_cited_evidence_mapped: bool = True
    missing_citation_claim_ids: List[str] = field(default_factory=list)


@dataclass
class AnswerAlignmentRecord:
    answer_claim_id: str
    answer_section: str
    wording_category: str
    claim_ids: List[str]
    claim_states: List[ClaimState]
    cited_source_ids: List[str]
    cited_source_roles: List[SourceRoleLevel]
    evidence_partition_labels: List[str] = field(default_factory=list)
    alignment_status: str = "pass"
    notes: List[str] = field(default_factory=list)


@dataclass
class AnswerAlignmentReport:
    question: str
    intent_type: str
    records: List[AnswerAlignmentRecord] = field(default_factory=list)
    blocking_violations: List[str] = field(default_factory=list)

    def has_blocking_violations(self) -> bool:
        return bool(self.blocking_violations)


@dataclass
class BlindValidationRawRead:
    source_id: str
    document_path: Optional[Path]
    purpose: str
    classification: str


@dataclass
class SpawnedValidatorResult:
    passed: bool
    context_inherited: bool
    artifacts_used: List[str]
    raw_document_reads: List[BlindValidationRawRead] = field(default_factory=list)
    raw_document_dependency: str = "none"
    product_output_self_sufficient: bool = False
    summary: str = ""
    validator_answer: str = ""
    notes: Optional[str] = None
    validator_command: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BlindValidationReport:
    question: str
    intent_type: str
    validation_mode: str
    artifacts_used: List[str]
    raw_document_reads: List[BlindValidationRawRead] = field(default_factory=list)
    raw_document_dependency: str = "none"
    structural_passed: bool = False
    product_output_self_sufficient: bool = False
    passed: bool = False
    summary: str = ""
    missing_facets: List[str] = field(default_factory=list)
    spawned_validator: Optional[SpawnedValidatorResult] = None


@dataclass
class CorpusCoverageFamily:
    family_id: str
    minimum_count: int
    admitted_count: int
    admitted_source_ids: List[str]
    missing: bool


@dataclass
class CorpusCoverageReport:
    catalog_path: str
    corpus_state_id: str
    generation_timestamp: str
    admitted_source_counts_by_kind: Dict[str, int]
    families: List[CorpusCoverageFamily]
    passed: bool


@dataclass
class AnswerResult:
    question: str
    query_intent: QueryIntent
    retrieval_plan: RetrievalPlan
    gap_records: List[GapRecord]
    web_fetch_records: List[WebFetchRecord]
    ingestion_report: List[IngestionReportEntry]
    ledger_entries: List[LedgerEntry]
    approved_entries: List[LedgerEntry]
    rendered_answer: str
    provisional_grouping: List[ProvisionalGroup] = field(default_factory=list)
    manual_review: Optional[ManualReviewArtifact] = None
    facet_coverage_report: Optional[FacetCoverageReport] = None
    pinpoint_evidence_report: Optional[PinpointEvidenceReport] = None
    answer_alignment_report: Optional[AnswerAlignmentReport] = None
    blind_validation_report: Optional[BlindValidationReport] = None
    corpus_coverage_report: Optional[CorpusCoverageReport] = None


@dataclass
class ScenarioVerdict:
    scenario_id: str
    passed: bool
    checks: List[str]


@dataclass
class RealQuestionPackQuestionRunSummary:
    question_id: str
    title: str
    review_focus: str
    expected_intent_type: Optional[str]
    linked_scenario_id: Optional[str]
    tags: List[str]
    output_dir: str
    artifacts_present: List[str]
    missing_artifacts: List[str]
    has_missing_artifacts: bool
    intent_type: str
    approved_entry_count: int
    gap_record_count: int
    discovery_record_count: int
    web_fetch_count: int
    used_official_web_discovery: bool
    local_corpus_only: bool
    final_judgment: str
    usefulness_verdict: str
    source_bound_verdict: str
    pinpoint_traceability_verdict: str
    product_output_self_sufficiency_verdict: str
    review_complete: bool = False


@dataclass
class RealQuestionPackRunTriageSummary:
    total_questions: int
    accepted_question_ids: List[str] = field(default_factory=list)
    rejected_question_ids: List[str] = field(default_factory=list)
    question_ids_with_discovery: List[str] = field(default_factory=list)
    question_ids_with_fetch: List[str] = field(default_factory=list)
    question_ids_with_missing_artifacts: List[str] = field(default_factory=list)


@dataclass
class RealQuestionPackRunManifest:
    run_id: str
    run_timestamp: str
    pack_path: str
    pack_digest: str
    selected_question_ids: List[str]
    catalog_path: str
    corpus_state_id: str
    runtime_contract_version: str
    runtime_config_path: Optional[str]
    runtime_config_digest: Optional[str]
    local_retrieval_backend: Optional[str]
    entrypoint: str
    git_commit: Optional[str]
    git_branch: Optional[str]
    git_dirty: bool
    repo_local_artifacts_written: bool
    run_triage_summary: RealQuestionPackRunTriageSummary
    question_runs: List[RealQuestionPackQuestionRunSummary] = field(default_factory=list)


@dataclass
class EvalScenarioRunSummary:
    scenario_id: str
    passed: bool
    require_manual_review_accept: bool
    manual_review_accept_satisfied: Optional[bool]
    final_judgment: str
    output_dir: str
    verdict_path: str
    manual_review_report_path: str


@dataclass
class EvalRunManifest:
    run_timestamp: str
    scenario_config_path: str
    catalog_path: str
    corpus_state_id: str
    runtime_contract_version: str
    runtime_config_path: Optional[str]
    runtime_config_digest: Optional[str]
    local_retrieval_backend: Optional[str]
    binding_gate_surface: str
    coverage_gate_passed: Optional[bool]
    overall_passed: bool
    coverage_report_path: Optional[str]
    coverage_summary_path: Optional[str]
    git_commit: Optional[str]
    git_branch: Optional[str]
    git_dirty: bool
    scenario_runs: List[EvalScenarioRunSummary] = field(default_factory=list)


@dataclass
class SpawnedValidatorGateScenarioRunSummary:
    scenario_id: str
    deterministic_passed: bool
    spawned_validator_invoked: bool
    spawned_validator_contract_passed: Optional[bool]
    spawned_validator_passed: Optional[bool]
    final_passed: bool
    output_dir: str
    verdict_path: str
    blind_validation_report_path: str
    spawned_validator_request_path: Optional[str] = None
    spawned_validator_result_path: Optional[str] = None


@dataclass
class SpawnedValidatorGateManifest:
    run_timestamp: str
    scenario_config_path: str
    catalog_path: str
    corpus_state_id: str
    runtime_contract_version: str
    runtime_config_path: Optional[str]
    runtime_config_digest: Optional[str]
    local_retrieval_backend: Optional[str]
    gate_target: str
    validator_command: str
    overall_passed: bool
    scenario_runs: List[SpawnedValidatorGateScenarioRunSummary] = field(default_factory=list)


@dataclass
class ValidatedBindingReviewSample:
    scenario_id: str
    manual_review_accept_required: bool
    manual_review_accept_satisfied: Optional[bool]
    verdict_path: str
    manual_review_report_path: str


@dataclass
class ValidatedCurrentStateReport:
    report_version: str
    binding_gate_surface: str
    release_validation_mode: str
    validated: bool
    catalog_path: str
    corpus_state_id: str
    runtime_contract_version: str
    runtime_config_path: Optional[str]
    runtime_config_digest: Optional[str]
    local_retrieval_backend: Optional[str]
    git_commit: Optional[str]
    git_branch: Optional[str]
    git_dirty: Optional[bool]
    total_sources: int
    counts_by_kind: Dict[str, int]
    counts_by_role_level: Dict[str, int]
    coverage_gate_passed: Optional[bool]
    eval_gate_passed: bool
    current_catalog_matches_eval_gate: bool
    current_runtime_matches_eval_gate: bool
    eval_manifest_path: str
    corpus_state_snapshot_path: str
    corpus_coverage_report_path: Optional[str]
    corpus_coverage_summary_path: Optional[str]
    corpus_selection_summary_path: Optional[str]
    spawned_validator_gate_passed: Optional[bool]
    binding_review_samples: List[ValidatedBindingReviewSample] = field(default_factory=list)
    spawned_validator_gate_manifest_path: Optional[str] = None
    spawned_validator_gate_matches_state: Optional[bool] = None
    supplemental_real_question_pack_manifest_path: Optional[str] = None
    supplemental_real_question_pack_matches_state: Optional[bool] = None
    supplemental_real_question_pack_run_id: Optional[str] = None


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {
            item.name: dataclass_to_dict(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, tuple):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: dataclass_to_dict(item) for key, item in value.items()}
    return value
