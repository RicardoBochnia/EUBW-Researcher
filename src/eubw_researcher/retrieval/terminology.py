from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class _TerminologyMapping:
    canonical_term: str
    aliases: Tuple[str, ...]


_TERMINOLOGY_MAPPINGS: Tuple[_TerminologyMapping, ...] = (
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
    return re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", re.IGNORECASE)


def explain_query_term_normalization(question: str) -> List[tuple[str, str]]:
    normalized = question
    applied: List[tuple[str, str]] = []

    for mapping in _TERMINOLOGY_MAPPINGS:
        for alias in mapping.aliases:
            pattern = _alias_pattern(alias)

            def _replace(match: re.Match[str]) -> str:
                applied.append((match.group(0).lower(), mapping.canonical_term))
                return mapping.canonical_term

            normalized = pattern.sub(_replace, normalized)

    return applied


def normalize_query_terms(question: str) -> str:
    normalized = question

    for mapping in _TERMINOLOGY_MAPPINGS:
        for alias in mapping.aliases:
            normalized = _alias_pattern(alias).sub(mapping.canonical_term, normalized)

    return normalized
