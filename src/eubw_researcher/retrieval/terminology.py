from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class _TerminologyMapping:
    canonical_term: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class _CompiledTerminologyMapping:
    canonical_term: str
    patterns: tuple[re.Pattern[str], ...]


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
    ),
)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-zA-Z0-9]){re.escape(alias)}(?![a-zA-Z0-9])", re.IGNORECASE)


_COMPILED_TERMINOLOGY_MAPPINGS: tuple[_CompiledTerminologyMapping, ...] = tuple(
    _CompiledTerminologyMapping(
        canonical_term=mapping.canonical_term,
        patterns=tuple(_alias_pattern(alias) for alias in mapping.aliases),
    )
    for mapping in _TERMINOLOGY_MAPPINGS
)


def explain_query_term_normalization(question: str) -> list[tuple[str, str]]:
    normalized = question
    applied: list[tuple[str, str]] = []

    for mapping in _COMPILED_TERMINOLOGY_MAPPINGS:
        for pattern in mapping.patterns:
            found_match = False
            for match in pattern.finditer(normalized):
                found_match = True
                applied.append((match.group(0).lower(), mapping.canonical_term))
            if not found_match:
                continue
            normalized = pattern.sub(mapping.canonical_term, normalized)

    return applied


def normalize_query_terms(question: str) -> str:
    normalized = question

    for mapping in _COMPILED_TERMINOLOGY_MAPPINGS:
        for pattern in mapping.patterns:
            normalized = pattern.sub(mapping.canonical_term, normalized)

    return normalized
