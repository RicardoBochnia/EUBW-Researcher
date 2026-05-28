from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from eubw_researcher.models import TerminologyConfig
from eubw_researcher.retrieval.terminology import normalize_query_terms_with_trace
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "bei",
    "das",
    "der",
    "die",
    "ein",
    "eine",
    "for",
    "im",
    "in",
    "ist",
    "mit",
    "of",
    "oder",
    "the",
    "to",
    "und",
    "wann",
    "was",
    "welche",
    "wenn",
    "wie",
    "with",
    "zu",
    "kann",
    "nutzen",
    "statt",
    "entstehen",
}

GENERIC_ROLE_TERMS = {
    "attestation",
    "eidas",
    "eudi",
    "party",
    "parties",
    "provider",
    "providers",
    "relying",
    "service",
    "services",
    "wallet",
    "wallets",
}

DOMAIN_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "aendern": ("update", "status", "revocation", "suspension"),
    "aendert": ("update", "status", "revocation", "suspension"),
    "anbieter": ("provider",),
    "architektur": ("architecture",),
    "access": ("access",),
    "auditspur": ("audit", "trace", "log", "transaction"),
    "auditierbarkeit": ("audit", "traceability"),
    "aufbewahren": ("retain", "retention", "record", "records", "10 years"),
    "aufbewahrung": ("retain", "retention", "record", "records", "10 years"),
    "aussteller": ("issuer", "issue", "attestation provider", "credential issuer"),
    "ausstellers": ("issuer", "issue", "attestation provider", "credential issuer"),
    "ausgesetzt": ("suspend", "suspended", "suspension", "cancellation"),
    "ausstellung": ("issuance", "issued", "initial issuance"),
    "ausgestellt": ("issued", "initial issuance"),
    "authentifiziert": ("authenticated", "authentication"),
    "authentisiert": ("authenticated", "authentication"),
    "autorisiert": ("authorise", "authorised", "authorize", "authorized", "authorisation", "authorization"),
    "befugnis": ("authority", "authorisation", "authorization", "mandate", "powers"),
    "behoerden": ("authorities", "public sector bodies", "public authorities"),
    "behoerde": ("authority",),
    "benutzerkonto": ("user account", "resource owner", "end-user", "client"),
    "beschreiben": ("describe", "description", "certificate policy", "practice statement"),
    "betroffenen": ("affected",),
    "ca": ("ca", "certificate authority", "access ca", "access certificate authority"),
    "certificate": ("certificate", "certificate policy", "practice statement"),
    "client": ("client", "resource owner", "authorization server", "token endpoint"),
    "delegationskette": (
        "delegation",
        "chain",
        "mandate",
        "powers",
        "represent",
        "scope",
        "validity",
        "status",
        "revocation",
        "auditability",
    ),
    "dauerhaft": ("retention",),
    "englisch": ("english", "language", "description", "name"),
    "endnutzer": ("end-user", "resource owner"),
    "endnutzers": ("end-user", "resource owner"),
    "entfernen": ("remove", "removal", "cancellation", "withdrawal", "withdraw", "revoke", "revocation"),
    "ereignisspuren": ("event", "audit", "log", "transaction"),
    "ereignisse": ("event", "audit", "log"),
    "feldbeschreibung": ("field", "description", "attribute", "schema"),
    "feldbeschreibungen": ("field", "description", "attribute", "schema"),
    "finale": ("final",),
    "format": ("format", "schema"),
    "geloescht": ("cancel", "cancelled", "cancellation", "delete", "deleted"),
    "geltendes": ("binding", "final", "law"),
    "grenzueberschreitend": ("cross-border", "cross border", "eu", "european"),
    "grenzueberschreitende": ("cross-border", "cross border", "eu", "european"),
    "handlungsbefugnis": ("authority", "representation", "mandate", "powers"),
    "identitaetsabgleich": ("identity matching", "unequivocal matching", "identity", "matching"),
    "identitaetsmatching": ("identity matching", "unequivocal matching", "identity", "matching"),
    "identitaet": ("identity", "legal identity", "identification"),
    "immabescheinigung": ("enrolment", "enrollment", "student", "attestation", "credential", "certificate"),
    "immabescheinigungen": ("enrolment", "enrollment", "student", "attestation", "credential", "certificate"),
    "immatrikulationsbescheinigung": ("enrolment", "enrollment", "student", "attestation", "credential", "certificate"),
    "immatrikulationsbescheinigungen": ("enrolment", "enrollment", "student", "attestation", "credential", "certificate"),
    "inhalte": ("content", "payload"),
    "juristische": ("legal",),
    "log": ("log", "audit"),
    "logging": ("log", "audit"),
    "linkbar": ("linkable", "linkability", "unlinkability"),
    "linkbare": ("linkable", "linkability", "unlinkability"),
    "linkbaren": ("linkable", "linkability", "unlinkability"),
    "linkbares": ("linkable", "linkability", "unlinkability"),
    "lote": ("lote", "list of trusted entities", "trusted list", "trusted list provider"),
    "mandat": ("mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"),
    "mandate": ("mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"),
    "mandaten": ("mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"),
    "mandats": ("mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"),
    "mindest": ("minimum", "at least", "level of assurance"),
    "nachweis": ("credential", "attestation", "evidence"),
    "nachweise": ("credential", "attestation", "evidence"),
    "nachvollziehbarkeit": ("traceability", "audit"),
    "natuerliche": ("natural",),
    "oeffentliche": ("public sector", "public sector bodies", "public authorities"),
    "person": ("person",),
    "portabilitaet": ("portability", "migration", "export", "transfer", "migration object", "re-issuance", "rebinding", "device-bound"),
    "protokollieren": ("log", "audit"),
    "pseudonym": (
        "pseudonym",
        "pseudonyms",
        "pseudonymous authentication",
        "pseudonym generation",
        "wallet-relying party specific pseudonym",
    ),
    "pseudonyme": (
        "pseudonym",
        "pseudonyms",
        "pseudonymous authentication",
        "pseudonym generation",
        "wallet-relying party specific pseudonym",
    ),
    "pseudonymen": (
        "pseudonym",
        "pseudonyms",
        "pseudonymous authentication",
        "pseudonym generation",
        "wallet-relying party specific pseudonym",
    ),
    "pseudonymes": (
        "pseudonym",
        "pseudonyms",
        "pseudonymous authentication",
        "pseudonym generation",
        "wallet-relying party specific pseudonym",
    ),
    "pseudonymous": (
        "pseudonym",
        "pseudonyms",
        "pseudonymous authentication",
        "pseudonym generation",
    ),
    "pruefbarkeit": ("audit", "verification", "traceability"),
    "providers": ("provider",),
    "pubeaa": (
        "pubeaa",
        "public sector electronic attestation of attributes",
        "public sector body responsible for an authentic source",
        "electronic attestation of attributes issued by or on behalf of a public sector body",
        "Article 45f",
        "revocation",
        "validity",
    ),
    "pubeaas": (
        "pubeaa",
        "public sector electronic attestation of attributes",
        "public sector body responsible for an authentic source",
        "electronic attestation of attributes issued by or on behalf of a public sector body",
        "Article 45f",
        "revocation",
        "validity",
    ),
    "pruefer": ("verifier", "relying", "party"),
    "register": ("register", "registration", "authentic", "source"),
    "registerbetreiber": ("registrar", "register", "registration"),
    "registerdaten": ("register", "registration", "authentic", "source"),
    "recht": ("law", "regulation"),
    "regelwerk": ("rulebook", "catalogue", "attribute", "description"),
    "richtige": ("selection", "scope", "intended use", "purpose"),
    "richtigen": ("selection", "scope", "intended use", "purpose"),
    "rollen": ("roles", "client", "resource owner", "authorization server"),
    "rp": ("relying", "party", "wallet-relying-party"),
    "rulebook": ("rulebook", "catalogue", "attribute", "description"),
    "rulebooks": ("rulebook", "catalogue", "attribute", "description"),
    "sichtbar": ("visible", "display", "displayed", "shown"),
    "sichtbare": ("visible", "display", "displayed", "shown"),
    "sichtbaren": ("visible", "display", "displayed", "shown"),
    "sichtbares": ("visible", "display", "displayed", "shown"),
    "offenlegung": ("disclosure", "selective disclosure", "reveal identity", "identity disclosure"),
    "spezifikation": ("specification",),
    "spezifikationen": ("specification",),
    "stellen": ("bodies", "public sector bodies", "public authorities"),
    "streitfaelle": ("dispute", "investigation", "audit"),
    "studierendenausweis": ("student", "attestation", "credential", "status"),
    "technische": ("technical", "specification"),
    "unternehmensstatus": ("status", "revocation", "suspension", "cancellation"),
    "uebergangszeit": ("transition", "transitional", "communication solutions", "alternative communication"),
    "vertrauenskette": ("trust", "attestation", "trust-list", "wallet unit attestation", "wua", "device-bound"),
    "vertrauensmarke": ("trust mark", "wallet trust mark", "eudi wallet trust mark"),
    "vertrauenszeichen": ("trust mark", "wallet trust mark", "eudi wallet trust mark"),
    "vertretung": ("representation", "mandate", "authority", "powers", "represent"),
    "vertretungsrechte": ("representation", "mandate", "authority", "powers", "represent"),
    "vertrauensniveau": ("level of assurance", "assurance", "substantial level of assurance", "authentication"),
    "attributpraesentation": (
        "attribute presentation",
        "presentation of attributes",
        "selective disclosure",
        "claims",
        "credentials",
    ),
    "attributpraesentationen": (
        "attribute presentation",
        "presentation of attributes",
        "selective disclosure",
        "claims",
        "credentials",
    ),
    "authentifizierung": ("authentication", "authenticate"),
    "bindung": ("binding", "user binding", "cryptographic binding"),
    "account": ("account", "user account"),
    "account bindung": ("account binding", "user account binding", "user account"),
    "vorrang": ("priority", "authentic", "source"),
    "vorschlag": ("proposal",),
    "wechsel": ("migration", "transfer", "export", "portability", "migration object", "re-issuance", "rebinding"),
    "widerruf": ("revocation", "revoked"),
    "widerrufen": ("revocation", "revoked", "lose validity", "validity"),
    "widerrufsstatus": ("revocation status", "status", "validity"),
    "wodurch": ("how", "means", "mechanism"),
    "wrp": ("wallet-relying party", "registration", "access certificate", "registration certificate"),
    "zertifikate": ("certificates", "access certificates", "registration certificates"),
}


@dataclass(frozen=True)
class QueryExpansion:
    original_terms: tuple[str, ...]
    expanded_terms: tuple[str, ...]
    phrases: tuple[str, ...]
    term_weights: dict[str, float] = field(default_factory=dict)
    traces: tuple[dict[str, object], ...] = field(default_factory=tuple)

    @property
    def all_terms(self) -> tuple[str, ...]:
        return self.expanded_terms

    @property
    def distinctive_terms(self) -> tuple[str, ...]:
        return tuple(
            term
            for term in self.expanded_terms
            if term not in GENERIC_ROLE_TERMS and len(term) > 3
        )


def searchable_text(value: str) -> str:
    normalized = normalize_text_for_matching(value)
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def contains_term(surface: str, term: str) -> bool:
    normalized_term = searchable_text(term)
    if not normalized_term:
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", surface))


def _tokens(value: str) -> list[str]:
    normalized = normalize_text_for_matching(value)
    terms: list[str] = []
    seen: set[str] = set()
    for raw_term in re.findall(r"[a-z0-9][a-z0-9_-]{1,}", normalized):
        variants = [raw_term, *[part for part in re.split(r"[-_]+", raw_term) if part]]
        if raw_term.endswith("s") and not raw_term.endswith("ss") and len(raw_term) > 4:
            variants.append(raw_term[:-1])
        for term in variants:
            if term in seen or term in STOPWORDS:
                continue
            if len(term) < 3 and term not in DOMAIN_EXPANSIONS:
                continue
            seen.add(term)
            terms.append(term)
    return terms


def _append_unique(values: list[str], seen: set[str], items: Iterable[str]) -> None:
    for item in items:
        normalized = searchable_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)


def _question_phrases(terms: list[str]) -> list[str]:
    phrases: list[str] = []
    seen: set[str] = set()
    filtered = [term for term in terms if term not in STOPWORDS]
    for width in (3, 2):
        for index in range(0, len(filtered) - width + 1):
            phrase = " ".join(filtered[index : index + width])
            if phrase in seen:
                continue
            seen.add(phrase)
            phrases.append(phrase)
    return phrases


def _weight_for_term(term: str) -> float:
    if " " in term:
        return 2.0
    if term in GENERIC_ROLE_TERMS:
        return 0.28
    if len(term) >= 10:
        return 1.25
    return 1.0


def expand_query(
    question: str,
    terminology: TerminologyConfig | None = None,
) -> QueryExpansion:
    traces: list[dict[str, object]] = []
    terms = _tokens(question)
    if terminology is not None:
        normalized_question, applied = normalize_query_terms_with_trace(question, terminology)
        normalized_terms = _tokens(normalized_question)
        if normalized_terms != terms:
            traces.extend(
                {
                    "source_term": item.source_term,
                    "expanded_terms": [item.canonical_term],
                    "reason": "terminology_config",
                }
                for item in applied
            )
            terms = [*terms, *normalized_terms]

    values: list[str] = []
    seen: set[str] = set()
    _append_unique(values, seen, terms)
    for term in list(terms):
        aliases = DOMAIN_EXPANSIONS.get(term, ())
        if not aliases:
            continue
        _append_unique(values, seen, aliases)
        traces.append(
            {
                "source_term": term,
                "expanded_terms": [searchable_text(alias) for alias in aliases],
                "reason": "domain_alias",
            }
        )

    phrases: list[str] = []
    phrase_seen: set[str] = set()
    phrase_candidates = [
        value for value in values if " " in value
    ] + _question_phrases(terms)
    if "wallet" in values and any(term in values for term in ("trust mark", "vertrauenszeichen")):
        phrase_candidates.extend(["wallet trust mark", "eudi wallet trust mark"])
    if any(term in values for term in ("pseudonym", "pseudonyms")):
        phrase_candidates.extend(
            [
                "pseudonymous authentication",
                "pseudonym generation",
                "wallet-relying party specific pseudonym",
                "linkable pseudonymous authentication",
                "verifiable pseudonyms",
                "attested pseudonyms",
            ]
        )
    if "selective disclosure" in values or "attribute presentation" in values:
        phrase_candidates.extend(
            [
                "selective disclosure",
                "presentation of attributes",
                "strictly necessary claims",
                "minimal dataset",
            ]
        )
    if "linkability" in values or "unlinkability" in values:
        phrase_candidates.extend(
            [
                "relying party linkability",
                "verifier-to-verifier unlinkable presentations",
                "cross-party linkability",
            ]
        )
    _append_unique(phrases, phrase_seen, phrase_candidates)

    term_weights = {term: _weight_for_term(term) for term in values}
    for phrase in phrases:
        term_weights.setdefault(phrase, _weight_for_term(phrase))

    return QueryExpansion(
        original_terms=tuple(dict.fromkeys(terms)),
        expanded_terms=tuple(values),
        phrases=tuple(phrases),
        term_weights=term_weights,
        traces=tuple(traces),
    )
