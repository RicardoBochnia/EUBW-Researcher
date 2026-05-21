from __future__ import annotations

import re
from typing import Iterable

from eubw_researcher.models import (
    CandidateClaimRecord,
    CandidateClaimStatus,
    ClaimTarget,
    ClaimType,
    EvidenceCluster,
    IngestionBundle,
    RetrievalCandidate,
    SelectedEvidenceRecord,
    SourceChunk,
    SourceCatalog,
    SourceKind,
    SourceRoleLevel,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


def _claim_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", normalize_text_for_matching(value)).strip("_")
    return f"dynamic_{normalized[:80] or 'claim'}"


def _terms(value: str, *, max_terms: int = 8) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", normalize_text_for_matching(value)):
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) >= max_terms:
            break
    return terms


def _claim_text(snippet: str) -> str:
    compact = " ".join(snippet.split())
    if len(compact) <= 320:
        return compact
    truncated = compact[:320].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def build_dynamic_claim_targets(
    clusters: Iterable[EvidenceCluster],
    *,
    max_targets: int = 10,
) -> tuple[list[ClaimTarget], list[SelectedEvidenceRecord]]:
    targets: list[ClaimTarget] = []
    selected_evidence: list[SelectedEvidenceRecord] = []
    seen_chunk_ids: set[str] = set()
    cluster_list = [cluster for cluster in clusters if cluster.records]
    max_records = max((len(cluster.records) for cluster in cluster_list), default=0)
    for record_index in range(max_records):
        for cluster in cluster_list:
            if record_index >= len(cluster.records):
                continue
            record = cluster.records[record_index]
            if record.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(record.chunk_id)
            claim_text = _claim_text(record.snippet)
            primary_terms = _terms(" ".join([claim_text, *cluster.matched_concepts]))
            if not primary_terms:
                continue
            support_group = primary_terms[: min(3, len(primary_terms))]
            claim_id = _claim_id(f"{cluster.cluster_id}_{record.chunk_id}")
            targets.append(
                ClaimTarget(
                    target_id=claim_id,
                    claim_text=claim_text,
                    claim_type=ClaimType.SYNTHESIS,
                    required_source_role_level=record.source_role_level,
                    preferred_kinds=[record.source_kind],
                    scope_terms=primary_terms,
                    primary_terms=primary_terms,
                    support_groups=[support_group],
                    contradiction_groups=[],
                    grouping_label=f"Evidence cluster: {cluster.label}",
                    source_ids=[record.source_id],
                )
            )
            selected_evidence.append(
                SelectedEvidenceRecord(
                    claim_id=claim_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    selection_reason="assistive_dynamic_claim_target",
                )
            )
            if len(targets) >= max_targets:
                return targets, selected_evidence
    return targets, selected_evidence


def _role_rank(role: SourceRoleLevel) -> int:
    return {
        SourceRoleLevel.HIGH: 3,
        SourceRoleLevel.MEDIUM: 2,
        SourceRoleLevel.LOW: 1,
    }[role]


def build_candidate_claim_targets(
    candidate_claims: Iterable[CandidateClaimRecord],
    catalog: SourceCatalog,
    *,
    max_targets: int = 8,
) -> list[ClaimTarget]:
    targets: list[ClaimTarget] = []
    sources_by_id = catalog.by_id()
    for claim in candidate_claims:
        if claim.status == CandidateClaimStatus.DEPRECATED:
            continue
        source_ids = [
            source_id for source_id in claim.source_ids if source_id in sources_by_id
        ]
        source_entries = [sources_by_id[source_id] for source_id in source_ids]
        terms = _terms(
            " ".join(
                part
                for part in [
                    claim.normalized_statement,
                    claim.topic or "",
                    claim.actor or "",
                    claim.action or "",
                    claim.object or "",
                    claim.modality or "",
                ]
                if part
            ),
            max_terms=10,
        )
        if not terms:
            continue
        preferred_kinds: list[SourceKind] = []
        for entry in source_entries:
            if entry.source_kind not in preferred_kinds:
                preferred_kinds.append(entry.source_kind)
        required_role = (
            max(
                (entry.source_role_level for entry in source_entries),
                key=_role_rank,
            )
            if source_entries
            else SourceRoleLevel.MEDIUM
        )
        targets.append(
            ClaimTarget(
                target_id=claim.claim_id,
                claim_text=claim.normalized_statement,
                claim_type=(
                    ClaimType.OBLIGATION
                    if claim.modality in {"obligation", "prohibition"}
                    else ClaimType.SYNTHESIS
                ),
                required_source_role_level=required_role,
                preferred_kinds=preferred_kinds,
                scope_terms=terms,
                primary_terms=terms[: min(5, len(terms))],
                support_groups=[terms[: min(3, len(terms))]],
                contradiction_groups=[],
                grouping_label=(
                    f"Imported legacy candidate: {claim.topic}"
                    if claim.topic
                    else "Imported legacy candidate"
                ),
                source_ids=source_ids,
            )
        )
        if len(targets) >= max_targets:
            break
    return targets


def selected_evidence_candidates(
    ingestion_bundle: IngestionBundle,
    selected_evidence: Iterable[SelectedEvidenceRecord],
) -> list[RetrievalCandidate]:
    chunks_by_id: dict[str, SourceChunk] = {
        chunk.chunk_id: chunk
        for document in ingestion_bundle.documents
        for chunk in document.chunks
    }
    candidates: list[RetrievalCandidate] = []
    for index, selected in enumerate(selected_evidence, start=1):
        chunk = chunks_by_id.get(selected.chunk_id)
        if chunk is None:
            continue
        score = max(0.5, 1.0 - index * 0.01)
        candidates.append(
            RetrievalCandidate(
                chunk=chunk,
                lexical_score=score,
                semantic_score=score,
                combined_score=score,
                meets_threshold=True,
            )
        )
    return candidates
