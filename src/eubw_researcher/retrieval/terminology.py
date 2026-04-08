from __future__ import annotations

import re
from dataclasses import dataclass

from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


@dataclass(frozen=True)
class _TerminologyMapping:
    canonical_term: str
    aliases: tuple[str, ...]
    context_aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CompiledTerminologyMapping:
    canonical_term: str
    patterns: tuple[re.Pattern[str], ...]
    context_patterns: tuple[re.Pattern[str], ...]


_TERMINOLOGY_MAPPINGS: tuple[_TerminologyMapping, ...] = (
    _TerminologyMapping(
        canonical_term="business wallet",
        aliases=("eu business wallet", "eubw"),
    ),
    _TerminologyMapping(
        canonical_term="wallet-relying party",
        aliases=("wallet relying party", "wallet relying-party", "wallet-relying-party"),
    ),
    _TerminologyMapping(
        canonical_term="authorization server",
        aliases=("authorisation server",),
    ),
    _TerminologyMapping(
        canonical_term="registration certificate",
        aliases=("registration cert",),
    ),
    _TerminologyMapping(
        canonical_term="access certificate",
        aliases=("access cert",),
        context_aliases=(
            "business wallet",
            "eu business wallet",
            "eubw",
            "wallet-relying party",
            "wallet relying party",
            "wallet-relying-party",
        ),
    ),
)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<!\w){re.escape(normalize_text_for_matching(alias))}(?!\w)",
        re.IGNORECASE,
    )


def _has_required_context(match_text: str, mapping: _CompiledTerminologyMapping) -> bool:
    if not mapping.context_patterns:
        return True
    return any(pattern.search(match_text) for pattern in mapping.context_patterns)


_COMPILED_TERMINOLOGY_MAPPINGS: tuple[_CompiledTerminologyMapping, ...] = tuple(
    _CompiledTerminologyMapping(
        canonical_term=mapping.canonical_term,
        patterns=tuple(_alias_pattern(alias) for alias in mapping.aliases),
        context_patterns=tuple(_alias_pattern(alias) for alias in mapping.context_aliases),
    )
    for mapping in _TERMINOLOGY_MAPPINGS
)


def explain_query_term_normalization(question: str) -> list[tuple[str, str]]:
    display_text = question
    match_text = normalize_text_for_matching(question)
    offset_map = list(range(len(question) + 1))
    applied_with_positions: list[tuple[int, str, str]] = []

    for mapping in _COMPILED_TERMINOLOGY_MAPPINGS:
        if not _has_required_context(match_text, mapping):
            continue
        for pattern in mapping.patterns:
            matches = list(pattern.finditer(match_text))
            if not matches:
                continue
            rebuilt_display_parts: list[str] = []
            rebuilt_match_parts: list[str] = []
            rebuilt_offset_map: list[int] = []
            last_end = 0

            for match in matches:
                original_start = offset_map[match.start()]
                applied_with_positions.append(
                    (
                        original_start,
                        display_text[match.start() : match.end()].lower(),
                        mapping.canonical_term,
                    )
                )
                rebuilt_display_parts.append(display_text[last_end : match.start()])
                rebuilt_display_parts.append(mapping.canonical_term)
                rebuilt_match_parts.append(match_text[last_end : match.start()])
                rebuilt_match_parts.append(normalize_text_for_matching(mapping.canonical_term))
                rebuilt_offset_map.extend(offset_map[last_end : match.start()])
                rebuilt_offset_map.extend([original_start] * len(mapping.canonical_term))
                last_end = match.end()

            rebuilt_display_parts.append(display_text[last_end:])
            rebuilt_match_parts.append(match_text[last_end:])
            rebuilt_offset_map.extend(offset_map[last_end:])
            display_text = "".join(rebuilt_display_parts)
            match_text = "".join(rebuilt_match_parts)
            offset_map = rebuilt_offset_map

    applied_with_positions.sort(key=lambda item: item[0])
    return [
        (source_term, canonical_term)
        for _, source_term, canonical_term in applied_with_positions
    ]


def normalize_query_terms(question: str) -> str:
    display_text = question
    match_text = normalize_text_for_matching(question)

    for mapping in _COMPILED_TERMINOLOGY_MAPPINGS:
        if not _has_required_context(match_text, mapping):
            continue
        for pattern in mapping.patterns:
            matches = list(pattern.finditer(match_text))
            if not matches:
                continue
            rebuilt_display_parts: list[str] = []
            rebuilt_match_parts: list[str] = []
            last_end = 0
            for match in matches:
                rebuilt_display_parts.append(display_text[last_end : match.start()])
                rebuilt_display_parts.append(mapping.canonical_term)
                rebuilt_match_parts.append(match_text[last_end : match.start()])
                rebuilt_match_parts.append(normalize_text_for_matching(mapping.canonical_term))
                last_end = match.end()

            rebuilt_display_parts.append(display_text[last_end:])
            rebuilt_match_parts.append(match_text[last_end:])
            display_text = "".join(rebuilt_display_parts)
            match_text = "".join(rebuilt_match_parts)

    return display_text
