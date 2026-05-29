from __future__ import annotations

from collections.abc import Iterable

from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


_FACET_TERMS: dict[str, tuple[str, ...]] = {
    "trust_mark_meaning": (
        "wallet trust mark",
        "eudi wallet trust mark",
        "trust mark",
        "vertrauenszeichen",
        "vertrauensmarke",
        "visible trust mark",
        "visible",
        "sichtbar",
        "meaning",
        "bedeutet",
        "nutzer",
        "users",
    ),
    "trust_mark_removal": (
        "wallet trust mark",
        "eudi wallet trust mark",
        "trust mark",
        "vertrauenszeichen",
        "vertrauensmarke",
        "remove",
        "removal",
        "entfernen",
        "aufhebung",
        "cancellation",
        "withdraw",
        "withdrawal",
        "widerruf",
        "revocation",
    ),
    "trust_mark_scope_boundary": (
        "wallet trust mark",
        "eudi wallet trust mark",
        "trust mark",
        "vertrauenszeichen",
        "vertrauensmarke",
        "scope",
        "out of scope",
        "relying party",
        "relying parties",
        "attestation provider",
        "attestation providers",
        "bewertet",
        "bewertung",
    ),
    "actor_boundary": (
        "auseinanderhalten",
        "trennen",
        "unterscheiden",
        "boundary",
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
        "welche informationen",
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
    "wallet_solution_certification": (
        "certification",
        "zertifizierung",
        "certification scheme",
        "conformity assessment",
        "wallet solution certification",
        "certification of european digital identity wallets",
        "eudi wallet loesungen",
        "eudi-wallet-loesungen",
    ),
    "protocol_security_parameter": (
        "openid4vp",
        "openid for verifiable presentations",
        "authorization request",
        "authorization response",
        "response uri",
        "response_uri",
        "direct post",
        "direct_post",
        "state",
        "nonce",
        "wallet nonce",
        "wallet_nonce",
        "request id",
        "request-id",
        "transaction id",
        "transaction-id",
        "csrf",
        "replay",
    ),
    "open_issue_or_member_state_choice": (
        "open issue",
        "offene frage",
        "offener punkt",
        "offen bleibt",
        "member state",
        "mitgliedstaat",
        "where applicable",
        "if applicable",
        "may require",
    ),
    "pseudonym_legal_permission": (
        "pseudonym",
        "pseudonyme",
        "pseudonymen",
        "pseudonymous",
        "pseudonymous authentication",
        "legal identity",
        "identity disclosure",
    ),
    "pseudonym_account_binding": (
        "account binding",
        "account-bindung",
        "user account",
        "scope unique",
        "specific and unique",
        "user binding",
        "cryptographic binding",
    ),
    "attribute_presentation_limit": (
        "attribute presentation",
        "attributpraesentation",
        "presentation of attributes",
        "selective disclosure",
        "disclose attributes",
        "requested attributes",
        "strictly necessary claims",
    ),
    "linkability_risk": (
        "linkable",
        "linkbaren",
        "linkability",
        "unlinkability",
        "unlinkable",
        "cross-party",
        "relying party linkability",
        "verifier-to-verifier",
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

_TRUST_MARK_TERMS = _normalized_terms(
    (
        "wallet trust mark",
        "eudi wallet trust mark",
        "trust mark",
        "vertrauenszeichen",
        "vertrauensmarke",
    )
)
_TRUST_MARK_REMOVAL_TERMS = _normalized_terms(
    (
        "remove",
        "removal",
        "entfernen",
        "aufhebung",
        "cancellation",
        "withdraw",
        "withdrawal",
        "widerruf",
        "revocation",
    )
)
_TRUST_MARK_SCOPE_TERMS = _normalized_terms(
    (
        "scope",
        "out of scope",
        "relying party",
        "relying parties",
        "attestation provider",
        "attestation providers",
        "bewertet",
        "bewertung",
    )
)
_WALLET_CERTIFICATION_TERMS = _normalized_terms(
    (
        "certification",
        "zertifizierung",
        "certification scheme",
        "conformity assessment",
    )
)
_WALLET_SOLUTION_TERMS = _normalized_terms(
    (
        "wallet solution",
        "wallet solutions",
        "wallet loesung",
        "wallet loesungen",
        "eudi wallet",
        "eudi-wallet",
    )
)
_PROTOCOL_PARAMETER_TERMS = _normalized_terms(
    (
        "state",
        "nonce",
        "wallet nonce",
        "wallet_nonce",
        "request id",
        "request-id",
        "transaction id",
        "transaction-id",
    )
)
_PROTOCOL_CONTEXT_TERMS = _normalized_terms(
    (
        "openid4vp",
        "openid for verifiable presentations",
        "authorization request",
        "authorization response",
        "response uri",
        "response_uri",
        "direct post",
        "direct_post",
        "csrf",
        "replay",
        "cross-site request forgery",
        "session fixation",
        "verifiable presentation",
        "holder binding",
        "oauth",
    )
)


def _surface_has_trust_mark(surface: str) -> bool:
    return any(term in surface for term in _TRUST_MARK_TERMS)


def _surface_has_any(surface: str, terms: tuple[str, ...]) -> bool:
    return any(term in surface for term in terms)


def _surface_has_protocol_term(surface: str, term: str) -> bool:
    if term in {"state", "nonce", "csrf", "replay", "oauth"}:
        return f" {term} " in f" {surface} "
    return term in surface


def _surface_has_any_protocol_term(surface: str, terms: tuple[str, ...]) -> bool:
    return any(_surface_has_protocol_term(surface, term) for term in terms)


def _trust_mark_facets_for_surface(surface: str) -> list[str]:
    if not _surface_has_trust_mark(surface):
        return []
    facets = ["trust_mark_meaning"]
    if _surface_has_any(surface, _TRUST_MARK_REMOVAL_TERMS):
        facets.append("trust_mark_removal")
    if _surface_has_any(surface, _TRUST_MARK_SCOPE_TERMS):
        facets.append("trust_mark_scope_boundary")
    return facets


def _surface_has_requested_attribute_term(surface: str, terms: tuple[str, ...]) -> bool:
    padded = f" {surface} "
    for term in terms:
        if term in {"data", "daten"}:
            if f" {term} " in padded:
                return True
            continue
        if term in surface:
            return True
    return False


def _surface_has_protocol_security_parameter(surface: str) -> bool:
    has_nonce_or_identifier = _surface_has_any_protocol_term(
        surface,
        tuple(term for term in _PROTOCOL_PARAMETER_TERMS if term != "state"),
    )
    has_state_protocol_context = _surface_has_protocol_term(surface, "state") and _surface_has_any_protocol_term(
        surface,
        (
            "openid4vp",
            "openid for verifiable presentations",
            "authorization request",
            "authorization response",
            "response uri",
            "response_uri",
            "direct post",
            "direct_post",
            "csrf",
            "replay",
        ),
    )
    has_context = _surface_has_any_protocol_term(surface, _PROTOCOL_CONTEXT_TERMS)
    return (has_nonce_or_identifier or has_state_protocol_context) and has_context


def detect_question_facets(question: str) -> list[str]:
    """Return reusable semantic facets that should constrain evidence synthesis."""

    surface = normalize_text_for_matching(question)
    facets: list[str] = []
    for facet, terms in _NORMALIZED_FACET_TERMS.items():
        if facet.startswith("trust_mark_"):
            if facet in _trust_mark_facets_for_surface(surface):
                facets.append(facet)
            continue
        if facet == "wallet_solution_certification":
            if _surface_has_any(surface, _WALLET_CERTIFICATION_TERMS) and _surface_has_any(
                surface,
                _WALLET_SOLUTION_TERMS,
            ):
                facets.append(facet)
            continue
        if facet == "protocol_security_parameter":
            if _surface_has_protocol_security_parameter(surface):
                facets.append(facet)
            continue
        if facet == "requested_attributes":
            attribute_surface = surface.replace("attestation provider", "")
            attribute_surface = attribute_surface.replace("attestation providern", "")
            if _surface_has_requested_attribute_term(attribute_surface, terms):
                facets.append(facet)
            continue
        if any(term in surface for term in terms):
            facets.append(facet)
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
        if facet.startswith("trust_mark_"):
            if facet not in _trust_mark_facets_for_surface(surface):
                continue
            matched = [term for term in terms if term in surface]
            if matched:
                hits[facet] = matched
            continue
        if facet == "wallet_solution_certification":
            matched = [
                term
                for term in terms
                if term in surface
                and _surface_has_any(surface, _WALLET_CERTIFICATION_TERMS)
                and _surface_has_any(surface, _WALLET_SOLUTION_TERMS)
            ]
            if matched:
                hits[facet] = matched
            continue
        if facet == "protocol_security_parameter":
            if not _surface_has_protocol_security_parameter(surface):
                continue
            matched = [term for term in terms if _surface_has_protocol_term(surface, term)]
            if matched:
                hits[facet] = matched
            continue
        if facet == "requested_attributes":
            matched = [
                term
                for term in terms
                if (
                    f" {term} " in f" {surface} "
                    if term in {"data", "daten"}
                    else term in surface
                )
            ]
        else:
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
