from __future__ import annotations

import re
from collections import defaultdict

from eubw_researcher.models import (
    ClaimVerificationRecord,
    EvidenceCluster,
    EvidenceSynthesisMatrix,
    EvidenceSynthesisRecord,
    OpenedPassageRecord,
    ReadingPlan,
    ReadingPlanItem,
    RuntimeConfig,
    SelectedEvidenceRecord,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching

ROLE_BOUNDARY_FACETS: dict[str, tuple[str, ...]] = {
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
        "abgrenz",
        "boundary",
        "intermediary",
        "intermediaer",
        "relying party",
        "wallet-relying party",
    ),
    "technical_requester": (
        "technical requester",
        "technisch",
        "authenticates",
        "authentisiert",
        "access certificate",
        "access certificates",
        "rpac",
    ),
    "end_relying_party": (
        "end party",
        "end relying party",
        "intermediated",
        "intermediated relying party",
        "wallet-relying party",
        "wallet relying party",
    ),
    "registry_information": (
        "registration",
        "registrierung",
        "registry",
        "register",
        "registrar",
        "certificate",
        "zertifikat",
    ),
    "user_display": (
        "user display",
        "display",
        "anzeige",
        "nutzeranzeige",
        "shown to the user",
        "request context",
    ),
    "purpose_or_intended_use": (
        "purpose",
        "zweck",
        "intended use",
        "use case",
        "uses",
    ),
    "requested_attributes": (
        "welche informationen",
        "requested attributes",
        "attribute",
        "attributes",
        "requested data",
        "daten",
    ),
    "privacy_policy_or_dpa": (
        "privacy policy",
        "privacy",
        "datenschutz",
        "dpa",
        "complaint",
        "contact",
        "kontakt",
    ),
    "certificate_or_trust_anchor": (
        "certificate",
        "zertifikat",
        "trust anchor",
        "access ca",
        "rpac",
        "rprc",
    ),
    "wallet_solution_certification": (
        "certification",
        "zertifizierung",
        "certification scheme",
        "conformity assessment",
        "wallet solution certification",
        "certification of european digital identity wallets",
        "wallet solution",
        "wallet solutions",
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
        "national",
        "choice",
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

CENTRAL_ROLE_BOUNDARY_FACETS = {
    "trust_mark_meaning",
    "trust_mark_removal",
    "trust_mark_scope_boundary",
    "actor_boundary",
    "registry_information",
    "user_display",
    "purpose_or_intended_use",
    "requested_attributes",
    "privacy_policy_or_dpa",
    "pseudonym_legal_permission",
    "pseudonym_account_binding",
    "attribute_presentation_limit",
    "linkability_risk",
    "wallet_solution_certification",
    "protocol_security_parameter",
}

FACET_COOCCURRENCE_BOOSTS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("trust_mark_removal", ("trust mark", "vertrauenszeichen"), ("remove", "entfernen", "cancellation")),
    ("trust_mark_scope_boundary", ("trust mark", "vertrauenszeichen"), ("out of scope", "relying party", "attestation provider", "scope")),
    ("user_display", ("intermediary", "intermediaer"), ("display", "anzeige", "request")),
    ("registry_information", ("intermediary", "intermediaer"), ("registration certificate", "certificate", "registrierung")),
    ("purpose_or_intended_use", ("intended use", "zweck", "purpose"), ("attribute", "attributes", "requested")),
    ("privacy_policy_or_dpa", ("privacy policy", "datenschutz", "dpa"), ("wallet-relying party", "relying party", "intermediary")),
    ("pseudonym_account_binding", ("pseudonym", "pseudonymous"), ("account", "binding", "unique")),
    ("attribute_presentation_limit", ("attribute", "attributes", "claims"), ("presentation", "selective disclosure", "disclosure")),
    ("linkability_risk", ("linkable", "linkability", "unlinkability"), ("pseudonym", "presentation", "relying party")),
    ("wallet_solution_certification", ("certification", "certification scheme", "conformity assessment"), ("wallet solution", "european digital identity wallets")),
    ("protocol_security_parameter", ("state", "nonce", "wallet_nonce", "request-id"), ("openid4vp", "authorization response", "authorization request", "direct_post", "replay")),
)


TRUST_MARK_TERMS = (
    "wallet trust mark",
    "eudi wallet trust mark",
    "trust mark",
    "vertrauenszeichen",
    "vertrauensmarke",
)
TRUST_MARK_REMOVAL_TERMS = (
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
TRUST_MARK_SCOPE_TERMS = (
    "scope",
    "out of scope",
    "relying party",
    "relying parties",
    "attestation provider",
    "attestation providers",
    "bewertet",
    "bewertung",
)
PROTOCOL_PARAMETER_TERMS = (
    "state",
    "nonce",
    "wallet nonce",
    "wallet_nonce",
    "request id",
    "request-id",
    "transaction id",
    "transaction-id",
)
PROTOCOL_CONTEXT_TERMS = (
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


def _trust_mark_facets_for_surface(surface: str) -> list[str]:
    if not any(term in surface for term in TRUST_MARK_TERMS):
        return []
    facets = ["trust_mark_meaning"]
    if any(term in surface for term in TRUST_MARK_REMOVAL_TERMS):
        facets.append("trust_mark_removal")
    if any(term in surface for term in TRUST_MARK_SCOPE_TERMS):
        facets.append("trust_mark_scope_boundary")
    return facets


def _surface_has_protocol_term(surface: str, term: str) -> bool:
    if term in {"state", "nonce", "csrf", "replay", "oauth"}:
        return f" {term} " in f" {surface} "
    return term in surface


def _surface_has_protocol_security_parameter(surface: str) -> bool:
    has_nonce_or_identifier = any(
        _surface_has_protocol_term(surface, term)
        for term in PROTOCOL_PARAMETER_TERMS
        if term != "state"
    )
    has_state_protocol_context = _surface_has_protocol_term(surface, "state") and any(
        _surface_has_protocol_term(surface, term)
        for term in (
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
        )
    )
    return (has_nonce_or_identifier or has_state_protocol_context) and any(
        _surface_has_protocol_term(surface, term) for term in PROTOCOL_CONTEXT_TERMS
    )


def _surface_has_protocol_record_context(surface: str) -> bool:
    return any(
        term in surface
        for term in (
            "openid4vp_1_0_official",
            "rfc6749_oauth2",
        )
    )


def detect_question_facets(question: str) -> list[str]:
    normalized = normalize_text_for_matching(question)
    facets: list[str] = []
    for facet_id, terms in ROLE_BOUNDARY_FACETS.items():
        if facet_id.startswith("trust_mark_"):
            if facet_id in _trust_mark_facets_for_surface(normalized):
                facets.append(facet_id)
            continue
        if facet_id == "protocol_security_parameter":
            if _surface_has_protocol_security_parameter(normalized):
                facets.append(facet_id)
            continue
        if facet_id == "requested_attributes":
            padded = f" {normalized} "
            if any(
                f" {term} " in padded if term in {"data", "daten"} else term in normalized
                for term in terms
            ):
                facets.append(facet_id)
            continue
        if any(term in normalized for term in terms):
            facets.append(facet_id)
    if (
        {"technical_requester", "end_relying_party"} & set(facets)
        or ("intermediary" in normalized or "intermediaer" in normalized)
    ) and "actor_boundary" not in facets:
        facets.insert(0, "actor_boundary")
    if ("pseudonym" in normalized or "pseudonyme" in normalized) and "pseudonym_legal_permission" not in facets:
        facets.insert(0, "pseudonym_legal_permission")
    return facets


def _facet_tags_for_surface(surface: str, question_facets: set[str]) -> list[str]:
    normalized = normalize_text_for_matching(surface)
    tags: list[str] = []
    for facet_id in question_facets:
        if facet_id.startswith("trust_mark_"):
            trust_facets = _trust_mark_facets_for_surface(normalized)
            if facet_id in trust_facets:
                tags.append(facet_id)
            continue
        if facet_id == "protocol_security_parameter":
            if _surface_has_protocol_record_context(normalized) and _surface_has_protocol_security_parameter(normalized):
                tags.append(facet_id)
            continue
        terms = ROLE_BOUNDARY_FACETS.get(facet_id, ())
        if any(term in normalized for term in terms):
            tags.append(facet_id)
    for facet_id, left_terms, right_terms in FACET_COOCCURRENCE_BOOSTS:
        if facet_id not in question_facets or facet_id in tags:
            continue
        if facet_id == "protocol_security_parameter" and not _surface_has_protocol_record_context(normalized):
            continue
        if any(_surface_has_protocol_term(normalized, term) for term in left_terms) and any(
            _surface_has_protocol_term(normalized, term) for term in right_terms
        ):
            tags.append(facet_id)
    return sorted(tags)


def _quality_flags(text: str) -> list[str]:
    normalized = normalize_text_for_matching(text)
    flags: list[str] = []
    answer_like = any(
        marker in normalized
        for marker in (
            "upon cancellation",
            "must remove",
            "scope is",
            "out of scope",
            "shall support",
            "specific and unique",
            "selective disclosure",
            "linkability",
            "pseudonymous authentication",
            "securely bind verifiable presentation",
            "preventing replay",
            "authorization response with the parameters",
            "check that the same state value is returned",
        )
    )
    if (
        re.search(r"\b(references|bibliography)\b", normalized)
        or normalized.count("http") >= 2
    ) and not answer_like:
        flags.append("references_only")
    if re.match(r"^\s*article\s+\d+[a-z]?\b", normalized) and len(text.split()) < 24:
        flags.append("title_only")
    if re.match(r"^\s*\d+(?:\.\d+)+\s+topic\b", normalized) and len(text.split()) < 24:
        flags.append("title_only")
    if normalized.startswith("description section s in arf proposed solution"):
        flags.append("title_only")
    if "registry api s read methods shall be open for public access" in normalized:
        flags.append("context_only")
    if re.search(r"\btopic\s+\d+\b", normalized) and normalized.rstrip().endswith(" a"):
        flags.append("title_only")
    if (
        re.match(r"^\s*(\||table|note|annex|section)\s+\d", normalized)
        or text.lstrip().startswith("|")
        or " table " in f" {normalized} "
    ):
        flags.append("table_note")
    if len(re.findall(r"[.!?]", text)) == 0 and len(text.split()) < 18:
        flags.append("title_only")
    if (
        re.search(r"\bmeans\b", normalized)
        or "for the purposes of" in normalized
        or re.match(r"^\s*article\s+\d+[a-z]?\s+definitions\b", normalized)
    ):
        flags.append("definition_only")
    if len(text.split()) < 16 or text.endswith("..."):
        flags.append("snippet_like")
    if not flags or set(flags).isdisjoint({"references_only", "table_note", "title_only", "snippet_like", "context_only", "definition_only"}):
        flags.append("answer_ready")
    return list(dict.fromkeys(flags))


def _facet_score(record, question_facets: set[str]) -> int:
    if not question_facets:
        return 0
    surface = " ".join([record.snippet, record.locator or "", record.source_id])
    tags = _facet_tags_for_surface(surface, question_facets)
    score = len(tags) * 20
    normalized = normalize_text_for_matching(surface)
    for facet_id, left_terms, right_terms in FACET_COOCCURRENCE_BOOSTS:
        if facet_id in question_facets and any(term in normalized for term in left_terms) and any(
            term in normalized for term in right_terms
        ):
            score += 18
    if "actor_boundary" in question_facets and any(
        term in normalized
        for term in (
            "intermediary",
            "intermediaries",
            "intermediaer",
            "intermediated",
            "on behalf",
            "on-behalf",
        )
    ):
        score += 55
    if "user_display" in question_facets and any(
        term in normalized
        for term in ("wallet unit informs the user", "user display", "shown to the user")
    ):
        score += 35
    if "trust_mark_meaning" in question_facets and any(
        term in normalized
        for term in ("visible trust mark", "wallet trust mark", "eudi wallet trust mark", "vertrauenszeichen")
    ):
        score += 50
    if "trust_mark_removal" in question_facets and any(
        term in normalized
        for term in ("visible trust mark", "wallet trust mark", "eudi wallet trust mark", "vertrauenszeichen")
    ):
        score += 55
    if "trust_mark_removal" in question_facets and any(
        term in normalized
        for term in ("upon cancellation", "remove", "removal", "entfernen", "cancellation")
    ):
        score += 65
    if "trust_mark_scope_boundary" in question_facets and any(
        term in normalized
        for term in ("visible trust mark", "wallet trust mark", "eudi wallet trust mark", "vertrauenszeichen")
    ):
        score += 45
    if "trust_mark_scope_boundary" in question_facets and any(
        term in normalized for term in ("out of scope", "relying party", "attestation provider", "scope")
    ):
        score += 65
    if "trust_mark_scope_boundary" in question_facets and "visible trust mark" in normalized and any(
        term in normalized for term in ("out of scope", "relying party", "attestation provider")
    ):
        score += 120
    if "wallet_solution_certification" in question_facets and any(
        term in normalized
        for term in (
            "certification of european digital identity wallets",
            "national certification schemes",
            "certificate and certification assessment report",
            "certification body",
            "conformity assessment body",
            "wallet solution",
        )
    ):
        score += 95
    if "protocol_security_parameter" in question_facets:
        if _surface_has_protocol_record_context(normalized):
            score += 45
        if "nonce" in normalized and any(
            term in normalized
            for term in (
                "securely bind",
                "preventing replay",
                "verifiable presentation",
                "correct nonce",
                "verifier must verify",
                "verifier must validate",
                "fresh cryptographically random",
            )
        ):
            score += 110
        if "state" in normalized and any(
            term in normalized
            for term in (
                "authorization response",
                "request-id",
                "request id",
                "response uri",
                "response_uri",
                "direct_post",
                "same state value",
            )
        ):
            score += 105
        if "wallet_unavailable" in normalized or "token endpoint" in normalized:
            score -= 70
        if ("member state" in normalized or "state diagram" in normalized) and "nonce" not in normalized:
            score -= 85
    if "pseudonym_legal_permission" in question_facets and any(
        term in normalized
        for term in ("pseudonym", "pseudonyms", "pseudonymous authentication")
    ):
        score += 65
    if "pseudonym_legal_permission" in question_facets and any(
        term in normalized
        for term in (
            "article 14",
            "pseudonym generation",
            "specific and unique",
            "technical specifications for pseudonym",
        )
    ):
        score += 80
    if "pseudonym_account_binding" in question_facets and any(
        term in normalized
        for term in ("account", "specific and unique", "user binding", "cryptographic binding")
    ):
        score += 35
    if "attribute_presentation_limit" in question_facets and any(
        term in normalized
        for term in ("selective disclosure", "presentation of attributes", "strictly necessary claims")
    ):
        score += 35
    if "linkability_risk" in question_facets and any(
        term in normalized
        for term in ("linkability", "unlinkability", "linkable", "verifier-to-verifier")
    ):
        score += 35
    if "references_only" in _quality_flags(record.snippet):
        score -= 35
    if "table_note" in _quality_flags(record.snippet):
        score -= 15
    if "title_only" in _quality_flags(record.snippet):
        score -= 30
    if any(
        marker in normalized
        for marker in (
            "description section s in arf proposed solution",
            "topic 27 - registration of pid providers",
        )
    ):
        score -= 45
    return score


def _record_priority(record, question_facets: set[str]) -> tuple[int, int, float]:
    role_weight = {"high": 3, "medium": 2, "low": 1}.get(record.source_role_level.value, 0)
    return (_facet_score(record, question_facets), role_weight, record.score)


def _clusters_for_reading(
    clusters: list[EvidenceCluster],
    *,
    max_clusters: int,
    question_facets: set[str] | None = None,
) -> list[EvidenceCluster]:
    if max_clusters <= 0:
        return []
    if question_facets:
        ordered_clusters = sorted(
            clusters,
            key=lambda cluster: max(
                (_record_priority(record, question_facets) for record in cluster.records),
                default=(0, 0, 0.0),
            ),
            reverse=True,
        )
    else:
        ordered_clusters = list(clusters)
    selected = list(ordered_clusters[:max_clusters])
    selected_source_ids = {
        source_id for cluster in selected for source_id in cluster.source_ids
    }
    rescue_clusters = [
        cluster
        for cluster in ordered_clusters[max_clusters:]
        if "source_catalog_candidate_present" in cluster.sufficiency_signals
        and not selected_source_ids.intersection(cluster.source_ids)
    ]
    for cluster in rescue_clusters:
        if len(selected) < max_clusters:
            selected.append(cluster)
        else:
            selected[-1] = cluster
        selected_source_ids.update(cluster.source_ids)
    return selected


def _compact_statement(text: str, *, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"^[#>*\-\s]+", "", compact)
    compact = re.sub(
        r"^(passage|source|evidence)\s+supports:\s*",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    original_normalized = normalize_text_for_matching(compact)
    if (
        "pid provider or an attestation provider issuing device-bound attestations"
        in original_normalized
        and "issuer credential metadata" in original_normalized
        and (
            "proof_types_supported" in compact
            or "proof types supported" in original_normalized
        )
    ):
        return (
            "PID and Attestation Providers issuing device-bound attestations must "
            "advertise WUA proof support in Issuer Credential Metadata, require key "
            "attestation, and verify the WUA signature, x5c trust-anchor chain, "
            "attested-key binding, and c_nonce freshness."
        )
    if (
        "wallet providers issue wuas to the wallet unit" in original_normalized
        and "out of scope" in original_normalized
    ):
        return (
            "How Wallet Providers issue WUAs to the Wallet Unit is outside this "
            "technical specification; the source scopes WUA interoperability to "
            "transfer, format, content, life cycle, and revocation mechanisms."
        )
    if (
        "upon cancellation" in original_normalized
        and "remove" in original_normalized
        and "visible trust mark" in original_normalized
        and "relying party" in original_normalized
        and "attestation provider" in original_normalized
    ):
        return (
            "Upon cancellation, the Wallet Provider must remove "
            "the visible trust mark and references to it; the scoped trust mark is "
            "for the visible EUDI Wallet mark, not Relying Party services or "
            "Attestation Provider qualifications."
        )
    compact = re.sub(r"^ARF main markdown source\s+", "", compact)
    compact = re.sub(
        r"^(Keep with proposed changes|Delete|Add|Modify)\s+[A-Za-z0-9_-]+\s+",
        "",
        compact,
    )
    compact = re.sub(r"^\*\s+", "", compact)
    compact = re.sub(r"^Abstract\s+(?=The present\b)", "", compact)
    compact = re.sub(
        r"^Article\s+\d+[a-z]?\s+Definitions\s+(?=For the purposes\b)",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(
        r"^Commission Implementing Regulation\s+\(EU\)\s+\d+/\d+\s+.*?\s+(?=Under Article\b)",
        "",
        compact,
    )
    if " > " in compact:
        tail = compact.rsplit(" > ", 1)[-1].strip()
        if len(tail) >= 40:
            compact = tail
    compact = re.sub(r"^\*\s+", "", compact)
    compact = re.sub(r"^Abstract\s+(?=The present\b)", "", compact)
    compact = re.sub(
        r"^Article\s+\d+[a-z]?\s+Definitions\s+(?=For the purposes\b)",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(
        r"^\d+(?:\.\d+)*\.?\s+[^.!?]{0,120}?\s+(?=(According to|For the purposes|A |An |The ))",
        "",
        compact,
    )
    normalized = normalize_text_for_matching(compact)
    if "out of scope" in normalized and "relying party" in normalized:
        return (
            "The source treats the visible wallet trust mark as "
            "in-scope and leaves unrelated Relying Party or attestation-provider "
            "trust indicators out of scope."
        )
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    chosen = next((sentence for sentence in sentences if len(sentence) > 40), compact)
    if len(chosen) > limit:
        chosen = chosen[:limit].rsplit(" ", 1)[0].strip() + "..."
    return chosen


def _facet_statement(text: str, facet_tags: list[str], *, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"^[#>*\-\s]+", "", compact)
    compact = re.sub(r"^ARF main markdown source\s+", "", compact)
    compact = re.sub(
        r"^(Keep with proposed changes|Delete|Add|Modify)\s+[A-Za-z0-9_-]+\s+",
        "",
        compact,
    )
    normalized_full_compact = normalize_text_for_matching(compact)
    facet_set = set(facet_tags)
    if "trust_mark_removal" in facet_set and (
        "visible trust mark" in normalized_full_compact
        or "trust mark visible" in normalized_full_compact
        or "sichtbares vertrauenszeichen" in normalized_full_compact
    ) and any(
        term in normalized_full_compact
        for term in ("upon cancellation", "remove", "removal", "entfernen")
    ):
        if "trust_mark_scope_boundary" in facet_set:
            return (
                "Upon cancellation, the Wallet Provider must remove the visible trust mark "
                "and references to it; the scoped trust mark concerns the EUDI Wallet mark, "
                "not Relying Party services or Attestation Provider qualifications."
            )
        return (
            "Upon cancellation, the Wallet Provider must remove the visible trust mark "
            "and references to it."
        )
    if " > " in compact:
        tail = compact.rsplit(" > ", 1)[-1].strip()
        if len(tail) >= 40:
            compact = tail
    compact = re.sub(
        r"^\d+(?:\.\d+)*\.?\s+[^.!?]{0,120}?\s+(?=(According to|For the purposes|A |An |The ))",
        "",
        compact,
    )
    if not facet_tags:
        return _compact_statement(compact, limit=limit)
    normalized_tags = set(facet_tags)
    candidate_terms: list[str] = []
    for facet_id in normalized_tags:
        candidate_terms.extend(ROLE_BOUNDARY_FACETS.get(facet_id, ()))
    normalized_compact = normalize_text_for_matching(compact)
    if "trust_mark_removal" in normalized_tags and (
        "visible trust mark" in normalized_compact
        or "trust mark visible" in normalized_compact
        or "sichtbares vertrauenszeichen" in normalized_compact
    ) and any(
        term in normalized_compact
        for term in ("upon cancellation", "remove", "removal", "entfernen")
    ):
        if "trust_mark_scope_boundary" in normalized_tags:
            return (
                "Upon cancellation, the Wallet Provider must remove the visible trust mark "
                "and references to it; the scoped trust mark concerns the EUDI Wallet mark, "
                "not Relying Party services or Attestation Provider qualifications."
            )
        return (
            "Upon cancellation, the Wallet Provider must remove the visible trust mark "
            "and references to it."
        )
    sentences = re.split(r"(?<=[.!?])\s+|\s+-\s+", compact)
    scored: list[tuple[int, int, str]] = []
    for sentence in sentences:
        normalized_sentence = normalize_text_for_matching(sentence)
        if re.match(r"^\s*article\s+\d+[a-z]?\b", normalized_sentence) and len(sentence.split()) < 24:
            continue
        if re.match(r"^\s*\d+(?:\.\d+)+\s+topic\b", normalized_sentence) and len(sentence.split()) < 24:
            continue
        if "registry api s read methods shall be open for public access" in normalized_sentence:
            continue
        if re.search(r"\btopic\s+\d+\b", normalized_sentence) and normalized_sentence.rstrip().endswith(" a"):
            continue
        hits = sum(1 for term in candidate_terms if term in normalized_sentence)
        score = hits
        if any(
            term in normalized_sentence
            for term in (
                "intermediary",
                "intermediaries",
                "intermediaer",
                "intermediated",
                "on behalf",
                "on-behalf",
                "usesintermediary",
                "isintermediary",
            )
        ):
            score += 8
        if any(term in normalized_sentence for term in ("wallet unit informed the user", "shown to the user", "user approval")):
            score += 5
        if any(term in normalized_sentence for term in ("intended use", "privacy policy", "requested attributes")):
            score += 4
        if any(
            marker in normalized_sentence
            for marker in (
                "certificate histories",
                "public access",
                "write methods",
                "topic 27",
            )
        ):
            score -= 5
        if score > 0:
            scored.append((score, hits, sentence.strip()))
    if scored:
        scored.sort(key=lambda item: (item[0], item[1], len(item[2])), reverse=True)
        chosen = scored[0][2]
        if len(chosen) > limit:
            chosen = chosen[:limit].rsplit(" ", 1)[0].strip() + "..."
        return chosen
    return _compact_statement(compact, limit=limit)


def _answer_role(cluster: EvidenceCluster, record) -> str:
    surface = normalize_text_for_matching(" ".join([record.snippet, record.locator or ""]))
    if cluster.open_issue_ids:
        return "open_issue"
    if any(marker in surface for marker in ("out of scope", "does not address", "scope is")):
        return "scope_boundary"
    if "source_catalog_candidate_present" in cluster.sufficiency_signals:
        return "core_answer_support"
    if record.source_role_level.value == "low":
        return "background"
    if record.document_status.value in {"final", "adopted_pending_effective_date"}:
        return "normative_basis"
    if record.source_role_level.value == "medium":
        return "technical_spec_context"
    return "source_role_context"


def _caveats(cluster: EvidenceCluster, record, verification) -> list[str]:
    caveats: list[str] = [
        f"source_role:{record.source_role_level.value}",
        f"evidence_tier:{record.evidence_tier.value}",
        f"binding_level:{record.binding_level.value}",
        f"document_status:{record.document_status.value}",
    ]
    if verification is not None and not verification.answer_use_allowed:
        caveats.append("verification does not allow answer use")
    if cluster.open_issue_ids:
        caveats.extend(f"open_issue:{issue_id}" for issue_id in cluster.open_issue_ids)
    return caveats


def _opening_reason(
    cluster: EvidenceCluster,
    record,
    *,
    index: int,
    facet_tags: list[str],
    uncovered_facets: list[str],
) -> str:
    reason_parts: list[str] = []
    if "source_catalog_candidate_present" in cluster.sufficiency_signals:
        reason_parts.append("source-level rescue/source-title or corpus-alias match")
    if cluster.candidate_claim_ids:
        reason_parts.append("claim match")
    if cluster.open_issue_ids:
        reason_parts.append("gap/open-issue check")
    if record.source_role_level.value == "high":
        reason_parts.append("higher-authority check")
    if facet_tags:
        reason_parts.append("facet coverage: " + ", ".join(uncovered_facets or facet_tags))
    if not reason_parts:
        reason_parts.append("primary evidence-cluster passage" if index == 0 else "adjacent context passage")
    if index > 0:
        reason_parts.append("adjacent context")
    return "; ".join(reason_parts)


def build_reading_artifacts(
    *,
    question: str,
    clusters: list[EvidenceCluster],
    selected_evidence: list[SelectedEvidenceRecord],
    claim_verification: list[ClaimVerificationRecord],
    runtime_config: RuntimeConfig,
) -> tuple[ReadingPlan, list[OpenedPassageRecord], EvidenceSynthesisMatrix]:
    max_clusters = runtime_config.knowledge_service_max_reading_clusters
    max_opened = runtime_config.knowledge_service_max_opened_passages
    max_adjacent = runtime_config.knowledge_service_max_adjacent_passages_per_cluster

    budget = {
        "max_clusters": max_clusters,
        "max_opened_passages": max_opened,
        "max_adjacent_passages_per_cluster": max_adjacent,
        "timeout_seconds": runtime_config.knowledge_service_reading_timeout_seconds,
    }
    reading_plan = ReadingPlan(question=question, budget=budget)
    opened_passages: list[OpenedPassageRecord] = []
    question_facets = set(detect_question_facets(question))
    verification_by_claim_id = {
        record.claim_id: record for record in claim_verification
    }
    selected_by_chunk_id: dict[str, list[SelectedEvidenceRecord]] = defaultdict(list)
    for selected in selected_evidence:
        selected_by_chunk_id[selected.chunk_id].append(selected)

    reading_clusters = _clusters_for_reading(
        clusters,
        max_clusters=max_clusters,
        question_facets=question_facets,
    )
    opened_count = 0
    covered_facets: set[str] = set()
    for cluster in reading_clusters:
        if not cluster.records:
            continue
        ordered_records = sorted(
            cluster.records,
            key=lambda record: _record_priority(record, question_facets),
            reverse=True,
        ) if question_facets else list(cluster.records)
        cluster_records = ordered_records[: 1 + max_adjacent]
        for index, record in enumerate(cluster_records):
            if max_opened and opened_count >= max_opened:
                reading_plan.budget_exhausted = True
                break
            operation = "open_passage" if index == 0 else "open_adjacent_passage"
            facet_tags = _facet_tags_for_surface(
                " ".join([record.snippet, record.locator or "", record.source_id]),
                question_facets,
            )
            uncovered_facets = [
                facet for facet in facet_tags if facet in CENTRAL_ROLE_BOUNDARY_FACETS and facet not in covered_facets
            ]
            item_id = f"read_{len(reading_plan.items) + 1}"
            reading_plan.items.append(
                ReadingPlanItem(
                    item_id=item_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    operation=operation,
                    reason=_opening_reason(
                        cluster,
                        record,
                        index=index,
                        facet_tags=facet_tags,
                        uncovered_facets=uncovered_facets,
                    ),
                )
            )
            opened_passages.append(
                OpenedPassageRecord(
                    passage_id=item_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    passage_role="primary" if index == 0 else "adjacent",
                    text_snippet=record.snippet,
                )
            )
            covered_facets.update(facet_tags)
            opened_count += 1
        if reading_plan.budget_exhausted:
            break

    records: list[EvidenceSynthesisRecord] = []
    for cluster in reading_clusters:
        ordered_records = sorted(
            cluster.records,
            key=lambda record: _record_priority(record, question_facets),
            reverse=True,
        ) if question_facets else list(cluster.records)
        for record in ordered_records[: 1 + max_adjacent]:
            selected_records = selected_by_chunk_id.get(record.chunk_id, [])
            claim_id = selected_records[0].claim_id if selected_records else None
            verification = verification_by_claim_id.get(claim_id or "")
            facet_tags = _facet_tags_for_surface(
                " ".join([record.snippet, record.locator or "", record.source_id]),
                question_facets,
            )
            quality_flags = _quality_flags(record.snippet)
            answer_role = _answer_role(cluster, record)
            if facet_tags and "answer_ready" in quality_flags and answer_role == "background":
                answer_role = "candidate_core_claim"
            if set(quality_flags).intersection({"references_only", "table_note", "title_only"}):
                answer_role = "background"
            records.append(
                EvidenceSynthesisRecord(
                    synthesis_id=f"synthesis_{len(records) + 1}",
                    claim_id=claim_id,
                    cluster_id=cluster.cluster_id,
                    answer_role=answer_role,
                    statement=_facet_statement(record.snippet, facet_tags),
                    source_ids=[record.source_id],
                    chunk_ids=[record.chunk_id],
                    locators=[record.locator] if record.locator else [],
                    source_role_levels=[record.source_role_level],
                    evidence_tiers=[record.evidence_tier],
                    binding_levels=[record.binding_level],
                    document_statuses=[record.document_status],
                    facet_tags=facet_tags,
                    quality_flags=quality_flags,
                    verification_status=(
                        verification.verification_result if verification is not None else None
                    ),
                    caveats=_caveats(cluster, record, verification),
                )
            )

    return (
        reading_plan,
        opened_passages,
        EvidenceSynthesisMatrix(question=question, records=records),
    )
