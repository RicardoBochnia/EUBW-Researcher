from __future__ import annotations

import re


TOKEN_RE = re.compile(r"[a-z0-9]+")

_MATCH_TRANSLATION = str.maketrans(
    {
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ß": "s",
        "Ä": "a",
        "Ö": "o",
        "Ü": "u",
    }
)


def normalize_text_for_matching(text: str) -> str:
    return text.translate(_MATCH_TRANSLATION).lower()


def tokenize_normalized_text(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text_for_matching(text))


def token_set(text: str) -> set[str]:
    return set(tokenize_normalized_text(text))
