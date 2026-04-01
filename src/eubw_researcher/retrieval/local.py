from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List

from eubw_researcher.models import (
    IngestionBundle,
    RetrievalCandidate,
    RetrievalPlanStep,
    RuntimeConfig,
    SourceHierarchyConfig,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def _expand_tokens(tokens: Iterable[str], expansions: Dict[str, List[str]]) -> List[str]:
    expanded = set(tokens)
    for token in list(expanded):
        for mapped in expansions.get(token, []):
            expanded.add(mapped)
    return sorted(expanded)


def _lexical_score(query_tokens: List[str], chunk_tokens: List[str]) -> float:
    if not query_tokens:
        return 0.0
    counts = Counter(chunk_tokens)
    unique_query = set(query_tokens)
    hits = sum(1 for token in unique_query if counts[token] > 0)
    return hits / max(len(unique_query), 1)


def _semantic_score(
    query_tokens: List[str],
    chunk_tokens: List[str],
    expansions: Dict[str, List[str]],
) -> float:
    query_set = set(_expand_tokens(query_tokens, expansions))
    chunk_set = set(_expand_tokens(chunk_tokens, expansions))
    if not query_set:
        return 0.0
    return len(query_set & chunk_set) / len(query_set)


def retrieve_candidates(
    question: str,
    step: RetrievalPlanStep,
    bundle: IngestionBundle,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
) -> List[RetrievalCandidate]:
    query_tokens = _tokenize(question)
    candidates: List[RetrievalCandidate] = []

    for document in bundle.documents:
        if document.entry.source_kind != step.required_kind:
            continue
        if document.entry.source_role_level != step.required_source_role_level:
            continue
        for chunk in document.chunks:
            chunk_tokens = _tokenize(chunk.text)
            lexical = _lexical_score(query_tokens, chunk_tokens)
            semantic = _semantic_score(
                query_tokens,
                chunk_tokens,
                runtime_config.semantic_expansions,
            )
            rank = hierarchy.rank_for(document.entry.source_kind)
            role_bonus = max(0.0, 0.15 - (0.01 * rank))
            combined = (
                lexical * runtime_config.lexical_weight
                + semantic * runtime_config.semantic_weight
                + role_bonus
            )
            candidates.append(
                RetrievalCandidate(
                    chunk=chunk,
                    lexical_score=round(lexical, 4),
                    semantic_score=round(semantic, 4),
                    combined_score=round(combined, 4),
                    meets_threshold=combined >= runtime_config.min_combined_score,
                )
            )
    candidates.sort(
        key=lambda item: (
            item.combined_score,
            item.lexical_score,
            item.semantic_score,
        ),
        reverse=True,
    )
    thresholded = [candidate for candidate in candidates if candidate.meets_threshold]
    if thresholded:
        return thresholded[: step.inspection_depth]
    return candidates[: step.inspection_depth]
