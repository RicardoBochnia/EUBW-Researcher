from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from eubw_researcher.models import (
    AppliedTermNormalization,
    TerminologyAlias,
    TerminologyConfig,
    TerminologyMapping,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


@dataclass(frozen=True)
class _CompiledTerminologyAlias:
    term: str
    pattern: re.Pattern[str]
    context_patterns: tuple[re.Pattern[str], ...]


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<!\w){re.escape(normalize_text_for_matching(alias))}(?!\w)",
        re.IGNORECASE,
    )


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


def _has_required_context(match_text: str, alias: _CompiledTerminologyAlias) -> bool:
    if not alias.context_patterns:
        return True
    return any(pattern.search(match_text) for pattern in alias.context_patterns)


def _normalize_text_with_offset_map(text: str) -> tuple[str, list[int]]:
    normalized_parts: list[str] = []
    offset_map = [0]
    for index, char in enumerate(text):
        normalized_char = normalize_text_for_matching(char)
        normalized_parts.append(normalized_char)
        if not normalized_char:
            continue
        for normalized_index in range(len(normalized_char)):
            offset_map.append(index if normalized_index < (len(normalized_char) - 1) else index + 1)
    return "".join(normalized_parts), offset_map


def normalize_query_terms_with_trace(
    question: str,
    terminology: TerminologyConfig,
) -> tuple[str, list[AppliedTermNormalization]]:
    display_text = question
    match_text, offset_map = _normalize_text_with_offset_map(question)
    applied_with_positions: list[tuple[int, str, str]] = []

    for mapping in _compile_terminology_config(terminology):
        for alias in mapping.aliases:
            if not _has_required_context(match_text, alias):
                continue
            matches = list(alias.pattern.finditer(match_text))
            if not matches:
                continue
            rebuilt_display_parts: list[str] = []
            last_display_end = 0

            for match in matches:
                display_start = offset_map[match.start()]
                display_end = offset_map[match.end()]
                applied_with_positions.append(
                    (
                        display_start,
                        display_text[display_start:display_end].lower(),
                        mapping.canonical_term,
                    )
                )
                rebuilt_display_parts.append(display_text[last_display_end:display_start])
                rebuilt_display_parts.append(mapping.canonical_term)
                last_display_end = display_end

            rebuilt_display_parts.append(display_text[last_display_end:])
            display_text = "".join(rebuilt_display_parts)
            match_text, offset_map = _normalize_text_with_offset_map(display_text)

    applied_with_positions.sort(key=lambda item: item[0])
    applied = [
        AppliedTermNormalization(
            source_term=source_term,
            canonical_term=canonical_term,
        )
        for _, source_term, canonical_term in applied_with_positions
    ]
    return display_text, applied


def explain_query_term_normalization(
    question: str,
    terminology: TerminologyConfig,
) -> list[AppliedTermNormalization]:
    return normalize_query_terms_with_trace(question, terminology)[1]


def normalize_query_terms(question: str, terminology: TerminologyConfig) -> str:
    return normalize_query_terms_with_trace(question, terminology)[0]
