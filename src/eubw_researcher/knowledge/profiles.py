from __future__ import annotations

from eubw_researcher.models import (
    EvidenceCluster,
    ResearchProfileConfig,
    ResearchProfileTrace,
    ResearchProfileActivation,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


def _normalized_terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_text_for_matching(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
    return terms


def build_research_profile_trace(
    question: str,
    profile_config: ResearchProfileConfig | None,
    clusters: list[EvidenceCluster],
) -> ResearchProfileTrace | None:
    if profile_config is None or not profile_config.profiles:
        return None

    question_surface = normalize_text_for_matching(question)
    cluster_surface_parts: list[str] = []
    source_ids_by_concept: dict[str, set[str]] = {}
    for cluster in clusters:
        cluster_surface_parts.append(cluster.label)
        cluster_surface_parts.extend(cluster.matched_concepts)
        cluster_surface_parts.extend(cluster.source_ids)
        for concept in cluster.matched_concepts:
            source_ids_by_concept.setdefault(
                normalize_text_for_matching(concept),
                set(),
            ).update(cluster.source_ids)
        for record in cluster.records:
            cluster_surface_parts.append(record.snippet)
            cluster_surface_parts.append(record.source_id)
    cluster_surface = normalize_text_for_matching(" ".join(cluster_surface_parts))
    combined_surface = " ".join([question_surface, cluster_surface])

    activations: list[ResearchProfileActivation] = []
    rejected_profile_ids: list[str] = []
    notes: list[str] = []
    for profile in profile_config.profiles:
        concepts = _normalized_terms(profile.concepts)
        negative_controls = _normalized_terms(profile.negative_controls)
        matched_negative = [
            control for control in negative_controls if control in question_surface
        ]
        if matched_negative:
            rejected_profile_ids.append(profile.profile_id)
            notes.append(
                f"{profile.profile_id}: rejected by negative control "
                + ", ".join(matched_negative)
            )
            continue

        matched_concepts = [
            concept for concept in concepts if concept in combined_surface
        ]
        if not matched_concepts:
            rejected_profile_ids.append(profile.profile_id)
            continue

        matched_source_ids: set[str] = set()
        for concept in matched_concepts:
            matched_source_ids.update(source_ids_by_concept.get(concept, set()))
        activations.append(
            ResearchProfileActivation(
                profile_id=profile.profile_id,
                matched_concepts=matched_concepts,
                matched_source_ids=sorted(matched_source_ids),
                activation_reason=(
                    "Matched generic profile concepts in question or evidence clusters: "
                    + ", ".join(matched_concepts)
                ),
                benchmark_specific_risk=profile.benchmark_specific_risk,
            )
        )

    return ResearchProfileTrace(
        question=question,
        activations=activations,
        rejected_profile_ids=sorted(set(rejected_profile_ids)),
        notes=notes,
    )
