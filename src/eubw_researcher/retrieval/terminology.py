from __future__ import annotations

import re
from dataclasses import dataclass

from eubw_researcher.models import (
    AppliedTermNormalization,
    TerminologyConfig,
    TerminologyMapping,
)


@dataclass(frozen=True)
class _CompiledTerminologyMapping:
    canonical_term: str
    patterns: tuple[re.Pattern[str], ...]
    context_patterns: tuple[re.Pattern[str], ...]


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE)


def _compile_mapping(mapping: TerminologyMapping) -> _CompiledTerminologyMapping:
    return _CompiledTerminologyMapping(
        canonical_term=mapping.canonical_term,
        patterns=tuple(_alias_pattern(alias) for alias in mapping.aliases),
        context_patterns=tuple(_alias_pattern(alias) for alias in mapping.context_aliases),
    )


def _compile_terminology_config(
    terminology: TerminologyConfig,
) -> tuple[_CompiledTerminologyMapping, ...]:
    return tuple(_compile_mapping(mapping) for mapping in terminology.mappings)


def _has_required_context(question: str, mapping: _CompiledTerminologyMapping) -> bool:
    if not mapping.context_patterns:
        return True
    return any(pattern.search(question) for pattern in mapping.context_patterns)


def _apply_query_term_normalization(
    question: str,
    terminology: TerminologyConfig,
) -> tuple[str, list[AppliedTermNormalization]]:
    normalized = question
    offset_map = list(range(len(question) + 1))
    applied_with_positions: list[tuple[int, str, str]] = []

    for mapping in _compile_terminology_config(terminology):
        if not _has_required_context(normalized, mapping):
            continue
        for pattern in mapping.patterns:
            matches = list(pattern.finditer(normalized))
            if not matches:
                continue
            rebuilt_parts: list[str] = []
            rebuilt_offset_map: list[int] = []
            last_end = 0

            for match in matches:
                original_start = offset_map[match.start()]
                applied_with_positions.append(
                    (original_start, match.group(0).lower(), mapping.canonical_term)
                )
                rebuilt_parts.append(normalized[last_end : match.start()])
                rebuilt_parts.append(mapping.canonical_term)
                rebuilt_offset_map.extend(offset_map[last_end : match.start()])
                rebuilt_offset_map.extend([original_start] * len(mapping.canonical_term))
                last_end = match.end()

            rebuilt_parts.append(normalized[last_end:])
            rebuilt_offset_map.extend(offset_map[last_end:])
            normalized = "".join(rebuilt_parts)
            offset_map = rebuilt_offset_map

    applied_with_positions.sort(key=lambda item: item[0])
    applied = [
        AppliedTermNormalization(
            source_term=source_term,
            canonical_term=canonical_term,
        )
        for _, source_term, canonical_term in applied_with_positions
    ]
    return normalized, applied


def explain_query_term_normalization(
    question: str,
    terminology: TerminologyConfig,
) -> list[AppliedTermNormalization]:
    return _apply_query_term_normalization(question, terminology)[1]


def normalize_query_terms(question: str, terminology: TerminologyConfig) -> str:
    return _apply_query_term_normalization(question, terminology)[0]
