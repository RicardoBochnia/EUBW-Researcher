from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from eubw_researcher.knowledge.query_expansion import (
    QueryExpansion,
    contains_term,
    searchable_text,
)
from eubw_researcher.models import (
    CandidateClaimRecord,
    OpenIssueRecord,
    RelationGraphEdge,
    SourceCatalog,
    SourceCatalogEntry,
)

SOURCE_RESCUE_THRESHOLD = 0.55


@dataclass(frozen=True)
class SourceRetrievalCandidate:
    source_id: str
    score: float
    matched_terms: tuple[str, ...] = field(default_factory=tuple)
    matched_phrases: tuple[str, ...] = field(default_factory=tuple)
    channel_scores: dict[str, float] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_diagnostic(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "score": round(self.score, 4),
            "matched_terms": list(self.matched_terms),
            "matched_phrases": list(self.matched_phrases),
            "channel_scores": {
                key: round(value, 4) for key, value in self.channel_scores.items()
            },
            "reasons": list(self.reasons),
        }


def _path_basename(path: Path | None) -> str:
    if path is None:
        return ""
    return path.name


def _metadata_surface(source: SourceCatalogEntry) -> str:
    metadata_values: list[str] = []
    for key, value in sorted(source.governance_metadata.items()):
        if isinstance(value, (str, int, float, bool)):
            metadata_values.extend([str(key), str(value)])
        elif isinstance(value, list):
            metadata_values.append(str(key))
            metadata_values.extend(str(item) for item in value if isinstance(item, (str, int, float, bool)))
    return " ".join(metadata_values)


def _source_surfaces(source: SourceCatalogEntry) -> dict[str, str]:
    id_values = [
        source.source_id,
        source.archive_source_id or "",
        " ".join(source.legacy_source_ids),
    ]
    path_values = [
        _path_basename(source.local_path),
        str(source.local_path or ""),
        source.canonical_url or "",
    ]
    metadata_values = [
        source.publication_status or "",
        source.source_kind.value,
        source.source_role_level.value,
        source.source_family_id or "",
        _metadata_surface(source),
    ]
    return {
        "title": searchable_text(source.title),
        "ids": searchable_text(" ".join(id_values)),
        "path": searchable_text(" ".join(path_values)),
        "metadata": searchable_text(" ".join(metadata_values)),
        "all": searchable_text(" ".join([source.title, *id_values, *path_values, *metadata_values])),
    }


def _weighted_hits(
    surface: str,
    terms: Iterable[str],
    expansion: QueryExpansion,
) -> tuple[float, tuple[str, ...]]:
    matched: list[str] = []
    score = 0.0
    for term in terms:
        if not contains_term(surface, term):
            continue
        matched.append(term)
        score += expansion.term_weights.get(term, 1.0)
    return score, tuple(matched)


def _claim_source_scores(
    claims: Iterable[CandidateClaimRecord],
    expansion: QueryExpansion,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    distinctive_total = max(
        1.0,
        sum(expansion.term_weights.get(term, 1.0) for term in expansion.distinctive_terms),
    )
    for claim in claims:
        surface = searchable_text(
            " ".join(
                value
                for value in (
                    claim.normalized_statement,
                    claim.topic or "",
                    claim.actor or "",
                    claim.action or "",
                    claim.object or "",
                    claim.modality or "",
                )
                if value
            )
        )
        matched_weight, _ = _weighted_hits(surface, expansion.distinctive_terms, expansion)
        if matched_weight <= 0:
            continue
        claim_score = min(1.0, matched_weight / distinctive_total)
        for source_id in claim.source_ids:
            scores[source_id] = max(scores.get(source_id, 0.0), claim_score)
    return scores


def _issue_source_scores(
    issues: Iterable[OpenIssueRecord],
    expansion: QueryExpansion,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    distinctive_total = max(
        1.0,
        sum(expansion.term_weights.get(term, 1.0) for term in expansion.distinctive_terms),
    )
    for issue in issues:
        surface = searchable_text(
            " ".join([issue.issue_statement, issue.reason_open, " ".join(issue.affected_answer_facets)])
        )
        matched_weight, _ = _weighted_hits(surface, expansion.distinctive_terms, expansion)
        if matched_weight <= 0:
            continue
        issue_score = min(1.0, matched_weight / distinctive_total)
        for source_id in issue.affected_source_ids:
            scores[source_id] = max(scores.get(source_id, 0.0), issue_score)
    return scores


def _relation_source_scores(
    relations: Iterable[RelationGraphEdge],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for relation in relations:
        for source_id in relation.evidence_source_ids:
            scores[source_id] = max(scores.get(source_id, 0.0), min(1.0, relation.confidence or 0.2))
    return scores


def retrieve_source_candidates(
    catalog: SourceCatalog,
    expansion: QueryExpansion,
    *,
    candidate_claims: Iterable[CandidateClaimRecord] = (),
    open_issues: Iterable[OpenIssueRecord] = (),
    relation_edges: Iterable[RelationGraphEdge] = (),
    limit: int = 40,
) -> list[SourceRetrievalCandidate]:
    claim_scores = _claim_source_scores(candidate_claims, expansion)
    issue_scores = _issue_source_scores(open_issues, expansion)
    relation_scores = _relation_source_scores(relation_edges)
    distinctive_terms = expansion.distinctive_terms or expansion.all_terms
    distinctive_total = max(
        1.0,
        sum(expansion.term_weights.get(term, 1.0) for term in distinctive_terms),
    )
    phrase_total = max(
        1.0,
        sum(expansion.term_weights.get(phrase, 2.0) for phrase in expansion.phrases),
    )

    candidates: list[SourceRetrievalCandidate] = []
    for source in catalog.entries:
        surfaces = _source_surfaces(source)
        title_weight, title_terms = _weighted_hits(surfaces["title"], distinctive_terms, expansion)
        id_weight, id_terms = _weighted_hits(surfaces["ids"], expansion.all_terms, expansion)
        path_weight, path_terms = _weighted_hits(surfaces["path"], expansion.all_terms, expansion)
        metadata_weight, metadata_terms = _weighted_hits(surfaces["metadata"], distinctive_terms, expansion)
        all_weight, all_terms = _weighted_hits(surfaces["all"], distinctive_terms, expansion)
        title_phrase_weight, title_phrases = _weighted_hits(surfaces["title"], expansion.phrases, expansion)
        path_phrase_weight, path_phrases = _weighted_hits(surfaces["path"], expansion.phrases, expansion)

        title_terms_score = min(1.0, title_weight / distinctive_total)
        phrase_score = min(1.0, (title_phrase_weight + path_phrase_weight) / phrase_total)
        id_path_score = min(1.0, (id_weight + path_weight) / max(1.0, sum(expansion.term_weights.get(term, 1.0) for term in expansion.all_terms)))
        metadata_score = min(1.0, metadata_weight / distinctive_total)
        broad_source_score = min(1.0, all_weight / distinctive_total)
        claim_score = claim_scores.get(source.source_id, 0.0)
        issue_score = issue_scores.get(source.source_id, 0.0)
        relation_score = relation_scores.get(source.source_id, 0.0)
        source_role_score = {
            "high": 0.06,
            "medium": 0.08,
            "low": 0.02,
        }.get(source.source_role_level.value, 0.0)
        kind_score = {
            "technical_standard": 0.08,
            "project_artifact": 0.08,
            "implementing_act": 0.06,
            "regulation": 0.05,
        }.get(source.source_kind.value, 0.0)

        unique_title_phrase_bonus = 0.0
        if title_phrases:
            unique_title_phrase_bonus = 0.22

        channel_scores = {
            "source_title_terms": title_terms_score,
            "source_title_or_path_phrase": phrase_score,
            "source_id_or_path": id_path_score,
            "source_metadata": metadata_score,
            "source_broad_field": broad_source_score,
            "imported_claim_signal": claim_score,
            "open_issue_signal": issue_score,
            "relation_signal": relation_score,
            "source_role": source_role_score,
            "source_kind": kind_score,
            "unique_title_phrase_bonus": unique_title_phrase_bonus,
        }
        score = min(
            1.0,
            0.38 * title_terms_score
            + 0.42 * phrase_score
            + 0.28 * id_path_score
            + 0.10 * metadata_score
            + 0.14 * broad_source_score
            + 0.22 * claim_score
            + 0.16 * issue_score
            + 0.08 * relation_score
            + source_role_score
            + kind_score
            + unique_title_phrase_bonus,
        )
        matched_terms = tuple(dict.fromkeys([*title_terms, *id_terms, *path_terms, *metadata_terms, *all_terms]))
        matched_phrases = tuple(dict.fromkeys([*title_phrases, *path_phrases]))
        if score <= 0 or (not matched_terms and not matched_phrases and not claim_score and not issue_score):
            continue
        reasons: list[str] = []
        if matched_phrases:
            reasons.append("distinctive_source_phrase")
        if title_terms:
            reasons.append("source_title_terms")
        if id_terms or path_terms:
            reasons.append("source_id_path_terms")
        if claim_score:
            reasons.append("imported_claim_signal")
        if issue_score:
            reasons.append("open_issue_signal")
        candidates.append(
            SourceRetrievalCandidate(
                source_id=source.source_id,
                score=score,
                matched_terms=matched_terms,
                matched_phrases=matched_phrases,
                channel_scores=channel_scores,
                reasons=tuple(reasons),
            )
        )

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates[:limit]
