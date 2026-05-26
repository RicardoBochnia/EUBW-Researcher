from __future__ import annotations

from collections.abc import Iterable

from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


_FACET_TERMS: dict[str, tuple[str, ...]] = {
    "actor_boundary": (
        "auseinanderhalten",
        "trennen",
        "unterscheiden",
        "boundary",
        "role",
        "rolle",
        "intermediaer",
        "intermediary",
        "on behalf",
        "acting for",
    ),
    "technical_requester": (
        "intermediaer",
        "intermediary",
        "technisch",
        "technical",
        "request",
        "presentation request",
        "access certificate",
    ),
    "end_relying_party": (
        "wallet relying party",
        "wallet-relying party",
        "relying party",
        "end relying party",
        "intermediated relying party",
        "end-rp",
    ),
    "registry_information": (
        "registrierung",
        "registration",
        "register",
        "registrar",
        "registry",
        "registered information",
    ),
    "user_display": (
        "nutzeranzeige",
        "anzeige",
        "display",
        "user display",
        "informs the user",
        "wallet unit informs",
        "user approval",
    ),
    "purpose_or_intended_use": (
        "zweck",
        "purpose",
        "intended use",
        "intendeduse",
        "use case",
    ),
    "requested_attributes": (
        "attribute",
        "attributes",
        "attestation",
        "attestationen",
        "daten",
        "data",
        "claim",
        "credential",
    ),
    "privacy_policy_or_dpa": (
        "datenschutz",
        "privacy",
        "privacy policy",
        "dpa",
        "complaint",
        "beschwerde",
        "deletion",
        "loesch",
    ),
    "certificate_or_trust_anchor": (
        "certificate",
        "zertifikat",
        "access certificate",
        "registration certificate",
        "rpac",
        "rprc",
        "wrprc",
        "trust anchor",
    ),
    "open_issue_or_member_state_choice": (
        "open issue",
        "offen",
        "member state",
        "mitgliedstaat",
        "where applicable",
        "if applicable",
        "may require",
    ),
}


def _normalized_terms(terms: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        normalized
        for term in terms
        if (normalized := normalize_text_for_matching(term))
    )


_NORMALIZED_FACET_TERMS = {
    facet: _normalized_terms(terms) for facet, terms in _FACET_TERMS.items()
}


def detect_question_facets(question: str) -> list[str]:
    """Return reusable semantic facets that should constrain evidence synthesis."""

    surface = normalize_text_for_matching(question)
    facets = [
        facet
        for facet, terms in _NORMALIZED_FACET_TERMS.items()
        if any(term in surface for term in terms)
    ]
    if "intermediaer" in surface or "intermediary" in surface:
        for implied in ("actor_boundary", "technical_requester", "end_relying_party"):
            if implied not in facets:
                facets.append(implied)
    if "wallet relying party" in surface or "wallet-relying party" in surface:
        if "end_relying_party" not in facets:
            facets.append("end_relying_party")
    return facets


def facet_hits_for_text(text: str, facets: Iterable[str] | None = None) -> dict[str, list[str]]:
    surface = normalize_text_for_matching(text)
    candidate_facets = list(facets or _NORMALIZED_FACET_TERMS.keys())
    hits: dict[str, list[str]] = {}
    for facet in candidate_facets:
        terms = _NORMALIZED_FACET_TERMS.get(facet, ())
        matched = [term for term in terms if term in surface]
        if matched:
            hits[facet] = matched
    return hits


def facet_tags_for_text(text: str, facets: Iterable[str] | None = None) -> list[str]:
    return sorted(facet_hits_for_text(text, facets).keys())


def facet_coverage_score(text: str, facets: Iterable[str]) -> float:
    facet_list = list(facets)
    if not facet_list:
        return 0.0
    hits = facet_hits_for_text(text, facet_list)
    return len(hits) / len(facet_list)

