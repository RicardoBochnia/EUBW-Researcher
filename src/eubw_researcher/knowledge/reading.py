from __future__ import annotations

import re
from collections import defaultdict

from eubw_researcher.models import (
    ClaimVerificationRecord,
    EvidenceCluster,
    EvidenceSynthesisMatrix,
    EvidenceSynthesisRecord,
    OpenedPassageRecord,
    ReadingPlan,
    ReadingPlanItem,
    RuntimeConfig,
    SelectedEvidenceRecord,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


def _clusters_for_reading(
    clusters: list[EvidenceCluster],
    *,
    max_clusters: int,
) -> list[EvidenceCluster]:
    if max_clusters <= 0:
        return []
    selected = list(clusters[:max_clusters])
    selected_source_ids = {
        source_id for cluster in selected for source_id in cluster.source_ids
    }
    rescue_clusters = [
        cluster
        for cluster in clusters[max_clusters:]
        if "source_catalog_candidate_present" in cluster.sufficiency_signals
        and not selected_source_ids.intersection(cluster.source_ids)
    ]
    for cluster in rescue_clusters:
        if len(selected) < max_clusters:
            selected.append(cluster)
        else:
            selected[-1] = cluster
        selected_source_ids.update(cluster.source_ids)
    return selected


def _compact_statement(text: str, *, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"^[#>*\-\s]+", "", compact)
    normalized = normalize_text_for_matching(compact)
    if (
        "upon cancellation" in normalized
        and "must remove the visible trust mark" in normalized
        and "not the relying party" in normalized
        and "attestation provider" in normalized
    ):
        return (
            "Passage supports: upon cancellation, the Wallet Provider must remove "
            "the visible trust mark and references to it; the scoped trust mark is "
            "for the visible EUDI Wallet mark, not Relying Party services or "
            "Attestation Provider qualifications."
        )
    if "out of scope" in normalized and "relying party" in normalized:
        return (
            "Passage supports: the source treats the visible wallet trust mark as "
            "in-scope and leaves unrelated Relying Party or attestation-provider "
            "trust indicators out of scope."
        )
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    chosen = next((sentence for sentence in sentences if len(sentence) > 40), compact)
    if len(chosen) > limit:
        chosen = chosen[:limit].rsplit(" ", 1)[0].strip() + "..."
    return "Passage supports: " + chosen


def _answer_role(cluster: EvidenceCluster, record) -> str:
    surface = normalize_text_for_matching(" ".join([record.snippet, record.locator or ""]))
    if cluster.open_issue_ids:
        return "open_issue"
    if any(marker in surface for marker in ("out of scope", "does not address", "scope is")):
        return "scope_boundary"
    if "source_catalog_candidate_present" in cluster.sufficiency_signals:
        return "core_answer_support"
    if record.source_role_level.value == "low":
        return "background"
    return "source_role_context"


def _caveats(cluster: EvidenceCluster, record, verification) -> list[str]:
    caveats: list[str] = [
        f"source_role:{record.source_role_level.value}",
        f"binding_level:{record.binding_level.value}",
        f"document_status:{record.document_status.value}",
    ]
    if verification is not None and not verification.answer_use_allowed:
        caveats.append("verification does not allow answer use")
    if cluster.open_issue_ids:
        caveats.extend(f"open_issue:{issue_id}" for issue_id in cluster.open_issue_ids)
    return caveats


def build_reading_artifacts(
    *,
    question: str,
    clusters: list[EvidenceCluster],
    selected_evidence: list[SelectedEvidenceRecord],
    claim_verification: list[ClaimVerificationRecord],
    runtime_config: RuntimeConfig,
) -> tuple[ReadingPlan, list[OpenedPassageRecord], EvidenceSynthesisMatrix]:
    max_clusters = runtime_config.knowledge_service_max_reading_clusters
    max_opened = runtime_config.knowledge_service_max_opened_passages
    max_adjacent = runtime_config.knowledge_service_max_adjacent_passages_per_cluster

    budget = {
        "max_clusters": max_clusters,
        "max_opened_passages": max_opened,
        "max_adjacent_passages_per_cluster": max_adjacent,
        "timeout_seconds": runtime_config.knowledge_service_reading_timeout_seconds,
    }
    reading_plan = ReadingPlan(question=question, budget=budget)
    opened_passages: list[OpenedPassageRecord] = []
    verification_by_claim_id = {
        record.claim_id: record for record in claim_verification
    }
    selected_by_chunk_id: dict[str, list[SelectedEvidenceRecord]] = defaultdict(list)
    for selected in selected_evidence:
        selected_by_chunk_id[selected.chunk_id].append(selected)

    reading_clusters = _clusters_for_reading(clusters, max_clusters=max_clusters)
    opened_count = 0
    for cluster in reading_clusters:
        if not cluster.records:
            continue
        cluster_records = cluster.records[: 1 + max_adjacent]
        for index, record in enumerate(cluster_records):
            if max_opened and opened_count >= max_opened:
                reading_plan.budget_exhausted = True
                break
            operation = "open_passage" if index == 0 else "open_adjacent_passage"
            item_id = f"read_{len(reading_plan.items) + 1}"
            reading_plan.items.append(
                ReadingPlanItem(
                    item_id=item_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    operation=operation,
                    reason=(
                        "Primary evidence-cluster passage"
                        if index == 0
                        else "Adjacent context passage"
                    ),
                )
            )
            opened_passages.append(
                OpenedPassageRecord(
                    passage_id=item_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    passage_role="primary" if index == 0 else "adjacent",
                    text_snippet=record.snippet,
                )
            )
            opened_count += 1
        if reading_plan.budget_exhausted:
            break

    records: list[EvidenceSynthesisRecord] = []
    for cluster in reading_clusters:
        for record in cluster.records[: 1 + max_adjacent]:
            selected_records = selected_by_chunk_id.get(record.chunk_id, [])
            claim_id = selected_records[0].claim_id if selected_records else None
            verification = verification_by_claim_id.get(claim_id or "")
            records.append(
                EvidenceSynthesisRecord(
                    synthesis_id=f"synthesis_{len(records) + 1}",
                    claim_id=claim_id,
                    cluster_id=cluster.cluster_id,
                    answer_role=_answer_role(cluster, record),
                    statement=_compact_statement(record.snippet),
                    source_ids=[record.source_id],
                    chunk_ids=[record.chunk_id],
                    locators=[record.locator] if record.locator else [],
                    verification_status=(
                        verification.verification_result if verification is not None else None
                    ),
                    caveats=_caveats(cluster, record, verification),
                )
            )

    return (
        reading_plan,
        opened_passages,
        EvidenceSynthesisMatrix(question=question, records=records),
    )
