from __future__ import annotations

import re
from functools import lru_cache
from dataclasses import dataclass

from eubw_researcher.models import (
    AppliedTermNormalization,
    TerminologyAlias,
    TerminologyConfig,
    TerminologyMapping,
)


@dataclass(frozen=True)
class _CompiledTerminologyAlias:
    term: str
    pattern: re.Pattern[str]
    context_patterns: tuple[re.Pattern[str], ...]


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE)


def _combined_context_aliases(
    mapping: TerminologyMapping,
    alias: TerminologyAlias,
) -> tuple[str, ...]:
    combined: list[str] = []
    seen: set[str] = set()
    for context_alias in [*mapping.context_aliases, *alias.context_aliases]:
        context_key = context_alias.casefold()
        if context_key in seen:
            continue
        seen.add(context_key)
        combined.append(context_alias)
    return tuple(combined)


@dataclass(frozen=True)
class _CompiledTerminologyMapping:
    canonical_term: str
    aliases: tuple[_CompiledTerminologyAlias, ...]


def _compile_mapping(mapping: TerminologyMapping) -> _CompiledTerminologyMapping:
    sorted_aliases = sorted(
        enumerate(mapping.alias_rules),
        key=lambda item: (-len(item[1].term), item[0]),
    )
    return _CompiledTerminologyMapping(
        canonical_term=mapping.canonical_term,
        aliases=tuple(
            _CompiledTerminologyAlias(
                term=alias.term,
                pattern=_alias_pattern(alias.term),
                context_patterns=tuple(
                    _alias_pattern(context_alias)
                    for context_alias in _combined_context_aliases(mapping, alias)
                ),
            )
            for _, alias in sorted_aliases
        ),
    )


@lru_cache(maxsize=8)
def _compile_terminology_config(
    terminology: TerminologyConfig,
) -> tuple[_CompiledTerminologyMapping, ...]:
    return tuple(_compile_mapping(mapping) for mapping in terminology.mappings)


def _has_required_context(question: str, alias: _CompiledTerminologyAlias) -> bool:
    if not alias.context_patterns:
        return True
    return any(pattern.search(question) for pattern in alias.context_patterns)


def normalize_query_terms_with_trace(
    question: str,
    terminology: TerminologyConfig,
) -> tuple[str, list[AppliedTermNormalization]]:
    normalized = question
    offset_map = list(range(len(question) + 1))
    applied_with_positions: list[tuple[int, str, str]] = []

    for mapping in _compile_terminology_config(terminology):
        for alias in mapping.aliases:
            if not _has_required_context(normalized, alias):
                continue
            matches = list(alias.pattern.finditer(normalized))
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
    return normalize_query_terms_with_trace(question, terminology)[1]


def normalize_query_terms(question: str, terminology: TerminologyConfig) -> str:
    return normalize_query_terms_with_trace(question, terminology)[0]
