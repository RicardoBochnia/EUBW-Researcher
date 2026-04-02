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
    source_origin: SourceOrigin = SourceOrigin.LOCAL
    anchorability_hints: List[str] = field(default_factory=list)
    admission_reason: Optional[str] = None


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
class WebDomainPolicy:
    domain: str
    source_kind: SourceKind
    source_role_level: SourceRoleLevel
    jurisdiction: str
    seed_urls: List[str] = field(default_factory=list)
    discovery_urls: List[str] = field(default_factory=list)
    allowed_path_prefixes: List[str] = field(default_factory=list)
    blocked_url_keywords: List[str] = field(default_factory=list)
    allowed_cross_domain_domains: List[str] = field(default_factory=list)


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
        for policy in self.domain_policies:
            if policy.domain == domain:
                return policy
        return None

    def seed_urls_for_kind(self, source_kind: SourceKind) -> List[str]:
        urls: List[str] = []
        for policy in self.domain_policies:
            if policy.source_kind == source_kind:
                urls.extend(policy.seed_urls)
        return urls

    def discovery_urls_for_kind(self, source_kind: SourceKind) -> List[str]:
        urls: List[str] = []
        for policy in self.domain_policies:
            if policy.source_kind == source_kind:
                urls.extend(policy.discovery_urls)
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
    source_origin: SourceOrigin = SourceOrigin.LOCAL
    anchorability_hints: List[str] = field(default_factory=list)
    admission_reason: Optional[str] = None


@dataclass
class ArchiveCorpusConfig:
    archive_root: Path
    archive_catalog: Path
    sources: List[ArchiveSourceSelection]


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
    required_web_fetch_count: int = 0
    require_provisional_grouping: bool = False
    require_manual_review_accept: bool = False
    min_gap_records: int = 0
    min_ledger_entries: int = 1


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
class RetrievalPlan:
    question: str
    steps: List[RetrievalPlanStep]


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
class BlindValidationReport:
    question: str
    intent_type: str
    validation_mode: str
    artifacts_used: List[str]
    raw_document_reads: List[BlindValidationRawRead] = field(default_factory=list)
    raw_document_dependency: str = "none"
    product_output_self_sufficient: bool = False
    passed: bool = False
    summary: str = ""
    missing_facets: List[str] = field(default_factory=list)


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
