from __future__ import annotations

import re
from dataclasses import dataclass


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
    return re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE)


def _has_required_context(question: str, mapping: _CompiledTerminologyMapping) -> bool:
    if not mapping.context_patterns:
        return True
    return any(pattern.search(question) for pattern in mapping.context_patterns)


_COMPILED_TERMINOLOGY_MAPPINGS: tuple[_CompiledTerminologyMapping, ...] = tuple(
    _CompiledTerminologyMapping(
        canonical_term=mapping.canonical_term,
        patterns=tuple(_alias_pattern(alias) for alias in mapping.aliases),
        context_patterns=tuple(_alias_pattern(alias) for alias in mapping.context_aliases),
    )
    for mapping in _TERMINOLOGY_MAPPINGS
)


def explain_query_term_normalization(question: str) -> list[tuple[str, str]]:
    normalized = question
    offset_map = list(range(len(question) + 1))
    applied_with_positions: list[tuple[int, str, str]] = []

    for mapping in _COMPILED_TERMINOLOGY_MAPPINGS:
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
    return [
        (source_term, canonical_term)
        for _, source_term, canonical_term in applied_with_positions
    ]


def normalize_query_terms(question: str) -> str:
    normalized = question

    for mapping in _COMPILED_TERMINOLOGY_MAPPINGS:
        if not _has_required_context(normalized, mapping):
            continue
        for pattern in mapping.patterns:
            normalized = pattern.sub(mapping.canonical_term, normalized)

    return normalized
