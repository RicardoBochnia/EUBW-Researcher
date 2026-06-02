from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

from eubw_researcher.knowledge.query_expansion import expand_query
from eubw_researcher.knowledge.question_facets import detect_question_facets
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


_GENERIC_TERMS = {
    "about",
    "auch",
    "before",
    "beim",
    "braucht",
    "durch",
    "einer",
    "einem",
    "einen",
    "fuer",
    "gegen",
    "have",
    "interagiert",
    "interaktionen",
    "oder",
    "rund",
    "sagt",
    "spielen",
    "ueber",
    "und",
    "wallet",
    "wallets",
    "welche",
    "wenn",
    "what",
    "with",
}

_GENERIC_SEMANTIC_TERMS = {
    "attestation",
    "content",
    "credential",
    "evidence",
    "payload",
    "provider",
    "registration",
    "service",
    "source",
    "wallet",
}

_TOPIC_ANCHORS: dict[str, tuple[str, ...]] = {
    "trust_mark": (
        "trust mark",
        "wallet trust mark",
        "eudi wallet trust mark",
        "ec_ts01_wallet_trust_mark",
        "wallettrustmarkinformation",
        "vertrauenszeichen",
        "vertrauensmarke",
    ),
    "wallet_solution_certification": (
        "certification of european digital identity wallets",
        "wallet solution certification",
        "wallet solutions",
        "wallet solution",
        "european digital identity wallets",
        "european digital identity wallet",
        "certified european digital identity wallet",
        "national certification schemes",
        "certification assessment report",
        "zertifizierung",
    ),
    "openidvp_security_parameter": (
        "openid4vp",
        "openid for verifiable presentations",
        "rfc6749",
        "oauth 2 0",
        "cross site request forgery",
        "csrf",
        "response uri",
        "response_uri",
        "authorization response",
        "authorization request",
        "preventing replay",
    ),
    "wallet_unit_attestation": (
        "wallet unit attestation",
        "wallet unit attestations",
        "ec_ts03_wallet_unit_attestation",
        "transport of wua",
        "wuas",
        " wua ",
    ),
    "wallet_unit_attestation_issuer": (
        "issuer credential metadata",
        "pid provider",
        "pid providers",
        "attestation provider",
        "attestation providers",
        "issuing party",
        "issuance of pid and attestations",
        "proof_types_supported",
        "key_attestation_required",
        "wallet providers issue wuas",
        "outside this technical specification",
        "out of scope",
    ),
    "wallet_provider_portability": (
        "ec_ts03_wallet_unit_attestation",
        "ec_ts10_data_portability_export",
        "wallet unit attestation",
        "wallet unit attestations",
        "transport of wua",
        "data portability and download export",
        "migrationobject",
        "migration object",
    ),
    "pseudonym_use_boundary": (
        "celex_32024r2979",
        "eudi_arf_main_markdown",
        "openid4vp_1_0_official",
        "pseudonym",
        "pseudonyms",
        "pseudonymous authentication",
        "specific and unique",
        "selective disclosure",
        "strictly necessary claims",
        "linkability",
        "unlinkability",
    ),
    "identity_matching": (
        "celex_32025r0846",
        "cross-border identity matching",
        "unequivocal identity matching",
        "identity matching",
        "identitaetsabgleich",
        "identitaetsmatching",
    ),
    "audit_log_boundary": (
        "celex_32024r2979",
        "transaction log",
        "transaction logs",
        "logging transactions",
        "event log",
        "audit trail",
        "traceability of previous transactions",
    ),
    "authentic_source_priority": (
        "celex_32024r1183",
        "celex_32025r1569",
        "authentic source",
        "authentic sources",
        "definitive repository",
    ),
    "qualified_trust_service_lists": (
        "celex_32025d2164",
        "trusted lists",
        "trusted list",
        "vertrauenswuerdige listen",
        "vertrauenswuerdigen listen",
    ),
    "attestation_rulebook_catalogue": (
        "ec_ts11_catalogue_attributes_schemes",
        "attestation rulebook",
        "attestation rulebooks",
        "attestation schemas",
        "catalogue of attributes",
        "catalogue of attestations",
        "attribute catalogue",
    ),
    "delegation_chain": (
        "delegation chain",
        "delegationskette",
        "subdelegation",
        "powers and mandates",
        "mandates to represent",
        "scope validity and constraints",
        "catalogue of attestations",
        "ec_ts11_catalogue_attributes_schemes",
    ),
    "ebw_governance_status": (
        "european business wallet",
        "european business wallets",
        "business wallet",
        "business wallets",
        "ebw",
        "proposal",
        "annex",
        "technical assumption",
        "technische annahme",
        "entwurfsstand",
    ),
    "ebw_public_service_boundary": (
        "european business wallet",
        "european business wallets",
        "business wallet",
        "business wallets",
        "ebw",
        "qualified electronic registered delivery service",
        "qerds",
    ),
}

_TOPIC_SOURCE_IDS: dict[str, tuple[str, ...]] = {
    "wallet_provider_portability": (
        "ec_ts03_wallet_unit_attestation",
        "ec_ts10_data_portability_export",
    ),
    "pseudonym_use_boundary": (
        "celex_32024R2979_fulltext_en",
        "eudi_arf_main_markdown",
        "openid4vp_1_0_official",
    ),
    "identity_matching": (
        "celex_32025R0846_fulltext_en",
        "celex_32024R1183_fulltext_en",
    ),
    "audit_log_boundary": (
        "celex_32024R2979_fulltext_en",
        "eudi_arf_main_markdown",
        "ec_ts07_data_deletion_interface",
        "ec_ts08_dpa_complaints_interface",
        "ec_ts10_data_portability_export",
    ),
    "authentic_source_priority": (
        "celex_32024R1183_fulltext_en",
        "celex_32025R1569_fulltext_en",
        "eudi_arf_main_markdown",
        "ec_ts11_catalogue_attributes_schemes",
    ),
    "delegation_chain": (
        "ec_ts11_catalogue_attributes_schemes",
        "celex_32024R1183_fulltext_en",
        "eudi_arf_main_markdown",
    ),
    "ebw_governance_status": (
        "ebw_proposal_com_2025_0838",
        "ebw_annex_com_2025_0838",
        "celex_32024R1183_fulltext_en",
    ),
}


@dataclass(frozen=True)
class EvidenceRelevanceDecision:
    relevant: bool
    score: int
    topics: tuple[str, ...]
    matched_topics: tuple[str, ...]
    matched_terms: tuple[str, ...]
    reason: str


def _contains(surface: str, term: str) -> bool:
    if term == " wua ":
        return " wua " in f" {surface} "
    return normalize_text_for_matching(term) in surface


def _question_topics(question: str) -> tuple[str, ...]:
    surface = normalize_text_for_matching(question)
    facets = set(detect_question_facets(question))
    topics: list[str] = []
    provider_portability = (
        any(term in surface for term in ("wallet-provider", "wallet provider"))
        and any(
            term in surface
            for term in (
                "wechsel",
                "portabilitaet",
                "portability",
                "migration",
                "export",
            )
        )
    )
    if facets.intersection(
        {"trust_mark_meaning", "trust_mark_removal", "trust_mark_scope_boundary"}
    ):
        topics.append("trust_mark")
    if "wallet_solution_certification" in facets:
        topics.append("wallet_solution_certification")
    if "protocol_security_parameter" in facets:
        topics.append("openidvp_security_parameter")
    if (
        "wallet unit attestation" in surface
        or "wallet-unit-attestation" in surface
        or re.search(r"\bwua(?:s)?\b", surface)
    ):
        topics.append("wallet_unit_attestation")
        if any(
            term in surface
            for term in (
                "aussteller",
                "issuer",
                "pid",
                "attribut",
                "pruefung",
                "pruefungen",
            )
        ):
            topics.append("wallet_unit_attestation_issuer")
    if provider_portability:
        topics.append("wallet_provider_portability")
    if "pseudonym" in surface or "pseudonyme" in surface:
        topics.append("pseudonym_use_boundary")
    if (
        "identity matching" in surface
        or "identitaetsabgleich" in surface
        or "identitaetsmatching" in surface
    ):
        topics.append("identity_matching")
    if (
        not provider_portability
        and any(
            term in surface
            for term in (
                "audit",
                "auditierbarkeit",
                "auditspur",
                "ereignisspur",
                "protokollier",
                "transaction log",
            )
        )
    ):
        topics.append("audit_log_boundary")
    if (
        any(term in surface for term in ("registerdaten", "authentic source", "authentische quelle"))
        and any(
            term in surface
            for term in (
                "auseinanderfallen",
                "conflict",
                "konflikt",
                "priority",
                "vorrang",
            )
        )
    ):
        topics.append("authentic_source_priority")
    if (
        "trusted list" in surface
        or "vertrauenswuerdige listen" in surface
        or "vertrauenswuerdigen listen" in surface
    ):
        topics.append("qualified_trust_service_lists")
    if (
        "ts11" in surface
        or "attestation rulebook" in surface
        or (
            ("katalog" in surface or "catalogue" in surface)
            and (
                "attributschema" in surface
                or "attribute" in surface
                or "attestation" in surface
            )
        )
    ):
        topics.append("attestation_rulebook_catalogue")
    if (
        any(
            term in surface
            for term in (
                "delegationskette",
                "delegation chain",
                "subdelegation",
            )
        )
        or (
            "delegation" in surface
            and any(term in surface for term in ("mehrstufig", "multi-stage", "chain", "kette"))
        )
    ):
        topics.append("delegation_chain")
    if (
        any(term in surface for term in ("business wallet", "ebw"))
        and any(
            term in surface
            for term in (
                "geltendes recht",
                "current law",
                "final law",
                "proposal",
                "vorschlag",
                "technical assumption",
                "technische annahme",
                "qualifizier",
            )
        )
    ):
        topics.append("ebw_governance_status")
    if (
        any(term in surface for term in ("business wallet", "ebw"))
        and any(
            term in surface
            for term in (
                "behoerde",
                "behoerden",
                "public sector",
                "communication",
                "kommunikation",
                "channel",
                "kanal",
                "qerds",
            )
        )
    ):
        topics.append("ebw_public_service_boundary")
    return tuple(dict.fromkeys(topics))


def _topic_matches(topic: str, surface: str) -> bool:
    if topic == "wallet_solution_certification":
        if "celex_32024r2981" in surface:
            return True
        if "ec_ts01_wallet_trust_mark" in surface:
            return "non-certified" in surface or "revoked at solution" in surface
        has_certification = any(
            term in surface
            for term in (
                "certification",
                "certified",
                "non-certified",
                "zertifizierung",
                "konformitaet",
                "conformity",
            )
        )
        has_wallet_solution = any(
            term in surface
            for term in (
                "wallet solution",
                "eudi wallet solution",
                "european digital identity wallet",
            )
        )
        return has_certification and has_wallet_solution
    if topic == "openidvp_security_parameter":
        return (
            "openid4vp" in surface
            or "openid for verifiable presentations" in surface
            or (
                ("rfc6749" in surface or "oauth 2 0" in surface or "oauth" in surface)
                and ("csrf" in surface or "cross site request forgery" in surface)
            )
        )
    if topic == "wallet_provider_portability":
        if (
            "ec_ts10_data_portability_export" in surface
            or "data portability and download export" in surface
            or "migrationobject" in surface
            or "migration object" in surface
        ):
            return True
        return (
            "ec_ts03_wallet_unit_attestation" in surface
            and any(
                term in surface
                for term in (
                    "transport of wua",
                    "wallet providers responsibilities",
                    "revocation mechanism",
                    "validity period of the wua",
                    "device-bound",
                    "key_attestation",
                    "attested keys",
                    "cannot be re-issued",
                )
            )
        )
    if topic == "pseudonym_use_boundary":
        if "celex_32024r2979" in surface:
            return "pseudonym" in surface
        if "eudi_arf_main_markdown" in surface:
            return any(
                term in surface
                for term in (
                    "pseudonym",
                    "pseudonymous authentication",
                    "linkability",
                    "unlinkability",
                )
            )
        if "openid4vp_1_0_official" in surface:
            return any(
                term in surface
                for term in (
                    "selective disclosure",
                    "strictly necessary claims",
                    "unlinkable presentations",
                    "linkability",
                )
            )
        return any(
            term in surface
            for term in (
                "pseudonym generation",
                "specific and unique",
                "wallet-relying party specific pseudonym",
            )
        )
    if topic == "identity_matching":
        return (
            "celex_32025r0846" in surface
            or "cross-border identity matching" in surface
            or "unequivocal identity matching" in surface
            or "identity matching" in surface
        )
    if topic == "audit_log_boundary":
        return any(
            term in surface
            for term in (
                "transaction log",
                "transaction logs",
                "logging transactions",
                "event log",
                "audit trail",
                "traceability of previous transactions",
            )
        )
    if topic == "authentic_source_priority":
        return (
            (
                "celex_32024r1183" in surface
                or "celex_32025r1569" in surface
                or "eudi_arf_main_markdown" in surface
                or "ec_ts11_catalogue_attributes_schemes" in surface
            )
            and "authentic source" in surface
        )
    if topic == "qualified_trust_service_lists":
        return (
            "celex_32025d2164" in surface
            or (
                "implementing decision" in surface
                and ("trusted list" in surface or "trusted lists" in surface)
                and "common template" in surface
            )
        )
    if topic == "attestation_rulebook_catalogue":
        return (
            "ec_ts11_catalogue_attributes_schemes" in surface
            or (
                any(
                    term in surface
                    for term in (
                        "attestation rulebook",
                        "attestation rulebooks",
                        "attestation schemas",
                    )
                )
                and (
                    "catalogue" in surface
                    or "catalog" in surface
                )
            )
            or "catalogue of attributes" in surface
            or "catalogue of attestations" in surface
        )
    if topic == "delegation_chain":
        if "ec_ts11_catalogue_attributes_schemes" in surface:
            return any(
                term in surface
                for term in (
                    "powers and mandates",
                    "revocation mechanisms",
                )
            )
        if "celex_32024r1183" in surface:
            return any(term in surface for term in ("mandate", "power of attorney", "representation"))
        if "eudi_arf_main_markdown" in surface:
            return any(term in surface for term in ("mandate", "representing another", "representation"))
        return (
            any(term in surface for term in ("delegation", "subdelegation", "delegationskette"))
            and any(term in surface for term in ("chain", "kette", "mandate", "attestation"))
        )
    if topic == "ebw_governance_status":
        return (
            "ebw_proposal_com_2025_0838" in surface
            or "ebw_annex_com_2025_0838" in surface
            or (
                "celex_32024r1183" in surface
                and "european digital identity wallet" in surface
            )
            or (
                any(term in surface for term in ("european business wallet", "business wallet", "ebw"))
                and any(term in surface for term in ("proposal", "annex", "entwurfsstand"))
            )
        )
    return any(_contains(surface, anchor) for anchor in _TOPIC_ANCHORS[topic])


def _distinctive_question_terms(question: str) -> tuple[str, ...]:
    surface = normalize_text_for_matching(question)
    terms: list[str] = []
    seen: set[str] = set()
    for term in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", surface):
        if term in seen or term in _GENERIC_TERMS:
            continue
        seen.add(term)
        terms.append(term)
    return tuple(terms)


def _semantic_question_matches(question: str, surface: str) -> tuple[str, ...]:
    expansion = expand_query(question)
    original_terms = set(_distinctive_question_terms(question))
    terms = [
        term
        for term in expansion.distinctive_terms
        if term not in original_terms and term not in _GENERIC_SEMANTIC_TERMS
    ]
    return tuple(
        term
        for term in terms
        if _contains(surface, term)
    )


def _has_sufficient_semantic_overlap(matches: Sequence[str]) -> bool:
    return any(" " in term for term in matches) or len(set(matches)) >= 2


def evidence_relevance_decision(
    question: str,
    evidence_surface: str,
    *,
    require_original_overlap: bool = True,
) -> EvidenceRelevanceDecision:
    surface = normalize_text_for_matching(evidence_surface)
    topics = _question_topics(question)
    matched_topics = tuple(
        topic
        for topic in topics
        if _topic_matches(topic, surface)
    )
    missing_topics = tuple(topic for topic in topics if topic not in matched_topics)
    terms = _distinctive_question_terms(question)
    matched_terms = tuple(term for term in terms if term in surface)
    semantic_matches = _semantic_question_matches(question, surface)
    score = len(matched_topics) * 100 + min(40, len(matched_terms) * 8)

    if missing_topics:
        return EvidenceRelevanceDecision(
            relevant=False,
            score=score,
            topics=topics,
            matched_topics=matched_topics,
            matched_terms=matched_terms,
            reason="missing constrained topic anchors: " + ", ".join(missing_topics),
        )
    if topics:
        return EvidenceRelevanceDecision(
            relevant=True,
            score=score,
            topics=topics,
            matched_topics=matched_topics,
            matched_terms=matched_terms,
            reason="matched constrained topic anchors",
        )
    if (
        require_original_overlap
        and terms
        and not matched_terms
        and not _has_sufficient_semantic_overlap(semantic_matches)
    ):
        return EvidenceRelevanceDecision(
            relevant=False,
            score=score,
            topics=topics,
            matched_topics=matched_topics,
            matched_terms=matched_terms,
            reason="no distinctive original-question term or semantic multi-match matched",
        )
    return EvidenceRelevanceDecision(
        relevant=True,
        score=score,
        topics=topics,
        matched_topics=matched_topics,
        matched_terms=matched_terms,
        reason="matched original-question surface or no narrow topic constraint applies",
    )


def evidence_record_surface(record: object) -> str:
    return " ".join(
        [
            str(getattr(record, "snippet", "") or ""),
            str(getattr(record, "statement", "") or ""),
            str(getattr(record, "locator", "") or ""),
            " ".join(str(value) for value in (getattr(record, "locators", []) or [])),
            str(getattr(record, "source_id", "") or ""),
            " ".join(str(value) for value in (getattr(record, "source_ids", []) or [])),
            str(getattr(record, "cluster_id", "") or ""),
        ]
    )


def evidence_record_is_relevant(question: str, record: object) -> bool:
    decision = evidence_relevance_decision(
        question,
        evidence_record_surface(record),
    )
    if not decision.relevant or not decision.topics:
        return decision.relevant
    content_surface = " ".join(
        [
            str(getattr(record, "snippet", "") or ""),
            str(getattr(record, "statement", "") or ""),
            str(getattr(record, "source_id", "") or ""),
            " ".join(str(value) for value in (getattr(record, "source_ids", []) or [])),
        ]
    )
    return evidence_relevance_decision(question, content_surface).relevant


def source_entry_is_relevant(
    question: str,
    source: object,
    *,
    aliases: Iterable[str] = (),
) -> bool:
    surface = " ".join(
        [
            str(getattr(source, "source_id", "") or ""),
            str(getattr(source, "title", "") or ""),
            str(getattr(source, "source_kind", "") or ""),
            str(getattr(source, "publication_status", "") or ""),
            str(getattr(source, "source_family_id", "") or ""),
            " ".join(str(alias) for alias in aliases),
        ]
    )
    decision = evidence_relevance_decision(
        question,
        surface,
        require_original_overlap=False,
    )
    if decision.relevant:
        return True
    source_id = str(getattr(source, "source_id", "") or "")
    return bool(decision.topics) and all(
        topic in decision.matched_topics
        or source_id in _TOPIC_SOURCE_IDS.get(topic, ())
        for topic in decision.topics
    )


def ledger_entry_surface(entry: object) -> str:
    citations = getattr(entry, "citations", []) or []
    evidence = [
        *list(getattr(entry, "supporting_evidence", []) or []),
        *list(getattr(entry, "governing_evidence", []) or []),
        *list(getattr(entry, "contradicting_evidence", []) or []),
    ]
    return " ".join(
        [
            str(getattr(entry, "claim_text", "") or ""),
            str(getattr(entry, "claim_id", "") or ""),
            *[
                " ".join(
                    [
                        str(getattr(citation, "source_id", "") or ""),
                        str(getattr(citation, "document_title", "") or ""),
                        str(getattr(citation, "anchor_label", "") or ""),
                    ]
                )
                for citation in citations
            ],
            *[
                " ".join(
                    [
                        str(getattr(getattr(item, "citation", None), "source_id", "") or ""),
                        str(getattr(getattr(item, "citation", None), "document_title", "") or ""),
                        str(getattr(getattr(item, "citation", None), "anchor_label", "") or ""),
                    ]
                )
                for item in evidence
            ],
        ]
    )


def ledger_entry_claim_surface(entry: object) -> str:
    return " ".join(
        [
            str(getattr(entry, "claim_text", "") or ""),
            str(getattr(entry, "claim_id", "") or ""),
        ]
    )


def _looks_like_reference_catalog(surface: str) -> bool:
    return (
        surface.count("http") >= 3
        or (
            surface.count("#") >= 5
            and sum(marker in surface.casefold() for marker in ("oidf", "ietf", "etsi", "done")) >= 2
        )
    )


def ledger_entry_is_relevant(question: str, entry: object) -> bool:
    surface = ledger_entry_surface(entry)
    if _looks_like_reference_catalog(surface):
        return False
    decision = evidence_relevance_decision(
        question,
        ledger_entry_claim_surface(entry),
        require_original_overlap=False,
    )
    if not decision.relevant:
        return False
    if not str(getattr(entry, "claim_id", "") or "").startswith("dynamic_"):
        return True
    citations = getattr(entry, "citations", []) or []
    return any(
        evidence_relevance_decision(
            question,
            " ".join(
                [
                    str(getattr(citation, "source_id", "") or ""),
                    str(getattr(citation, "document_title", "") or ""),
                    str(getattr(citation, "anchor_label", "") or ""),
                ]
            ),
            require_original_overlap=False,
        ).relevant
        for citation in citations
    )


def claim_surface_is_relevant(
    question: str,
    *,
    statement: str,
    source_ids: Sequence[str] = (),
    extra_values: Sequence[str] = (),
) -> bool:
    surface = " ".join([statement, *source_ids, *extra_values])
    if _looks_like_reference_catalog(surface):
        return False
    return evidence_relevance_decision(
        question,
        surface,
    ).relevant


def build_gap_discovery_query(
    question: str,
    *,
    question_facets: Sequence[str],
    gap_reason: str,
    target_terms: Sequence[str],
) -> str:
    normalized_question = normalize_text_for_matching(question)
    topics = _question_topics(question)
    safe_terms: list[str] = []
    for term in target_terms:
        normalized_term = normalize_text_for_matching(term)
        if not normalized_term or len(normalized_term) > 72:
            continue
        if normalized_term in normalized_question or any(
            _contains(normalized_term, anchor)
            or _contains(anchor, normalized_term)
            for topic in topics
            for anchor in _TOPIC_ANCHORS[topic]
        ):
            safe_terms.append(normalized_term)
    safe_terms = list(dict.fromkeys(safe_terms))[:8]
    facets = list(
        dict.fromkeys(
            [
                *(str(facet) for facet in question_facets if facet),
                *topics,
            ]
        )
    )[:8]
    parts = [
        question.strip(),
        "Facets: " + ", ".join(facets or ("general",)) + ".",
        "Gap: " + gap_reason.strip(),
    ]
    if safe_terms:
        parts.append("Relevant terms: " + ", ".join(safe_terms) + ".")
    return " ".join(parts)
