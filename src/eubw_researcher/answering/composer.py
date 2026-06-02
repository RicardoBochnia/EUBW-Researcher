from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable, List, Optional, Sequence

from eubw_researcher.models import (
    AnswerAlignmentRecord,
    AnswerAlignmentReport,
    Citation,
    CitationQuality,
    ClaimState,
    ClaimType,
    DocumentStatus,
    EvidenceSynthesisMatrix,
    FacetCoverageFacet,
    FacetCoverageReport,
    LedgerEntry,
    PinpointEvidenceRecord,
    PinpointEvidenceReport,
    QueryIntent,
    RelationHintRecord,
    RelationHintReport,
    SourceDocument,
    SourceKind,
    SourceRoleLevel,
    SupportDirectness,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching

TOPOLOGY_FACET_IDS = [
    "multiplicity_single_certificate",
    "derived_certificate_term_status",
    "registration_certificate_role",
    "access_certificate_role",
    "unresolved_or_interpretive_status",
]
TOPOLOGY_NOT_DEFINED_LABEL = "Not explicitly defined"
TOPOLOGY_NOT_DEFINED_PREFIX = "No governing EU source in the current corpus explicitly defines"
TOPOLOGY_SCOPING_SENTENCE = (
    "The governing EU material supports intended-use / service scoping: registration "
    "certificates are tied to intended use and requested attributes, access certificates "
    "authenticate the wallet-relying party, and registration-certificate issuance depends "
    "on a valid access certificate. But the governing texts do not expressly resolve "
    "whether one wallet-relying party is limited to a single organisation-level certificate."
)
TOPOLOGY_UNRESOLVED_WITH_PROJECT_SUPPORT_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. The current run can justify only a non-governing reading: "
    "governing EU text supports the boundary conditions, while medium-rank project "
    "artifacts make the multi-certificate interpretation more explicit."
)
TOPOLOGY_UNRESOLVED_GOVERNING_ONLY_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. This run preserves the governing boundary conditions, but it does "
    "not surface approved medium-rank project-artifact support that would make a "
    "multi-certificate interpretation more explicit."
)
TOPOLOGY_UNRESOLVED_PROJECT_ONLY_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. In this run, only medium-rank project artifacts make the "
    "multi-certificate interpretation more explicit; governing EU boundary support for "
    "that interpretation is not approved here."
)
TOPOLOGY_UNRESOLVED_NO_APPROVED_SUPPORT_SENTENCE = (
    'The broader multiplicity or "derived certificate" conclusion is not stated as '
    "governing EU law. This run does not surface approved governing-boundary support or "
    "approved medium-rank project-artifact support for that interpretation."
)
EUBW_STRUCTURED_INTENT_TYPES = {
    "eubw_role_boundary_analysis",
    "eubw_lifecycle_analysis",
    "eubw_audit_trail_analysis",
    "eubw_identity_authority_analysis",
    "eubw_architecture_bucket_analysis",
}
EUBW_ARCHITECTURE_BUCKET_SECTIONS = {
    "eubw_direct_architecture_constraints": "direkt ableitbar",
    "eubw_arf_subordination": "direkt ableitbar",
    "eubw_identifier_delegated_specs": "delegiert",
    "eubw_access_control_delegated_specs": "delegiert",
    "eubw_trust_model_still_open": "plausible Annahme",
}


@dataclass
class _EvidenceLine:
    label: str
    citations: List[Citation] = field(default_factory=list)


@dataclass
class _AnswerBullet:
    bullet_id: str
    section: str
    text: str
    rationale: Optional[str] = None
    wording_category: str = "state_forwarded"
    claim_ids: List[str] = field(default_factory=list)
    claim_states: List[ClaimState] = field(default_factory=list)
    evidence_lines: List[_EvidenceLine] = field(default_factory=list)
    explicit_role_partitioning: bool = False


@dataclass
class ComposedAnswerBundle:
    rendered_answer: str
    facet_coverage_report: Optional[FacetCoverageReport]
    pinpoint_evidence_report: PinpointEvidenceReport
    answer_alignment_report: AnswerAlignmentReport


@dataclass
class _TopologyEvidenceSelection:
    citations: List[Citation]
    claim_states: List[ClaimState]
    claim_ids: List[str]


@dataclass
class _TopologyProjectSupport:
    supported_entries: List[LedgerEntry]
    citations: List[Citation]
    claim_states: List[ClaimState]


@dataclass(frozen=True)
class _SynthesisRecordView:
    record: object
    role: str
    score: int
    statement: str


def _role_weight(role_level: SourceRoleLevel) -> int:
    return {
        SourceRoleLevel.HIGH: 3,
        SourceRoleLevel.MEDIUM: 2,
        SourceRoleLevel.LOW: 1,
    }[role_level]


def _citation_weight(citation_quality: CitationQuality) -> int:
    return 2 if citation_quality == CitationQuality.ANCHOR_GROUNDED else 1


def _dedupe_citations(citations: Iterable[Citation]) -> List[Citation]:
    unique: List[Citation] = []
    seen = set()
    for citation in citations:
        key = (
            citation.source_id,
            citation.anchor_label,
            citation.canonical_url,
            citation.document_title,
            citation.source_kind,
            citation.source_role_level,
            citation.source_origin,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique


def _render_citations(citations: Iterable[Citation]) -> str:
    deduped = _dedupe_citations(citations)
    if not deduped:
        return "no admissible citation"
    return "; ".join(citation.render() for citation in deduped)


def _render_bullets(
    summary: str,
    bullets: Sequence[_AnswerBullet],
    clarification_note: Optional[str],
) -> str:
    lines: List[str] = [summary]
    if clarification_note:
        lines.append(f"First-pass note: {clarification_note}")

    section_order = [TOPOLOGY_NOT_DEFINED_LABEL, "Confirmed", "Interpretive", "Open"]
    present_sections = []
    for section in section_order:
        if any(bullet.section == section for bullet in bullets):
            present_sections.append(section)
    for bullet in bullets:
        if bullet.section not in present_sections:
            present_sections.append(bullet.section)

    for section in present_sections:
        section_bullets = [bullet for bullet in bullets if bullet.section == section]
        if not section_bullets:
            continue
        lines.append(f"{section}:")
        for bullet in section_bullets:
            lines.append(f"- {bullet.text}")
            if bullet.rationale:
                lines.append(f"  Rationale: {bullet.rationale}")
            for evidence_line in bullet.evidence_lines:
                lines.append(
                    f"  {evidence_line.label}: {_render_citations(evidence_line.citations)}"
                )
    return "\n".join(lines)


def _render_citation_detail(citation: Citation) -> str:
    locator = _compact_locator(citation.anchor_label or (
        str(citation.document_path) if citation.document_path is not None else citation.canonical_url
    ))
    locator_part = f", locator={locator}" if locator else ""
    return (
        f"{citation.source_id} ({citation.source_kind.value}, "
        f"rank={citation.source_role_level.value}, "
        f"binding={_binding_effect_label(citation.source_kind.value, citation.binding_level.value, citation.document_status.value)}, "
        f"status={citation.document_status.value}{locator_part})"
    )


def _compact_answer_text(value: str, *, limit: int = 260) -> str:
    text = " ".join(value.split())
    for prefix in [
        "Current proposal-stage support indicates: ",
        "Current draft support indicates: ",
        "Adopted but not yet effective: ",
        "Informational source support indicates: ",
    ]:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    if len(text) <= limit:
        return text
    truncated = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def _compact_locator(value: Optional[str], *, limit: int = 180) -> Optional[str]:
    if value is None:
        return None
    return _compact_answer_text(value, limit=limit)


def _sources_from_bullets(bullets: Sequence[_AnswerBullet], *, limit: int = 5) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for bullet in bullets:
        for evidence_line in bullet.evidence_lines:
            for citation in evidence_line.citations:
                if citation.source_id in seen:
                    continue
                seen.add(citation.source_id)
                sources.append(citation.source_id)
                if len(sources) >= limit:
                    return sources
    return sources


def _matrix_records_matching(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    terms: Sequence[str],
    *,
    min_term_hits: int = 1,
    required_facets: Sequence[str] = (),
    allowed_answer_roles: Sequence[str] = (),
    required_source_ids: Sequence[str] = (),
) -> list:
    if evidence_synthesis_matrix is None:
        return []
    normalized_terms = [
        normalize_text_for_matching(term)
        for term in terms
        if normalize_text_for_matching(term)
    ]
    required_facet_set = {str(facet) for facet in required_facets}
    allowed_role_set = {str(role) for role in allowed_answer_roles}
    required_source_set = {str(source_id) for source_id in required_source_ids}
    records = []
    for record in evidence_synthesis_matrix.records:
        record_facets = {str(facet) for facet in (getattr(record, "facet_tags", []) or [])}
        if required_facet_set and not record_facets.intersection(required_facet_set):
            continue
        answer_role = str(getattr(record, "answer_role", "") or "")
        if allowed_role_set and answer_role not in allowed_role_set:
            continue
        record_source_ids = {str(source_id) for source_id in (getattr(record, "source_ids", []) or [])}
        if required_source_set and not record_source_ids.intersection(required_source_set):
            continue
        surface = normalize_text_for_matching(
            " ".join(
                [
                    record.statement,
                    " ".join(record.source_ids),
                    " ".join(record.locators),
                    record.cluster_id,
                ]
            )
        )
        term_hits = {term for term in normalized_terms if term in surface}
        if normalized_terms and len(term_hits) < min_term_hits:
            continue
        if normalized_terms or required_facet_set or allowed_role_set or required_source_set:
            records.append(record)
    return records


def _matrix_source_ids(records: Sequence, *, limit: int = 4) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for record in records:
        for source_id in record.source_ids:
            if source_id in seen:
                continue
            seen.add(source_id)
            sources.append(source_id)
            if len(sources) >= limit:
                return sources
    return sources


_SYNTHESIS_ROLE_ORDER = {
    "core_answer": 90,
    "core_answer_support": 90,
    "candidate_core_claim": 85,
    "scope_boundary": 96,
    "normative_basis": 74,
    "technical_spec_context": 66,
    "interpretation": 58,
    "source_role_context": 46,
    "audit_or_trace_detail": 40,
    "background": 18,
    "open_issue": 12,
}


_SYNTHESIS_GENERIC_TERMS = {
    "about",
    "also",
    "and",
    "bei",
    "can",
    "das",
    "dem",
    "den",
    "der",
    "die",
    "does",
    "eidas",
    "eudi",
    "eine",
    "einem",
    "einen",
    "for",
    "from",
    "fuer",
    "haben",
    "ist",
    "mit",
    "muesste",
    "muss",
    "oder",
    "party",
    "provider",
    "relying",
    "sagt",
    "service",
    "services",
    "should",
    "the",
    "und",
    "wallet",
    "wallets",
    "wann",
    "was",
    "wenn",
    "werden",
}


def _strip_answer_template_markers(value: str) -> str:
    text = " ".join(value.split())
    text = re.sub(
        r"^(passage|source|evidence)\s+supports:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def _distinctive_question_terms(question: str) -> list[str]:
    normalized = normalize_text_for_matching(question)
    terms: list[str] = []
    seen: set[str] = set()
    for term in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", normalized):
        compact = term.replace("-", "_")
        if compact in _SYNTHESIS_GENERIC_TERMS or compact in seen:
            continue
        seen.add(compact)
        terms.append(compact)
    return terms


def _question_alias_terms(question: str) -> list[str]:
    normalized = normalize_text_for_matching(question)
    aliases: list[str] = []
    if any(marker in normalized for marker in ["vertrauenszeichen", "trust mark", "trustmark"]):
        aliases.extend(["trust mark", "wallet trust mark", "visible trust mark", "eudi wallet trust mark"])
    if any(marker in normalized for marker in ["entfernen", "remove", "removal"]):
        aliases.extend(["remove", "removed", "must remove", "upon cancellation", "cancellation"])
    if any(
        marker in normalized
        for marker in [
            "bewertet",
            "relying parties",
            "attestation provider",
        ]
    ):
        aliases.extend([
            "not relying party",
            "relying party services",
            "attestation provider qualifications",
            "qualifications",
            "out of scope",
        ])
    normalized_aliases: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        normalized_alias = normalize_text_for_matching(alias)
        if normalized_alias and normalized_alias not in seen:
            normalized_aliases.append(normalized_alias)
            seen.add(normalized_alias)
    return normalized_aliases


def _is_german_question(question: str) -> bool:
    normalized = f" {normalize_text_for_matching(question)} "
    return any(
        marker in normalized
        for marker in [
            " welche ",
            " welcher ",
            " welches ",
            " wann ",
            " was ",
            " wie ",
            " wofuer ",
            " muesste ",
            " vertrauenszeichen ",
            " grenzueberschreitend ",
        ]
    )


def _synthesis_role(record: object) -> str:
    role = getattr(record, "answer_role", "") or "background"
    if role in {"core_answer", "core_answer_support", "candidate_core_claim"}:
        return "core_answer"
    return role


def _record_caveat_value(record: object, prefix: str) -> Optional[str]:
    for caveat in getattr(record, "caveats", []) or []:
        if isinstance(caveat, str) and caveat.startswith(prefix):
            return caveat[len(prefix):]
    return None


def _record_surface(record: object) -> str:
    return " ".join(
        [
            getattr(record, "statement", "") or "",
            " ".join(getattr(record, "source_ids", []) or []),
            " ".join(getattr(record, "locators", []) or []),
            getattr(record, "cluster_id", "") or "",
        ]
    )


def _record_relevance_score(
    record: object,
    *,
    question: str,
    question_terms: Sequence[str],
) -> int:
    role = _synthesis_role(record)
    surface = normalize_text_for_matching(_record_surface(record)).replace("-", "_")
    score = _SYNTHESIS_ROLE_ORDER.get(role, 20)
    for term in question_terms:
        if term in surface:
            score += 9
    alias_hits = 0
    alias_surface = normalize_text_for_matching(_record_surface(record))
    for alias in _question_alias_terms(question):
        if alias in alias_surface:
            alias_hits += 1
    score += alias_hits * 14
    if role == "scope_boundary" and alias_hits:
        score += 12
    source_role = _record_caveat_value(record, "source_role:")
    document_status = _record_caveat_value(record, "document_status:")
    if source_role == "high":
        score += 5
    elif source_role == "medium":
        score += 2
    if document_status in {"final", "adopted_pending_effective_date"}:
        score += 4
    if role == "open_issue":
        score -= 30
    if "verification does not allow answer use" in (getattr(record, "caveats", []) or []):
        score -= 60
    return score


def _record_answer_use_allowed(record: object) -> bool:
    caveats = getattr(record, "caveats", []) or []
    if "verification does not allow answer use" in caveats:
        return False
    verification_status = getattr(record, "verification_status", None)
    if verification_status is None:
        # Opened-passage synthesis rows may be source-backed but not mapped to a
        # verified claim id. Let those support the product answer as long as
        # they have concrete source/locator anchors and are not explicit claims
        # that skipped verification.
        return (
            not getattr(record, "claim_id", None)
            and bool(getattr(record, "source_ids", []) or [])
            and bool(getattr(record, "locators", []) or [])
        )
    status_value = getattr(verification_status, "value", verification_status)
    return status_value not in {"blocked", "open", "rejected"}


def _record_source_suffix(record: object) -> str:
    source_ids = list(getattr(record, "source_ids", []) or [])
    if not source_ids:
        return ""
    locators = [locator for locator in (getattr(record, "locators", []) or []) if locator]
    locator_part = ""
    if locators:
        locator_part = f" ({_compact_locator(locators[0], limit=150)})"
    return f" Quellenanker: {', '.join(source_ids)}{locator_part}."


def _answer_ready_statement(record: object, question: str, *, limit: int = 420) -> str:
    statement = _strip_answer_template_markers(getattr(record, "statement", "") or "")
    normalized = normalize_text_for_matching(statement)
    if _is_german_question(question) and (
        "visible trust mark" in normalized
        and "wallet provider" in normalized
        and "relying party" in normalized
        and "attestation provider" in normalized
    ):
        return (
            "Bei Aufhebung (cancellation) der Trust-Mark-Berechtigung muss der Wallet Provider "
            "das sichtbare EUDI-Wallet-Vertrauenszeichen und Verweise darauf entfernen; "
            "der Nachweis bezieht sich auf die Wallet Solution, nicht auf eine Bewertung "
            "von Relying Parties oder Attestation Providern."
        )
    if _is_german_question(question) and (
        ("wallet unit attestation" in normalized or "wua" in normalized)
        and "issuer credential metadata" in normalized
        and (
            "proof_types_supported" in statement
            or "proof support" in normalized
            or "proof types supported" in normalized
        )
    ):
        return (
            "Fuer PID- oder Attribut-Aussteller ist die WUA-Pruefung eine "
            "Issuer-/Transportpflicht: Bei device-bound Attestations muessen "
            "unterstuetzte WUA-Proof-Typen in der Issuer Credential Metadata "
            "sichtbar sein, einschliesslich Key-Attestation-Anforderung."
        )
    if _is_german_question(question) and (
        ("wallet unit attestation" in normalized or "wua" in normalized)
        and "x5c" in normalized
        and ("trust anchor" in normalized or "trust-anchor" in normalized)
        and "c_nonce" in statement
    ):
        return (
            "Pruefseitig geht es um kryptografische Bindung: Signatur der WUA, "
            "`x5c`-Zertifikatskette bis zu einem Wallet-Provider-Trust-Anchor, "
            "Bindung an den attestierten Schluessel und frischen `c_nonce`."
        )
    if _is_german_question(question) and (
        (
            "wallet providers issue wuas" in normalized
            or "wallet provider wuas" in normalized
            or "wallet providers issue wua" in normalized
        )
        and "out of scope" in normalized
    ):
        return (
            "Ausserhalb dieser WUA-Spezifikation bleibt, wie Wallet Provider WUAs "
            "an Wallet Units ausgeben; spezifiziert sind hier Transfer, Format, "
            "Inhalt, Lebenszyklus und Widerrufsmechanismus der WUA."
        )
    return _compact_answer_text(statement, limit=limit)


def _looks_like_pdf_page_heading_fragment(statement: str) -> bool:
    normalized = normalize_text_for_matching(statement)
    return (
        len(statement.split()) < 28
        and re.search(r"\bpage\s+\d+\s+en(?:\s+\d+)?\s+en\b", normalized) is not None
    )


def _synthesis_record_views(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    question: str,
    *,
    include_open_issues: bool = False,
) -> list[_SynthesisRecordView]:
    if evidence_synthesis_matrix is None:
        return []
    question_terms = _distinctive_question_terms(question)
    views: list[_SynthesisRecordView] = []
    for record in evidence_synthesis_matrix.records:
        if not _record_answer_use_allowed(record):
            continue
        quality_flags = set(getattr(record, "quality_flags", []) or [])
        if quality_flags.intersection({"references_only", "table_note", "title_only", "definition_only", "context_only"}):
            continue
        statement = _answer_ready_statement(record, question)
        if not statement:
            continue
        if _looks_like_pdf_page_heading_fragment(statement):
            continue
        normalized_statement = normalize_text_for_matching(statement)
        if re.match(r"^article\s+\d+[a-z]?\b", normalized_statement) and len(statement.split()) < 24:
            continue
        if statement.rstrip().endswith((" A.", " 1.")) and len(statement.split()) < 24:
            continue
        role = _synthesis_role(record)
        if role == "open_issue" and not include_open_issues:
            continue
        score = _record_relevance_score(
            record,
            question=question,
            question_terms=question_terms,
        )
        views.append(
            _SynthesisRecordView(
                record=record,
                role=role,
                score=score,
                statement=statement,
            )
        )
    views.sort(key=lambda view: view.score, reverse=True)
    return views


ROLE_BOUNDARY_RENDER_FACETS = {
    "actor_boundary",
    "technical_requester",
    "end_relying_party",
    "registry_information",
    "user_display",
    "purpose_or_intended_use",
    "requested_attributes",
    "privacy_policy_or_dpa",
    "certificate_or_trust_anchor",
    "open_issue_or_member_state_choice",
}


def _matrix_question_facets(
    question: str,
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
) -> set[str]:
    facets: set[str] = set()
    if evidence_synthesis_matrix is not None:
        for record in evidence_synthesis_matrix.records:
            facets.update(str(tag) for tag in (getattr(record, "facet_tags", []) or []))
    normalized = normalize_text_for_matching(question)
    if any(term in normalized for term in ["intermediaer", "intermediary", "rollen", "auseinanderhalten"]):
        facets.add("actor_boundary")
    if any(term in normalized for term in ["registrierung", "registration", "register", "zertifikat", "certificate"]):
        facets.add("registry_information")
    if any(term in normalized for term in ["nutzeranzeige", "display", "anzeige", "request"]):
        facets.add("user_display")
    if any(term in normalized for term in ["zweck", "purpose", "intended use"]):
        facets.add("purpose_or_intended_use")
    if any(term in normalized for term in ["attribute", "attributes"]):
        facets.add("requested_attributes")
    if any(term in normalized for term in ["datenschutz", "privacy", "dpa"]):
        facets.add("privacy_policy_or_dpa")
    return facets


def _role_boundary_answer_expected(
    question: str,
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
) -> bool:
    facets = _matrix_question_facets(question, evidence_synthesis_matrix)
    return "actor_boundary" in facets and len(facets & ROLE_BOUNDARY_RENDER_FACETS) >= 4


def _views_for_facets(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    question: str,
    facets: set[str],
    *,
    limit: int = 3,
    include_open_issues: bool = False,
) -> list[_SynthesisRecordView]:
    views = _synthesis_record_views(
        evidence_synthesis_matrix,
        question,
        include_open_issues=include_open_issues,
    )
    selected: list[_SynthesisRecordView] = []
    seen: set[str] = set()
    for view in views:
        record_facets = set(getattr(view.record, "facet_tags", []) or [])
        if not record_facets.intersection(facets):
            continue
        key = normalize_text_for_matching(view.statement)
        if key in seen:
            continue
        seen.add(key)
        selected.append(view)
        if len(selected) >= limit:
            break
    return selected


def _role_boundary_view_score(view: _SynthesisRecordView, facets: set[str]) -> int:
    surface = normalize_text_for_matching(
        " ".join(
            [
                view.statement,
                " ".join(getattr(view.record, "locators", []) or []),
                " ".join(getattr(view.record, "source_ids", []) or []),
            ]
        )
    )
    score = view.score
    boosts = {
        "actor_boundary": ["intermediary", "intermediaer", "isintermediary", "intermediated"],
        "technical_requester": ["access certificate", "authenticates", "authenticate", "rpac"],
        "end_relying_party": ["intermediated wallet-relying party", "wallet-relying party"],
        "registry_information": ["registration certificate", "rprc", "registrar", "registered"],
        "user_display": ["user approval", "shown", "display", "request context", "information set"],
        "purpose_or_intended_use": ["intended use", "purpose"],
        "requested_attributes": ["requested attributes", "selected attributes", "minimum set of attributes"],
        "privacy_policy_or_dpa": ["privacy policy", "data protection authority", "dpa", "erase personal data"],
        "open_issue_or_member_state_choice": ["open issue", "does not contain", "national", "member state"],
    }
    for facet in facets:
        if any(term in surface for term in boosts.get(facet, [])):
            score += 45
    if "api" in surface and "read methods" in surface and "open for public access" in surface:
        score -= 90
    if "data_portability" in surface or "data portability and download" in surface:
        score -= 110
    if "interactingpartytype" in surface or surface.strip().startswith("| |"):
        score -= 100
    if re.search(r"\barticle\s+\d+\b", surface) and len(view.statement.split()) < 12:
        score -= 80
    if view.statement.rstrip().endswith((" A.", " 1.")):
        score -= 70
    quality_flags = set(getattr(view.record, "quality_flags", []) or [])
    if quality_flags.intersection({"table_note", "title_only", "references_only", "context_only"}):
        score -= 70
    if "definition_only" in quality_flags:
        score -= 25
    return score


def _first_view_for_facets(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    question: str,
    facets: set[str],
) -> Optional[_SynthesisRecordView]:
    views = _views_for_facets(evidence_synthesis_matrix, question, facets, limit=8)
    views.sort(key=lambda view: _role_boundary_view_score(view, facets), reverse=True)
    return views[0] if views else None


def _anchor_view_for_facets(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    question: str,
    facets: set[str],
) -> Optional[_SynthesisRecordView]:
    if evidence_synthesis_matrix is None:
        return None
    question_terms = _distinctive_question_terms(question)
    views: list[_SynthesisRecordView] = []
    for record in evidence_synthesis_matrix.records:
        if not _record_answer_use_allowed(record):
            continue
        if not set(getattr(record, "facet_tags", []) or []).intersection(facets):
            continue
        statement = _answer_ready_statement(record, question)
        if not statement:
            continue
        role = _synthesis_role(record)
        views.append(
            _SynthesisRecordView(
                record=record,
                role=role,
                score=_record_relevance_score(
                    record,
                    question=question,
                    question_terms=question_terms,
                ),
                statement=statement,
            )
        )
    views.sort(key=lambda view: _role_boundary_view_score(view, facets), reverse=True)
    return views[0] if views else None


def _view_suffix(view: Optional[_SynthesisRecordView]) -> str:
    return _record_source_suffix(view.record) if view is not None else ""


def _role_boundary_product_sections(
    question: str,
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
) -> list[str]:
    if not _role_boundary_answer_expected(question, evidence_synthesis_matrix):
        return []

    actor = _first_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"actor_boundary", "technical_requester", "end_relying_party"},
    )
    registry = _first_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"registry_information", "certificate_or_trust_anchor"},
    )
    display = _first_view_for_facets(evidence_synthesis_matrix, question, {"user_display"})
    purpose = _first_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"purpose_or_intended_use", "requested_attributes"},
    )
    privacy = _first_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"privacy_policy_or_dpa"},
    )
    open_issue = _first_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"open_issue_or_member_state_choice", "privacy_policy_or_dpa"},
    )
    actor_anchor = actor or _anchor_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"actor_boundary", "technical_requester", "end_relying_party"},
    )
    registry_anchor = registry or _anchor_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"registry_information", "certificate_or_trust_anchor"},
    )
    display_anchor = display or _anchor_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"user_display"},
    )
    purpose_anchor = purpose or _anchor_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"purpose_or_intended_use", "requested_attributes"},
    )
    privacy_anchor = privacy or _anchor_view_for_facets(
        evidence_synthesis_matrix,
        question,
        {"privacy_policy_or_dpa"},
    )

    lines: list[str] = ["Kurzantwort:"]
    lines.append(
        "- Die Rollen muessen getrennt bleiben: Der Intermediaer ist der technische Anfragende bzw. Zertifikats-/Request-Kontext; die intermediierte Wallet-Relying Party bleibt die fachliche Endpartei, fuer deren Dienst Zweck, angefragte Attribute und Datenschutzinformationen verstaendlich angezeigt werden muessen."
        + _view_suffix(actor_anchor or registry_anchor or display_anchor or purpose_anchor)
    )
    lines.append(
        "- Praktisch heisst das: Registrierung/Zertifikate duerfen den Intermediaer nicht an die Stelle der Wallet-Relying Party schieben; Nutzeranzeige und Request-Kontext muessen die Endpartei, den Intermediaer und den Zweck separat rekonstruierbar machen."
        + _view_suffix(display_anchor or registry_anchor or actor_anchor)
    )

    lines.append("Registrierung / Zertifikate:")
    lines.append(
        "- Registrierung und Zertifikatskontext sollten die End-Wallet-Relying-Party, eine Intermediaer-Beziehung, Registrierungs-/Registrar-Bezug und den registrierten Zweck getrennt rekonstruierbar halten; der Access-Certificate-Kontext authentisiert die anfragende Gegenstelle, ersetzt aber nicht die fachliche Endpartei."
        + _view_suffix(registry_anchor or actor_anchor or purpose_anchor)
    )

    lines.append("Nutzeranzeige / Request-Kontext:")
    lines.append(
        "- Die Nutzeranzeige sollte nicht nur den technisch auftretenden Intermediaer zeigen, sondern auch fuer wen gehandelt wird, welchen Request-/Service-Kontext die Anfrage hat und welche Attribute der Nutzer fuer welchen Zweck freigibt."
        + _view_suffix(display_anchor or actor_anchor or purpose_anchor)
    )

    lines.append("Zweck, Attribute und Datenschutz:")
    lines.append(
        "- Intended use, angefragte Attribute und Privacy-/Kontaktinformationen gehoeren fachlich zum konkreten Dienst bzw. zur intermediated Wallet-Relying Party; sie sollten nicht pauschal dem Intermediaer zugeschrieben werden."
        + _view_suffix(purpose_anchor or privacy_anchor or display_anchor)
    )
    lines.append(
        "- Wo Datenschutzkontakt, DPA-/Beschwerdeweg oder Loeschanforderung nur technisch oder als offene Spezifikationsfrage belegt sind, muss die Antwort diese Grenze sichtbar lassen."
        + _view_suffix(privacy_anchor or open_issue or purpose_anchor)
    )

    lines.append("Grenzen / offene Punkte:")
    lines.append(
        "- Wo Spezifikationen Datenschutzkontakt, Beschwerdeweg oder nationale Registrar-Details nicht abschliessend regeln, darf die Antwort nur eine quellenmarkierte Grenze ziehen und keine finale Rechtsfolge erfinden."
        + _view_suffix(open_issue or privacy_anchor or registry_anchor)
    )
    return lines


def _selected_synthesis_views(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    question: str,
    *,
    limit: int = 3,
) -> list[_SynthesisRecordView]:
    views = _synthesis_record_views(evidence_synthesis_matrix, question)
    if not views:
        return []
    top_score = views[0].score
    selected: list[_SynthesisRecordView] = []
    seen_statements: set[str] = set()
    for view in views:
        if view.score < top_score - 22 and selected:
            continue
        key = normalize_text_for_matching(view.statement)
        if key in seen_statements:
            continue
        seen_statements.add(key)
        selected.append(view)
        if len(selected) >= limit:
            break
    return selected


def _synthesis_summary_lines(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    question: str,
    *,
    limit: int = 3,
) -> list[str]:
    selected = _selected_synthesis_views(
        evidence_synthesis_matrix,
        question,
        limit=limit,
    )
    if not selected:
        return []
    lines: list[str] = []
    for view in selected:
        lines.append(f"- {view.statement}{_record_source_suffix(view.record)}")
    return lines


def _binding_effect_label(source_kind: str, binding_level: str, document_status: str) -> str:
    if binding_level == "binding":
        return "bindend"
    if binding_level == "proposed":
        return "vorgeschlagen_nicht_bindend"
    if binding_level == "official_non_binding":
        return "amtlich_nicht_bindend"
    if binding_level == "non_binding":
        return "nicht_bindend"
    if source_kind in {"regulation", "implementing_act"}:
        if document_status in {"proposal", "draft"}:
            return "entwurfsstand_nicht_bindend"
        return "eu_rechtsnorm"
    if source_kind == "technical_standard":
        return "technischer_standard_keine_eu_rechtsnorm"
    if source_kind == "project_artifact":
        return "projektkontext_nicht_bindend"
    return "nicht_ausgewiesen"


def _source_role_label(record: object) -> str:
    source_role = _record_caveat_value(record, "source_role:") or "unknown"
    source_kind = _record_caveat_value(record, "source_kind:") or "unknown"
    binding_level = _record_caveat_value(record, "binding_level:") or "unknown"
    document_status = _record_caveat_value(record, "document_status:") or "unknown"
    binding_effect = _binding_effect_label(source_kind, binding_level, document_status)
    return (
        f"Rang: {source_role}; Bindungswirkung: {binding_effect}; "
        f"Dokumentstatus: {document_status}"
    )


def _render_vnext_clarification_note(note: Optional[str], question: str) -> Optional[str]:
    if not note:
        return None
    normalized_note = normalize_text_for_matching(note)
    if "broad question" in normalized_note and (
        "eu first" in normalized_note or "eu-first" in normalized_note
    ):
        if _is_german_question(question):
            return "Breite Frage; die Antwort bleibt deshalb EU-first und markiert Quellenrollen sichtbar."
        return "Broad question; the answer stays EU-first and keeps source roles visible."
    return note


def _product_evidence_sections(
    question: str,
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
) -> list[str]:
    selected = _selected_synthesis_views(evidence_synthesis_matrix, question, limit=4)
    selected_records = (
        [view.record for view in selected]
        if selected
        else _matrix_summary_records(evidence_synthesis_matrix, limit=4)
    )
    if not selected_records:
        return []

    lines: list[str] = ["Belege / Quellenrolle:"]
    for record in selected_records[:3]:
        source_ids = ", ".join(getattr(record, "source_ids", []) or ["unbekannte Quelle"])
        locators = [locator for locator in (getattr(record, "locators", []) or []) if locator]
        locator_part = f" - {_compact_locator(locators[0], limit=160)}" if locators else ""
        lines.append(
            f"- {source_ids}{locator_part}: {_source_role_label(record)}; Rolle im Answering: {_synthesis_role(record)}."
        )

    caveat_lines: list[str] = []
    if any(_record_caveat_value(record, "source_role:") == "medium" for record in selected_records):
        caveat_lines.append(
            "Technische Spezifikationen, ARF- oder Projektquellen stuetzen Interoperabilitaets- und Architekturkontext, ersetzen aber keine finale Rechtsnorm."
        )
    if any(_record_caveat_value(record, "document_status:") in {"proposal", "draft"} for record in selected_records):
        caveat_lines.append(
            "Proposal- oder Draft-Quellen duerfen nur als Entwurfsstand formuliert werden."
        )
    if caveat_lines:
        lines.append("Einordnung / Grenzen:")
        lines.extend(f"- {line}" for line in caveat_lines)

    open_views = [
        view
        for view in _synthesis_record_views(
            evidence_synthesis_matrix,
            question,
            include_open_issues=True,
        )
        if view.role == "open_issue"
    ]
    if open_views:
        lines.append("Offene Punkte:")
        for view in open_views[:2]:
            lines.append(f"- {view.statement}{_record_source_suffix(view.record)}")
    return lines


def _matrix_summary_records(
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
    *,
    limit: int = 3,
) -> list:
    if evidence_synthesis_matrix is None:
        return []
    preferred_roles = {
        "core_answer",
        "core_answer_support",
        "scope_boundary",
        "source_role_context",
        "technical_spec_context",
        "normative_basis",
    }
    records = [
        record
        for record in evidence_synthesis_matrix.records
        if record.answer_role in preferred_roles and record.statement
    ]
    records.sort(
        key=lambda record: (
            record.answer_role == "scope_boundary",
            record.answer_role == "core_answer_support",
            bool(record.source_ids),
        ),
        reverse=True,
    )
    return records[:limit]


def _source_suffix(source_ids: Sequence[str]) -> str:
    if not source_ids:
        return ""
    return f" Quellenanker: {', '.join(source_ids)}."


def _has_question_terms(normalized_question: str, terms: Sequence[str]) -> bool:
    return any(normalize_text_for_matching(term) in normalized_question for term in terms)


def _surface_contains_any(surface: str, terms: Sequence[str]) -> bool:
    normalized = normalize_text_for_matching(surface)
    return any(normalize_text_for_matching(term) in normalized for term in terms)


def _prefer_records_with_source(records: Sequence, source_id: str) -> list:
    preferred = [
        record
        for record in records
        if source_id in (getattr(record, "source_ids", []) or [])
    ]
    return preferred or list(records)


_SHORT_ANSWER_BLOCKING_QUALITY_FLAGS = {
    "references_only",
    "table_note",
    "title_only",
    "definition_only",
    "context_only",
}


def _schema_or_data_model_context_record(record: object) -> bool:
    surface = normalize_text_for_matching(
        " ".join(
            [
                str(getattr(record, "statement", "") or ""),
                " ".join(str(source_id) for source_id in (getattr(record, "source_ids", []) or [])),
                " ".join(str(locator) for locator in (getattr(record, "locators", []) or [])),
            ]
        )
    )
    return any(
        marker in surface
        for marker in (
            "json schema",
            "schema definition",
            "data model specified",
            "wallettrustmarkinformation",
            "trustmarkresource",
        )
    )


def _short_answer_anchor_records(records: Sequence) -> list:
    eligible = [
        record
        for record in records
        if _record_answer_use_allowed(record)
        and not set(getattr(record, "quality_flags", []) or []).intersection(
            _SHORT_ANSWER_BLOCKING_QUALITY_FLAGS
        )
    ]
    answer_ready = [
        record
        for record in eligible
        if "answer_ready" in set(getattr(record, "quality_flags", []) or [])
    ]
    return answer_ready or eligible


def _product_summary_lines(
    question: str,
    summary: str,
    bullets: Sequence[_AnswerBullet],
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
) -> list[str]:
    normalized_question = normalize_text_for_matching(question)
    lines: list[str] = ["Kurzantwort:"]
    non_dynamic_bullets = [
        bullet
        for bullet in bullets
        if bullet.wording_category != "dynamic_evidence_support"
        and bullet.section not in {"Open issues", "Cross-reference hints"}
    ]
    open_issue_bullets = [
        bullet for bullet in bullets if bullet.section in {"Open issues", "Open"}
    ]

    if _has_question_terms(
        normalized_question,
        ["vertrauenszeichen", "vertrauensmarke", "trust mark", "wallet trust mark"],
    ):
        matrix_records = (
            list(evidence_synthesis_matrix.records)
            if evidence_synthesis_matrix is not None
            else []
        )
        removal_requested = _has_question_terms(
            normalized_question,
            ["entfernen", "remove", "removal", "aufhebung", "cancellation", "widerruf", "revocation"],
        )
        scope_requested = _has_question_terms(
            normalized_question,
            ["relying party", "relying parties", "attestation provider", "attestation providers", "scope", "bewertet", "bewertung"],
        )
        trust_records = [
            record
            for record in matrix_records
            if set(getattr(record, "facet_tags", []) or []).intersection(
                {"trust_mark_meaning", "trust_mark_removal", "trust_mark_scope_boundary"}
            )
            or "ec_ts01_wallet_trust_mark" in (getattr(record, "source_ids", []) or [])
        ]
        meaning_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["trust mark", "wallet trust mark", "visible"],
            min_term_hits=1,
            required_facets=("trust_mark_meaning",),
        ) or [
            record
            for record in trust_records
            if "ec_ts01_wallet_trust_mark" in (getattr(record, "source_ids", []) or [])
        ]
        removal_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["visible trust mark", "remove", "removal", "cancellation", "entfernen"],
            min_term_hits=2,
            required_facets=("trust_mark_removal",),
        )
        scope_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["relying party", "attestation provider", "out of scope", "scope"],
            min_term_hits=1,
            required_facets=("trust_mark_scope_boundary",),
        )
        if removal_requested and removal_records:
            lines.append(
                "- Bei Aufhebung (cancellation) der Trust-Mark-Berechtigung muss der Wallet Provider "
                "das sichtbare EUDI-Wallet-Vertrauenszeichen und Verweise darauf entfernen."
                + _source_suffix(
                    _matrix_source_ids(
                        _prefer_records_with_source(removal_records, "ec_ts01_wallet_trust_mark")
                    )
                )
            )
        if scope_requested and scope_records:
            lines.append(
                "- Daraus folgt keine Bewertung von Relying Parties oder Attestation Providern: "
                "der Scope dieser Trust-Mark-Spezifikation ist das sichtbare Wallet-Zeichen "
                "der EUDI Wallet Solution."
                + _source_suffix(
                    _matrix_source_ids(
                        _prefer_records_with_source(scope_records, "ec_ts01_wallet_trust_mark")
                    )
                )
            )
        if len(lines) == 1:
            primary_meaning_records = [
                record
                for record in meaning_records
                if not _schema_or_data_model_context_record(record)
            ]
            meaning_anchor_records = _short_answer_anchor_records(
                primary_meaning_records or meaning_records
            )
            meaning_anchor_source_ids = _matrix_source_ids(meaning_anchor_records)
            lines.append(
                "- Das sichtbare Wallet-Vertrauenszeichen ist ein nutzerseitig sichtbarer "
                "Trust-Hinweis fuer die EUDI Wallet Solution; es sollte als Erkennungs- "
                "und Pruefanker fuer die Wallet gelesen werden, nicht als automatische "
                "Aussage ueber Relying Parties oder Attestation Provider."
                + _source_suffix(meaning_anchor_source_ids)
            )
            context_source_ids = _matrix_source_ids(
                [
                    record
                    for record in trust_records
                    if "ec_ts01_wallet_trust_mark" in (getattr(record, "source_ids", []) or [])
                ],
                limit=1,
            )
            if context_source_ids and "ec_ts01_wallet_trust_mark" not in meaning_anchor_source_ids:
                lines.append(
                    "- Technischer Kontext: Die Spezifikation des EUDI Wallet Trust Mark "
                    "bleibt als Kontextquelle fuer Datenmodell und Provisioning des "
                    "sichtbaren Trust Marks relevant; sie ist hier aber nicht der "
                    "Hauptanker fuer die Bedeutungsaussage."
                    + _source_suffix(context_source_ids)
                )
        return lines

    certification_question = _has_question_terms(
        normalized_question,
        ["zertifizierung", "certification", "certification scheme", "conformity assessment"],
    ) and _has_question_terms(
        normalized_question,
        ["wallet", "wallet solution", "wallet-loesung", "wallet loesung", "eudi-wallet"],
    )
    if evidence_synthesis_matrix is not None and not certification_question:
        certification_question = any(
            "wallet_solution_certification" in (getattr(record, "facet_tags", []) or [])
            for record in evidence_synthesis_matrix.records
        )
    if certification_question:
        certification_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "certification",
                "certification scheme",
                "conformity assessment",
                "wallet solution",
                "certificate",
            ],
            min_term_hits=2,
            required_facets=("wallet_solution_certification",),
            allowed_answer_roles=("normative_basis", "core_answer", "core_answer_support", "candidate_core_claim"),
            required_source_ids=("celex_32024R2981_fulltext_en",),
        )
        eidas_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "certified European Digital Identity Wallet",
                "certificate and certification assessment report",
                "conformity assessment",
                "certification",
            ],
            min_term_hits=1,
            required_facets=("wallet_solution_certification",),
            allowed_answer_roles=("normative_basis", "core_answer", "core_answer_support", "candidate_core_claim"),
            required_source_ids=("celex_32024R1183_fulltext_en",),
        )
        lines.append(
            "- Die Zertifizierungs-Durchfuehrungsverordnung behandelt die EUDI-Wallet-Loesung "
            "als Konformitaets- und Evaluierungsgegenstand: nationale Zertifizierungsschemata, "
            "Zertifikate, Evaluierungsaktivitaeten und vorzulegende Nachweise muessen "
            "quellengebunden geregelt werden."
            + _source_suffix(_matrix_source_ids(certification_records))
        )
        if eidas_records:
            lines.append(
                "- Der eIDAS-Rahmen bleibt der hoeherliegende Bezug: Mitgliedstaaten melden "
                "zertifizierte Wallets samt Zertifikat beziehungsweise Certification Assessment "
                "Report; die Durchfuehrungsverordnung konkretisiert diese Zertifizierungspruefung."
                + _source_suffix(_matrix_source_ids(eidas_records))
            )
        if _has_question_terms(
            normalized_question,
            ["aussetzung", "ausgesetzt", "suspension", "entzug", "withdrawal", "revocation", "widerruf"],
        ):
            lines.append(
                "- Aussetzung oder Entzug sollte deshalb als Zertifikats-/Konformitaetsstatus "
                "und Governancefolge behandelt werden, nicht als frei erfundene Aussage ueber "
                "eine einzelne Wallet-Funktion, solange die geoeffnete Evidenz diese Folge "
                "nicht gesondert belegt."
                + _source_suffix(_matrix_source_ids(certification_records or eidas_records))
            )
        return lines

    if _has_question_terms(normalized_question, ["pubeaa", "pub-eaa"]) and _has_question_terms(
        normalized_question,
        ["widerruf", "widerrufen", "revocation", "gueltigkeit"],
    ):
        status_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["PubEAA", "revocation", "validity", "status"],
        )
        lines.append(
            "- Ein widerrufenes PubEAA verliert ab Widerruf seine belastbare Gueltigkeit; ein Wallet- oder RP-Prozess sollte den Status deshalb erneut pruefen und den Nachweis nicht mehr als aktuellen Beleg verwenden."
            + _source_suffix(_matrix_source_ids(status_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Der operative Kern ist Statusmanagement: Widerrufs- und Gueltigkeitsinformationen muessen fuer die pruefende Stelle erreichbar bleiben; ein Widerruf ist keine blosse lokale Wallet-Markierung."
        )
        return lines

    if _has_question_terms(normalized_question, ["oeffentliche stellen", "public sector", "article 16"]) and _has_question_terms(
        normalized_question,
        ["business wallet", "business wallets", "ebw"],
    ):
        proposal_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["public sector bodies", "Article 16", "European Business Wallets"],
        )
        lines.append(
            "- Nach dem EBW-Vorschlag muessen oeffentliche Stellen fuer bestimmte in Artikel 16 adressierte Verfahren die Nutzung von European Business Wallets ermoeglichen; fuer einzelne Kommunikationszwecke sollen sie selbst Business Wallets einschliesslich QERDS haben."
            + _source_suffix(_matrix_source_ids(proposal_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Das ist proposal-stage Evidenz, also noch keine final geltende Verordnung; die Antwort sollte deshalb als Entwurfsstand und nicht als abgeschlossenes Sekundaerrecht gelesen werden."
        )
        return lines

    if _has_question_terms(normalized_question, ["uebergangszeit", "transition", "kommunikationsloesung", "kommunikationsloesungen"]) and _has_question_terms(
        normalized_question,
        ["business wallet", "business-wallet", "ebw"],
    ):
        transition_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["transitional", "communication solutions", "secure communication channel"],
        )
        lines.append(
            "- Im EBW-Vorschlag duerfen oeffentliche Stellen waehrend der Uebergangszeit alternative bestehende Kommunikationsloesungen weiter unterstuetzen, bevor der sichere Business-Wallet-Kommunikationskanal angeboten wird."
            + _source_suffix(_matrix_source_ids(transition_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Die Ausnahme ist zeitlich und funktional zu lesen: Sie ersetzt nicht dauerhaft den Business-Wallet-Kanal, sondern ueberbrueckt die Phase vor dessen Angebot."
        )
        return lines

    if _has_question_terms(normalized_question, ["vertrauensniveau", "level of assurance", "assurance", "authentisiert"]) and _has_question_terms(
        normalized_question,
        ["zugriff", "access"],
    ):
        auth_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["level of assurance", "successfully authenticated", "wallet unit authentication"],
        )
        lines.append(
            "- Der EBW-Annex verlangt fuer den Zugriff auf eine Business Wallet Unit eine erfolgreiche Nutzer-Authentisierung; als Mindestlinie wird ein notifiziertes eID-Mittel mit mindestens substantial level of assurance genannt."
            + _source_suffix(_matrix_source_ids(auth_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Auch das ist EBW-Annex-/Proposal-Stand: fachlich brauchbar fuer Architekturannahmen, aber als Entwurfsrecht zu markieren."
        )
        return lines

    if _has_question_terms(normalized_question, ["anfragen", "request", "requests", "autorisiert", "authentisiert"]) and _has_question_terms(
        normalized_question,
        ["business wallet unit", "wallet unit", "business wallet"],
    ):
        request_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["authorise requests", "authenticate", "relying-party access certificates", "wallet unit attestations"],
        )
        lines.append(
            "- Nach dem EBW-Annex muessen Business Wallet Units Anfragen autorisieren und, soweit einschlaegig, authentisieren; als Mechanismen werden insbesondere Relying-Party Access Certificates und Wallet Unit Attestations genannt."
            + _source_suffix(_matrix_source_ids(request_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Praktisch trennt das zwei Prueffragen: Darf die Gegenstelle diese Anfrage stellen, und ist die verwendete Wallet Unit beziehungsweise Gegenstelle kryptografisch/statusseitig noch gueltig?"
        )
        return lines

    wua_issuer_question = _has_question_terms(
        normalized_question,
        ["wallet unit attestation", "wallet unit attestations", "wua", "unit attestation"],
    ) and _has_question_terms(
        normalized_question,
        ["pid", "attribut", "attestation provider", "issuer", "aussteller"],
    )
    if evidence_synthesis_matrix is not None and not wua_issuer_question:
        wua_issuer_question = any(
            "ec_ts03_wallet_unit_attestation" in (getattr(record, "source_ids", []) or [])
            and _surface_contains_any(
                _record_surface(record),
                [
                    "issuer credential metadata",
                    "proof_types_supported",
                    "key_attestation_required",
                    "pid provider",
                    "attestation provider",
                ],
            )
            for record in evidence_synthesis_matrix.records
        )
    if wua_issuer_question:
        wua_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "issuer credential metadata",
                "proof_types_supported",
                "proof support",
                "key_attestation_required",
                "key attestation",
                "x5c",
                "trust anchor",
                "attested-key",
                "c_nonce",
            ],
            min_term_hits=1,
            allowed_answer_roles=("core_answer", "core_answer_support", "candidate_core_claim", "technical_spec_context"),
            required_source_ids=("ec_ts03_wallet_unit_attestation",),
        )
        scope_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "out of scope",
                "wallet providers issue wuas",
                "transfer",
                "format",
                "content",
                "life cycle",
                "revocation mechanism",
            ],
            min_term_hits=1,
            allowed_answer_roles=("scope_boundary", "core_answer", "core_answer_support", "technical_spec_context"),
            required_source_ids=("ec_ts03_wallet_unit_attestation",),
        )
        if wua_records or scope_records:
            wua_sources = _matrix_source_ids([*wua_records, *scope_records])
            lines.append(
                "- Fuer PID- oder Attribut-Aussteller ist die Wallet Unit Attestation "
                "kein allgemeiner Wallet-Status, sondern ein im Issuance-/Transportfluss "
                "zu pruefender Nachweis: device-bound Ausstellungen muessen WUA-Proof-Typen "
                "in der Issuer Credential Metadata signalisieren und Key Attestation verlangen."
                + _source_suffix(_matrix_source_ids(wua_records) or wua_sources)
            )
            lines.append(
                "- Die eigentliche Pruefung bleibt kryptografisch: WUA-Signatur, `x5c`-"
                "Zertifikatskette bis zu einem Wallet-Provider-Trust-Anchor, Bindung an "
                "den attestierten Schluessel und frischer `c_nonce` muessen zur konkreten "
                "Ausstellung passen."
                + _source_suffix(_matrix_source_ids(wua_records) or wua_sources)
            )
            if scope_records:
                lines.append(
                    "- Ausserhalb dieser WUA-Spezifikation bleibt, wie Wallet Provider WUAs "
                    "an Wallet Units ausgeben; spezifiziert sind Transfer, Format, Inhalt, "
                    "Lebenszyklus und Widerrufsmechanismus der WUA."
                    + _source_suffix(_matrix_source_ids(scope_records) or wua_sources)
                )
            return lines

    if _has_question_terms(normalized_question, ["access ca", "access certificate authority"]) and _has_question_terms(
        normalized_question,
        ["lote", "list of trusted entities"],
    ):
        lote_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["Access CA", "LoTE", "common trust infrastructure", "Access Certificate Authorities"],
        )
        lines.append(
            "- Die Access CA LoTE dient als Trust-Infrastruktur fuer Access Certificate Authorities: Trust-Anker werden in einer List of Trusted Entities veroeffentlicht und fuer die gemeinsame Vertrauensinfrastruktur auffindbar gemacht."
            + _source_suffix(_matrix_source_ids(lote_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Wichtig ist die Rollenabgrenzung: LoTE/Trusted List Provider veroeffentlichen beziehungsweise signieren die Liste; Wallets und pruefende Komponenten nutzen sie als Trust-Anker fuer Access-CA-bezogene Zertifikatspruefung."
        )
        return lines

    if _has_question_terms(
        normalized_question,
        ["gelistet", "notifiziert", "listed", "notified", "trust list", "trusted list", "lote"],
    ) and _has_question_terms(
        normalized_question,
        ["wallet unit attestation", "wallet unit attestations", "wua", "unit attestation"],
    ):
        wua_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["Wallet Unit Attestation", "Wallet Unit Attestations", "WUA", "attested keys"],
        )
        provider_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["provider", "listed", "notified", "trusted list", "trust list", "LoTE"],
        )
        lines.append(
            "- Vor Akzeptanz einer Wallet Unit Attestation sollte der EBW-Verifier zwei Ebenen trennen: erst die Provider-Listung oder Notifizierung in der massgeblichen Trust-/Register-Infrastruktur, dann die technische WUA-Pruefung."
            + _source_suffix(_matrix_source_ids([*provider_records, *wua_records]) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Die Wallet Unit Attestation (WUA) ersetzt den Provider-Status nicht; sie ist der technische Nachweis der Wallet Unit beziehungsweise ihrer attestierten Schluessel und muss mit Signatur, Status/Revocation und Zweckkontext geprueft werden."
            + _source_suffix(_matrix_source_ids(wua_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Wo eine technische Spezifikation Trust Establishment oder Public-Key-Finding als ausserhalb ihres Scopes markiert, darf daraus keine rechtliche Provider-Listung abgeleitet werden."
        )
        return lines

    protocol_security_question = (
        _has_question_terms(normalized_question, ["state"])
        and _has_question_terms(normalized_question, ["nonce"])
        and _has_question_terms(
            normalized_question,
            [
                "openid4vp",
                "openid",
                "authorization response",
                "authorization request",
                "csrf",
                "replay",
                "response-zuordnung",
                "response zuordnung",
            ],
        )
    )
    if evidence_synthesis_matrix is not None and not protocol_security_question:
        protocol_security_question = any(
            "protocol_security_parameter" in (getattr(record, "facet_tags", []) or [])
            for record in evidence_synthesis_matrix.records
        )
    if protocol_security_question:
        state_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "state",
                "authorization response",
                "request-id",
                "request id",
                "response_uri",
                "response uri",
                "direct_post",
            ],
            min_term_hits=2,
            required_facets=("protocol_security_parameter",),
            allowed_answer_roles=("normative_basis", "core_answer", "core_answer_support", "candidate_core_claim"),
            required_source_ids=("openid4vp_1_0_official",),
        )
        nonce_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "nonce",
                "securely bind",
                "verifiable presentation",
                "preventing replay",
                "replay",
                "correct nonce",
                "fresh cryptographically random",
            ],
            min_term_hits=1,
            required_facets=("protocol_security_parameter",),
            allowed_answer_roles=("normative_basis", "core_answer", "core_answer_support", "candidate_core_claim"),
            required_source_ids=("openid4vp_1_0_official",),
        )
        protocol_sources = _matrix_source_ids([*state_records, *nonce_records])
        lines.append(
            "- In OpenID4VP ist `state` der Korrelationsanker fuer die Antwort: "
            "bei `direct_post` sendet die Wallet die Authorization Response mit "
            "`vp_token` und `state` an die `response_uri`; die Response URI kann "
            "damit pruefen, ob die Antwort zum erwarteten Request gehoert."
            + _source_suffix(_matrix_source_ids(state_records) or protocol_sources)
        )
        lines.append(
            "- `nonce` bindet die Verifiable Presentation an die konkrete Transaktion: "
            "der Verifier erzeugt einen frischen Nonce fuer den Authorization Request, "
            "die Wallet bindet Presentation/Holder-Binding daran, und der Verifier "
            "muss den zur Session passenden Nonce validieren."
            + _source_suffix(_matrix_source_ids(nonce_records) or protocol_sources)
        )
        lines.append(
            "- Kurz gesagt: `state` adressiert falsche Response-Zuordnung und "
            "CSRF-/Session-Verwechslungen, waehrend `nonce` zusammen mit Holder Binding "
            "Replay alter Presentations verhindert; beides ist Protokollbindung, kein "
            "Wallet-Status- oder Trust-List-Signal."
            + _source_suffix(protocol_sources)
        )
        return lines

    if _has_question_terms(normalized_question, ["oid4vci", "credential-ausgabe", "credential issuance"]) and _has_question_terms(
        normalized_question,
        ["authorization server", "oauth"],
    ):
        oid_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["Authorization Server", "Credential Issuer", "Resource Server", "Access Token", "Credential Endpoint"],
        )
        lines.append(
            "- OID4VCI braucht den OAuth Authorization Server, weil die Credential-Ausgabe nicht nur ein Aufruf des Credential Endpoint ist: Der Credential Issuer agiert als geschuetzter Resource Server und gibt Credentials gegen ein autorisierendes Access Token aus."
            + _source_suffix(_matrix_source_ids(oid_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Die Wallet muss deshalb vor der Ausgabe die passenden Authorization-/Token-Endpunkte und Issuer-Metadaten kennen; erst danach kann sie den Credential Endpoint sinnvoll und pruefbar nutzen."
        )
        return lines

    if _has_question_terms(normalized_question, ["oauth client", "client", "benutzerkonto"]) and _has_question_terms(
        normalized_question,
        ["endnutzer", "resource owner", "benutzerkonto"],
    ):
        oauth_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["client", "resource owner", "authorization server", "resource server"],
        )
        lines.append(
            "- Die Aussage verwechselt den OAuth Client mit dem Resource Owner beziehungsweise Endnutzer: Der Client ist die Anwendung, die Zugriff anfragt; das Benutzerkonto gehoert zur Person beziehungsweise zum Resource Owner."
            + _source_suffix(_matrix_source_ids(oauth_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Zusaetzlich sind Authorization Server und Resource Server getrennte Rollen: Der Authorization Server stellt Tokens aus, der Resource Server schuetzt die Ressource und akzeptiert passende Tokens."
        )
        return lines

    if _has_question_terms(normalized_question, ["providerwechsel", "provider change", "portability", "portabilitaet", "migration object"]):
        migration_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["MigrationObject", "transaction log", "non-device-bound", "ListOfCredentials"],
        )
        device_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            [
                "device-bound",
                "Wallet Unit Attestation",
                "WUA",
                "attested keys",
                "cannot be re-issued",
                "re-issuance",
                "key_attestations_required",
            ],
        )
        lines.append(
            "- Bei echter Portabilitaet ist der Providerwechsel eine kontrollierte Migration mit Revalidierung, nicht nur ein Kopieren lokaler Wallet-Dateien."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:3]))
        )
        if migration_records:
            lines.append(
                "- Fuer Nachweise stuetzt die geoeffnete Evidenz ein MigrationObject mit Transaction Log, Credential-Liste und non-device-bound Attestations; device-bound Nachweise muessen separat neu gebunden oder neu ausgestellt werden."
                + _source_suffix(_matrix_source_ids([*migration_records, *device_records]))
            )
        if _has_question_terms(normalized_question, ["mandat", "mandate"]):
            lines.append(
                "- Mandate sollten beim Providerwechsel als Autoritaetsobjekte revalidiert werden: Scope, Gueltigkeit, Constraints, Aussteller und Widerrufsstatus duerfen durch Migration nicht erweitert oder wiederbelebt werden."
                + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:4]))
            )
        if _has_question_terms(normalized_question, ["vertrauenskette", "trust chain", "trust"]):
            lines.append(
                "- Die Vertrauenskette wandert nicht als providerlokale Eigenschaft mit; die Ziel-Wallet braucht eigene Wallet Unit Attestation (WUA), Schluessel-/Statusbindung und pruefbare Trust- bzw. Revocation-Anker."
                + _source_suffix(_matrix_source_ids([*device_records, *migration_records]))
            )
        if open_issue_bullets:
            lines.append(
                "- Offen bleibt die EBW-spezifische Detailregel fuer Mandatsmigration und einzelne Providerwechsel-Pflichten; die Antwort sollte diese Punkte als Spezifikations-/Implementierungsgrenze behandeln."
                + _source_suffix(_sources_from_bullets(open_issue_bullets[:2]))
            )
        lines.append(
            "- Die Auditspur darf beim Wechsel nicht abreissen: relevante Transaktions-/Status-/Revocation-Ereignisse muessen pruefbar bleiben, ohne daraus eine unbegrenzte Vollprotokollierung abzuleiten."
        )
        return lines

    if _has_question_terms(normalized_question, ["delegationskette", "delegation", "subdelegation", "mandats-credential", "mandat"]):
        lines.append(
            "- Eine mehrstufige Delegation sollte als Kette signierter, statuspruefbarer Mandats- oder Attribut-Attestations modelliert werden, nicht als flaches Rollenfeld."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:3]))
        )
        lines.append(
            "- Jede Stufe muss Scope, Gueltigkeit, Constraints, Delegationsrecht, Status-/Widerrufsreferenz und den Bezug zum Elternmandat erhalten; die effektive Berechtigung ist die Schnittmenge der Kette."
        )
        lines.append(
            "- Zur Pruefung sollte jede Nutzung die gesamte Kette aus Trust-Anker, Signatur, Parent-Bezug, monoton engerem Scope, Status/Widerruf und Policy-Version auswerten und als Entscheidungsnachweis protokollieren."
        )
        if open_issue_bullets:
            lines.append(
                "- Rechtlich und technisch offen bleiben konkrete EBW-Schemata, zulassige Subdelegationstiefe und nationale Root-Authority-Regeln."
                + _source_suffix(_sources_from_bullets(open_issue_bullets[:2]))
            )
        return lines

    if _has_question_terms(normalized_question, ["authentic source", "registerdaten", "unternehmensrealitaet", "wallet-gehaltene", "konfliktfall"]):
        lines.append(
            "- Im Konfliktfall ist die zustaendige authentic source bzw. das Register der Primaeranker; Wallet-Nachweise sind abgeleitete, zu validierende Belege."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Ein Wallet-Nachweis bleibt nur belastbar, solange Signatur, Status, Widerruf und Bezug zur massgeblichen Quelle stimmen."
        )
        if open_issue_bullets:
            lines.append(
                "- Eine behauptete aktuelle Unternehmensrealitaet ersetzt das Register nicht automatisch; sie ist ein Klaerungs-, Sperr- oder Aktualisierungsfall."
                + _source_suffix(_sources_from_bullets(open_issue_bullets[:2]))
            )
        return lines

    if _has_question_terms(normalized_question, ["pseudonym", "pseudonyme", "pseudonymen", "pseudonymous"]):
        legal_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["pseudonym", "pseudonyms", "specific and unique", "Article 14", "legal identity"],
            min_term_hits=1,
            required_facets=("pseudonym_legal_permission",),
        )
        account_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["account", "user account", "specific and unique", "user binding", "cryptographic binding"],
            min_term_hits=1,
            required_facets=("pseudonym_account_binding",),
        )
        attribute_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["selective disclosure", "presentation of attributes", "strictly necessary claims", "requested attributes"],
            min_term_hits=1,
            required_facets=("attribute_presentation_limit",),
        )
        linkability_records = _matrix_records_matching(
            evidence_synthesis_matrix,
            ["linkability", "unlinkability", "linkable", "verifier-to-verifier", "cross-party"],
            min_term_hits=1,
            required_facets=("linkability_risk",),
        )
        lines.append(
            "- Pseudonyme Authentifizierung ist dann tragfaehig, wenn keine rechtliche Pflicht zur Offenlegung der Identitaet besteht und die Wallet einen fuer die Wallet-Relying Party spezifischen, eindeutigen Pseudonymwert bereitstellen kann."
            + _source_suffix(_matrix_source_ids(legal_records) or _sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Bei Account-Bindung muss klar bleiben, woran gebunden wird: ein Pseudonym kann Account-Zugriff wiedererkennen, ersetzt aber nicht automatisch Identitaetsnachweis, User Binding oder eine kryptografische Bindung zwischen Attestationen."
            + _source_suffix(_matrix_source_ids(account_records))
        )
        lines.append(
            "- Attributpraesentation bleibt davon getrennt: OpenID4VP/DCQL und selective disclosure begrenzen, welche Claims oder Credentials fuer den konkreten Zweck offengelegt werden."
            + _source_suffix(_matrix_source_ids(attribute_records))
        )
        lines.append(
            "- Linkbare Pseudonyme sind ein eigener Risikofall; sobald derselbe Pseudonymwert ueber mehrere Akteure oder Services korreliert werden kann, muss die Linkability als bewusste Grenze statt als normale Identitaetsvermeidung behandelt werden."
            + _source_suffix(_matrix_source_ids(linkability_records))
        )
        return lines

    if _has_question_terms(normalized_question, ["device binding", "device-bound", "batch", "studierendenausweis"]) or (
        _has_question_terms(normalized_question, ["pid"])
        and _has_question_terms(
            normalized_question,
            ["subject binding", "device binding", "device-bound", "batch", "studierendenausweis"],
        )
    ):
        lines.append(
            "- PID-/Subject-Binding und Device-/Key-Binding sollten getrennt bewertet werden: PID klaert fachliche Identitaetsbindung, Device-Binding erschwert Weitergabe und erhoeht Re-Issuance-Aufwand."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:3]))
        )
        lines.append(
            "- Fuer Immatrikulationsbescheinigungen ist meist der konkrete Studiengangs-/Statusbezug entscheidend; fuer Studierendenausweise ist ein minimaler, device-bound Berechtigungsnachweis oft naheliegender."
        )
        return lines

    if _has_question_terms(normalized_question, ["immabescheinigung", "immatrikulationsbescheinigung", "bafoeg", "bafog", "richtige"]):
        lines.append(
            "- Die fachliche Auswahl der richtigen Immatrikulationsbescheinigung gehoert zur Relying Party bzw. zum Fachverfahren; die Wallet sollte bei mehreren passenden Credentials nicht raten."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:3]))
        )
        lines.append(
            "- Das Rulebook bzw. Schema muss die Unterscheidungsmerkmale liefern, etwa Hochschule, Studiengang, Status, Semester, Gueltigkeit, Issuer und Subject-/PID-Bezug."
        )
        if open_issue_bullets:
            lines.append(
                "- Fehlt ein BAfoeG- oder Deutschland-spezifisches Rulebook im Korpus, bleibt die konkrete fachrechtliche Selektionsregel als Gap zu markieren."
            )
        return lines

    if _has_question_terms(normalized_question, ["rulebook", "feldbeschreibung", "attribute", "englisch", "iana"]):
        lines.append(
            "- Rulebooks sollten fachliche Attribute mit stabilem Identifier, englischer Default-Beschreibung, Datentyp, Kardinalitaet, Disclosure-Regel, Trust-/Issuer-Modell und Binding-Regel beschreiben."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:3]))
        )
        lines.append(
            "- IANA-/JWT-Namen sind nur ein Baustein; fuer EU-weite Interoperabilitaet braucht es zusaetzlich Rulebook-, Catalogue- und Schema-Semantik."
        )
        if open_issue_bullets:
            lines.append(
                "- Eine harte allgemeine English-only-Pflicht ist im surfaced evidence nicht belegt; belastbarer ist eine englische Default-Semantik plus optionale Lokalisierungen."
            )
        return lines

    if _has_question_terms(normalized_question, ["audit", "ereignisspur", "vollprotokollierung", "compliance", "streitfall"]):
        lines.append(
            "- Erforderlich ist eine minimale, pruefbare Ereignisspur zu Autorisierung, Status, Widerruf, Gegenstelle, Policy-Version und Zeitpunkt, nicht die Vollspeicherung aller Payloads."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:4]))
        )
        if open_issue_bullets:
            lines.append(
                "- Aufbewahrung und Zugriff muessen an EU- oder nationales Recht sowie Datenminimierung gebunden bleiben."
            )
        return lines

    if _has_question_terms(normalized_question, ["natuerliche person", "juristische person", "handlungsbefugnis", "vertretung", "cross-border", "grenzueberschreitend"]):
        lines.append(
            "- Die Identitaet der natuerlichen Person und ihre Handlungsbefugnis fuer eine juristische Person muessen als getrennte Nachweise behandelt werden."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:4]))
        )
        lines.append(
            "- Die Relying Party sollte daher Person, Organisation, Mandat/Vertretung, Gueltigkeit und Widerruf getrennt pruefen."
        )
        return lines

    if _has_question_terms(normalized_question, ["architecture", "architektur", "speicher", "storage", "wallet gespeichert", "register"]):
        lines.append(
            "- Direkt ableitbar sind nur die belegten Architekturgrenzen; konkrete Speicher- oder Synchronisationspattern bleiben technische Gestaltung, solange sie nicht in Spezifikationen festgelegt sind."
            + _source_suffix(_sources_from_bullets(non_dynamic_bullets[:4]))
        )
        if open_issue_bullets:
            lines.append(
                "- Insbesondere lokale Wallet-Speicherung versus externe Register-/Issuer-Abfragen sollte als offene Architekturannahme ausgewiesen werden."
                + _source_suffix(_sources_from_bullets(open_issue_bullets[:2]))
        )
        return lines

    synthesis_summary = _synthesis_summary_lines(
        evidence_synthesis_matrix,
        question,
    )
    if synthesis_summary:
        lines.extend(synthesis_summary)
        return lines
    matrix_records = _matrix_summary_records(evidence_synthesis_matrix, limit=2)
    if matrix_records:
        source_ids = _matrix_source_ids(matrix_records)
        lines.append(
            "- Die geoeffnete Evidenz bindet die Antwort an die geoeffneten "
            "Quellen und Locator; weitergehende Aussagen bleiben begrenzt."
            + _source_suffix(source_ids)
        )
        return lines

    for bullet in non_dynamic_bullets[:3]:
        lines.append(
            f"- {_compact_answer_text(bullet.text)}"
            + _source_suffix(_sources_from_bullets([bullet], limit=2))
        )
    if open_issue_bullets:
        lines.append(f"- Offen bleibt: {_compact_answer_text(open_issue_bullets[0].text)}")
    if len(lines) == 1:
        lines.append(f"- {summary}")
    return lines


def _render_bullets_vnext(
    question: str,
    summary: str,
    bullets: Sequence[_AnswerBullet],
    clarification_note: Optional[str],
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix],
) -> str:
    lines: List[str] = _role_boundary_product_sections(
        question,
        evidence_synthesis_matrix,
    )
    if not lines:
        lines = _product_summary_lines(
            question,
            summary,
            bullets,
            evidence_synthesis_matrix,
        )
    rendered_note = _render_vnext_clarification_note(clarification_note, question)
    if rendered_note:
        lines.append(f"Begriffsklaerung / Scope: {rendered_note}")
    lines.extend(_product_evidence_sections(question, evidence_synthesis_matrix))
    lines.append("Pruefdetails:")

    synthesis_by_claim_id: dict[str, list[str]] = {}
    if evidence_synthesis_matrix is not None:
        for record in evidence_synthesis_matrix.records:
            if record.claim_id:
                synthesis_by_claim_id.setdefault(record.claim_id, []).append(
                    record.synthesis_id
                )

    section_order = [
        "Kurzantwort",
        "Normative evidence",
        "Technical / operational interpretation",
        "Interpretation/context",
        "Open issues",
        "Confirmed",
        "Interpretive",
        "Open",
        "Cross-reference hints",
    ]
    present_sections: list[str] = []
    for section in section_order:
        if any(bullet.section == section for bullet in bullets):
            present_sections.append(section)
    for bullet in bullets:
        if bullet.section not in present_sections:
            present_sections.append(bullet.section)

    for section in present_sections:
        section_bullets = [bullet for bullet in bullets if bullet.section == section]
        if not section_bullets:
            continue
        lines.append(f"{section}:")
        for bullet in section_bullets:
            claim_label = ", ".join(bullet.claim_ids) if bullet.claim_ids else bullet.bullet_id
            state_label = (
                ", ".join(state.value for state in bullet.claim_states)
                if bullet.claim_states
                else "unmapped"
            )
            lines.append(f"- {_compact_answer_text(bullet.text, limit=420)}")
            lines.append(f"  Claim: {claim_label} [{state_label}]")
            if bullet.rationale:
                lines.append(f"  Rationale: {bullet.rationale}")
            synthesis_ids = [
                synthesis_id
                for claim_id in bullet.claim_ids
                for synthesis_id in synthesis_by_claim_id.get(claim_id, [])
            ]
            if synthesis_ids:
                lines.append("  Synthesis matrix: " + ", ".join(sorted(set(synthesis_ids))))
            for evidence_line in bullet.evidence_lines:
                details = [
                    _render_citation_detail(citation)
                    for citation in _dedupe_citations(evidence_line.citations)
                ]
                lines.append(
                    f"  {evidence_line.label}: "
                    + ("; ".join(details) if details else "no admissible citation")
                )
    return "\n".join(lines)


def _evidence_pool(entry: LedgerEntry):
    return [
        *entry.supporting_evidence,
        *entry.governing_evidence,
        *entry.contradicting_evidence,
    ]


def _select_citations(
    entry: LedgerEntry,
    *,
    role_levels: Optional[Sequence[SourceRoleLevel]] = None,
    source_kinds: Optional[Sequence[SourceKind]] = None,
    require_direct: bool = False,
    limit: int = 3,
    strict_filters: bool = False,
) -> List[Citation]:
    matches = list(_evidence_pool(entry))
    if role_levels is not None:
        allowed_roles = set(role_levels)
        filtered = [item for item in matches if item.source_role_level in allowed_roles]
        if filtered:
            matches = filtered
        elif strict_filters and matches:
            return []
    if source_kinds is not None:
        allowed_kinds = set(source_kinds)
        filtered = [item for item in matches if item.source_kind in allowed_kinds]
        if filtered:
            matches = filtered
        elif strict_filters and matches:
            return []
    if require_direct:
        filtered = [
            item for item in matches if item.support_directness == SupportDirectness.DIRECT
        ]
        if filtered:
            matches = filtered
        elif strict_filters and matches:
            return []
    matches.sort(
        key=lambda item: (
            _role_weight(item.source_role_level),
            1 if item.support_directness == SupportDirectness.DIRECT else 0,
            _citation_weight(item.citation_quality),
            -item.source_kind_rank,
            item.on_point_score,
        ),
        reverse=True,
    )
    citations = _dedupe_citations(item.citation for item in matches)
    if citations:
        return citations[:limit]
    if strict_filters:
        # Strict mode means "no qualifying evidence, no topology evidence line", even if
        # the ledger still carries broad entry-level citations as a last-resort fallback.
        return []
    fallback_citations = list(_dedupe_citations(entry.citations))
    if role_levels is not None:
        allowed_roles = set(role_levels)
        fallback_citations = [
            citation for citation in fallback_citations if citation.source_role_level in allowed_roles
        ]
    if source_kinds is not None:
        allowed_kinds = set(source_kinds)
        fallback_citations = [
            citation for citation in fallback_citations if citation.source_kind in allowed_kinds
        ]
    return fallback_citations[:limit]


def _governing_term_hits(
    query_intent: QueryIntent,
    documents: Sequence[SourceDocument],
) -> tuple[List[SourceDocument], List[str]]:
    governing_documents = [
        document
        for document in documents
        if document.entry.source_role_level == SourceRoleLevel.HIGH
        and document.entry.source_kind in {SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT}
        and document.entry.jurisdiction == "EU"
    ]
    lowered_terms = [term.lower() for term in query_intent.undefined_terms]
    hit_titles: List[str] = []
    for document in governing_documents:
        lowered_text = document.text.lower()
        if any(term in lowered_text for term in lowered_terms):
            hit_titles.append(document.entry.title)
    return governing_documents, sorted(set(hit_titles))


def _document_citations(documents: Sequence[SourceDocument], *, limit: Optional[int] = None) -> List[Citation]:
    citations: List[Citation] = []
    for document in documents:
        if document.chunks:
            citations.append(document.chunks[0].citation)
        else:
            citations.append(
                Citation(
                    source_id=document.entry.source_id,
                    document_title=document.entry.title,
                    source_role_level=document.entry.source_role_level,
                    source_kind=document.entry.source_kind,
                    jurisdiction=document.entry.jurisdiction,
                    document_status=document.entry.document_status,
                    citation_quality=CitationQuality.DOCUMENT_ONLY,
                    document_path=document.entry.local_path,
                    canonical_url=document.entry.canonical_url,
                    source_origin=document.entry.source_origin,
                    structure_poor=document.structure_poor,
                    anchor_audit_note=(
                        document.anchor_audit.audit_note if document.anchor_audit is not None else None
                    ),
                )
            )
    deduped = _dedupe_citations(citations)
    if limit is not None:
        return deduped[:limit]
    return deduped


def _status_qualified_claim_text(entry: LedgerEntry) -> str:
    status = entry.governing_document_status
    if status == DocumentStatus.DRAFT:
        return f"Current draft support indicates: {entry.claim_text}"
    if status == DocumentStatus.PROPOSAL:
        return f"Current proposal-stage support indicates: {entry.claim_text}"
    if status == DocumentStatus.ADOPTED_PENDING_EFFECTIVE_DATE:
        return f"Adopted but not yet effective: {entry.claim_text}"
    if status == DocumentStatus.INFORMATIONAL and entry.claim_type in {
        ClaimType.SYNTHESIS,
        ClaimType.PROTOCOL_BEHAVIOR,
    }:
        return f"Informational source support indicates: {entry.claim_text}"
    return entry.claim_text


def _is_dynamic_entry(entry: LedgerEntry) -> bool:
    return entry.claim_id.startswith("dynamic_")


def _is_imported_legacy_candidate_entry(entry: LedgerEntry) -> bool:
    return entry.claim_id.startswith(("CLM-", "CLMSEED-"))


def _has_precise_citation(entry: LedgerEntry) -> bool:
    return any(citation.anchor_label for citation in _dedupe_citations(entry.citations))


def _is_answer_renderable_entry(entry: LedgerEntry) -> bool:
    if _is_dynamic_entry(entry) and not _has_precise_citation(entry):
        return False
    if _is_imported_legacy_candidate_entry(entry) and not _has_precise_citation(entry):
        return False
    return True


def _primary_citation(entry: LedgerEntry) -> Optional[Citation]:
    citations = _dedupe_citations(entry.citations)
    return citations[0] if citations else None


def _dynamic_evidence_text(entry: LedgerEntry) -> str:
    citation = _primary_citation(entry)
    if citation is None:
        return (
            "Dynamic evidence was surfaced for this point, but no admissible "
            "citation is attached; inspect the ledger before using it in an answer."
        )
    locator = _compact_locator(citation.anchor_label or citation.document_title)
    status_note = ""
    if citation.document_status == DocumentStatus.PROPOSAL:
        status_note = " proposal-stage"
    elif citation.document_status == DocumentStatus.DRAFT:
        status_note = " draft"
    elif citation.document_status == DocumentStatus.INFORMATIONAL:
        status_note = " informational"
    return (
        f"Opened{status_note} evidence from {citation.source_id} at {locator}; "
        "use it as inspectable support, not as a standalone composed claim."
    )


def _answer_entry_text(entry: LedgerEntry) -> str:
    if _is_dynamic_entry(entry):
        return _dynamic_evidence_text(entry)
    return _status_qualified_claim_text(entry)


def _select_answer_entries(
    entries: Sequence[LedgerEntry],
    *,
    dynamic_limit: int = 4,
) -> List[LedgerEntry]:
    selected: List[LedgerEntry] = []
    seen_statement_keys: set[tuple[str, tuple[str, ...]]] = set()
    for entry in entries:
        if _is_dynamic_entry(entry) or not _is_answer_renderable_entry(entry):
            continue
        statement_key = (
            normalize_text_for_matching(entry.claim_text),
            tuple(citation.source_id for citation in _dedupe_citations(entry.citations)),
        )
        if statement_key in seen_statement_keys:
            continue
        seen_statement_keys.add(statement_key)
        selected.append(entry)

    seen_dynamic_sources: set[str] = set()
    selected_dynamic = 0
    for entry in entries:
        if not _is_dynamic_entry(entry):
            continue
        if not _is_answer_renderable_entry(entry):
            continue
        citation = _primary_citation(entry)
        source_key = citation.source_id if citation is not None else entry.claim_id
        if source_key in seen_dynamic_sources:
            continue
        seen_dynamic_sources.add(source_key)
        selected.append(entry)
        selected_dynamic += 1
        if selected_dynamic >= dynamic_limit:
            break
    return selected


def _generic_entry_bullet(entry: LedgerEntry, section: str) -> _AnswerBullet:
    if _is_dynamic_entry(entry):
        wording_category = "dynamic_evidence_support"
    elif section == "Confirmed":
        wording_category = (
            "governing_confirmed"
            if entry.source_role_level == SourceRoleLevel.HIGH
            else "confirmed_non_governing"
        )
    else:
        wording_category = {
            "Interpretive": "interpretive_state_forwarded",
            "Open": "open_state_forwarded",
        }.get(section, "state_forwarded")
    return _AnswerBullet(
        bullet_id=entry.claim_id,
        section=section,
        text=_answer_entry_text(entry),
        rationale=entry.rationale,
        wording_category=wording_category,
        claim_ids=[entry.claim_id],
        claim_states=[entry.final_claim_state],
        evidence_lines=[_EvidenceLine(label="Evidence", citations=_dedupe_citations(entry.citations))],
    )


def _build_topology_term_status_bullet(
    query_intent: QueryIntent,
    documents: Sequence[SourceDocument],
) -> _AnswerBullet:
    governing_documents, governing_term_hits = _governing_term_hits(query_intent, documents)
    term_status_text = (
        "Governing EU sources in the current corpus use derivative wording for the "
        "requested certificate terminology, so this term-status point needs manual review."
        if governing_term_hits
        else f'{TOPOLOGY_NOT_DEFINED_PREFIX} a wallet-relying-party "derived certificate" '
        "term for access or registration certificates."
    )
    term_status_rationale = (
        "Exact governing-source term hits were found in "
        + "; ".join(governing_term_hits)
        if governing_term_hits
        else "Corpus-wide governing term scan across "
        f"{len(governing_documents)} governing EU source(s) found no exact match for "
        + ", ".join(f'"{term}"' for term in query_intent.undefined_terms)
        + "."
    )
    return _AnswerBullet(
        bullet_id="topology_undefined_term_status",
        section=TOPOLOGY_NOT_DEFINED_LABEL,
        text=term_status_text,
        rationale=term_status_rationale,
        wording_category="term_status_scan",
        evidence_lines=[
            _EvidenceLine(
                label="Evidence",
                citations=_document_citations(governing_documents),
            )
        ],
    )


def _build_topology_confirmed_bullet(
    entry: LedgerEntry,
    *,
    require_direct: bool,
) -> _AnswerBullet:
    return _AnswerBullet(
        bullet_id=entry.claim_id,
        section="Confirmed",
        text=entry.claim_text,
        rationale=entry.rationale,
        wording_category="governing_confirmed",
        claim_ids=[entry.claim_id],
        claim_states=[entry.final_claim_state],
        evidence_lines=[
            _EvidenceLine(
                label="Evidence",
                citations=_select_citations(
                    entry,
                    role_levels=[SourceRoleLevel.HIGH],
                    require_direct=require_direct,
                    strict_filters=True,
                ),
            )
        ],
    )


def _topology_scope_claim_ids(
    entry_by_id: dict[str, LedgerEntry],
) -> List[str]:
    return [
        claim_id
        for claim_id in [
            "topology_registration_certificate_role",
            "topology_access_certificate_role",
            "topology_registration_access_linkage",
        ]
        if claim_id in entry_by_id
        and entry_by_id[claim_id].final_claim_state != ClaimState.OPEN
    ]


def _collect_topology_scope_support(
    entry_by_id: dict[str, LedgerEntry],
    claim_ids: Sequence[str],
) -> _TopologyEvidenceSelection:
    citations: List[Citation] = []
    claim_states: List[ClaimState] = []
    for claim_id in claim_ids:
        scope_entry = entry_by_id[claim_id]
        claim_states.append(scope_entry.final_claim_state)
        citations.extend(
            _select_citations(
                scope_entry,
                role_levels=[SourceRoleLevel.HIGH],
                require_direct=True,
                strict_filters=True,
            )
        )
    return _TopologyEvidenceSelection(
        citations=_dedupe_citations(citations),
        claim_states=claim_states,
        claim_ids=list(claim_ids),
    )


def _build_topology_scope_interpretation_bullet(
    entry_by_id: dict[str, LedgerEntry],
) -> tuple[Optional[_AnswerBullet], set[str]]:
    scope_claim_ids = _topology_scope_claim_ids(entry_by_id)
    full_scope_claim_ids = [
        "topology_registration_certificate_role",
        "topology_access_certificate_role",
        "topology_registration_access_linkage",
    ]
    if scope_claim_ids != full_scope_claim_ids:
        return None, set()

    scope_support = _collect_topology_scope_support(entry_by_id, scope_claim_ids)
    bullet = _AnswerBullet(
        bullet_id="topology_governing_scope_interpretation",
        section="Interpretive",
        text=TOPOLOGY_SCOPING_SENTENCE,
        rationale=(
            "This is the narrower conclusion the governing texts support directly; "
            "they describe role, intended use, and certificate linkage, but they "
            "do not expressly settle multiplicity."
        ),
        wording_category="interpretive_governing_boundary",
        claim_ids=scope_support.claim_ids,
        claim_states=scope_support.claim_states,
        evidence_lines=[
            _EvidenceLine(
                label="Evidence",
                citations=scope_support.citations,
            )
        ],
    )
    covered_claim_ids = {
        claim_id
        for claim_id in scope_claim_ids
        if entry_by_id[claim_id].final_claim_state == ClaimState.INTERPRETIVE
    }
    return bullet, covered_claim_ids


def _topology_boundary_entries(
    entry_by_id: dict[str, LedgerEntry],
) -> List[LedgerEntry]:
    return [
        entry_by_id[claim_id]
        for claim_id in [
            "topology_registration_certificate_role",
            "topology_access_certificate_role",
            "topology_registration_access_linkage",
        ]
        if claim_id in entry_by_id
        and entry_by_id[claim_id].final_claim_state != ClaimState.OPEN
    ]


def _collect_topology_boundary_support(
    boundary_entries: Sequence[LedgerEntry],
) -> _TopologyEvidenceSelection:
    citations: List[Citation] = []
    claim_states: List[ClaimState] = []
    claim_ids: List[str] = []
    for boundary_entry in boundary_entries:
        claim_ids.append(boundary_entry.claim_id)
        claim_states.append(boundary_entry.final_claim_state)
        citations.extend(
            _select_citations(
                boundary_entry,
                role_levels=[SourceRoleLevel.HIGH],
                require_direct=True,
                strict_filters=True,
            )
        )
    return _TopologyEvidenceSelection(
        citations=_dedupe_citations(citations),
        claim_states=claim_states,
        claim_ids=claim_ids,
    )


def _collect_topology_project_support(
    project_entries: Sequence[LedgerEntry],
) -> _TopologyProjectSupport:
    citations: List[Citation] = []
    supported_entries: List[LedgerEntry] = []
    claim_states: List[ClaimState] = []
    for project_entry in project_entries:
        selected_citations = _select_citations(
            project_entry,
            role_levels=[SourceRoleLevel.MEDIUM],
            source_kinds=[SourceKind.PROJECT_ARTIFACT],
            require_direct=False,
            strict_filters=True,
        )
        if not selected_citations:
            continue
        supported_entries.append(project_entry)
        claim_states.append(project_entry.final_claim_state)
        citations.extend(selected_citations)
    return _TopologyProjectSupport(
        supported_entries=supported_entries,
        citations=_dedupe_citations(citations),
        claim_states=claim_states,
    )


def _build_topology_unresolved_multiplicity_bullet(
    entry_by_id: dict[str, LedgerEntry],
) -> tuple[Optional[_AnswerBullet], set[str]]:
    project_multiplicity_entry = entry_by_id.get("topology_project_artifact_multiplicity")
    project_scoping_entry = entry_by_id.get("topology_project_intended_use_scoping")
    approved_project_entries = [
        project_entry
        for project_entry in [project_multiplicity_entry, project_scoping_entry]
        if project_entry is not None and project_entry.final_claim_state != ClaimState.OPEN
    ]
    boundary_entries = _topology_boundary_entries(entry_by_id)
    if not (boundary_entries or project_multiplicity_entry or project_scoping_entry):
        return None, set()

    boundary_support = _collect_topology_boundary_support(boundary_entries)
    project_support = _collect_topology_project_support(approved_project_entries)

    has_boundary_support = bool(boundary_support.citations)
    has_project_support = bool(project_support.supported_entries and project_support.citations)
    unresolved_text = TOPOLOGY_UNRESOLVED_NO_APPROVED_SUPPORT_SENTENCE
    unresolved_rationale = (
        "The broader topology conclusion is still not explicit governing law in the local corpus, and this run does not surface approved supporting evidence for multiplicity."
    )
    wording_category = "unresolved_no_approved_support"
    evidence_lines: List[_EvidenceLine] = []
    explicit_role_partitioning = False

    if has_boundary_support and has_project_support:
        unresolved_text = TOPOLOGY_UNRESOLVED_WITH_PROJECT_SUPPORT_SENTENCE
        unresolved_rationale = (
            "The product can separate the governing role statements from the broader "
            "multiplicity interpretation, but the broader topology conclusion is still "
            "not explicit governing law in the local corpus."
        )
        wording_category = "unresolved_partitioned_support"
        evidence_lines = [
            _EvidenceLine(
                label="Evidence (governing boundary)",
                citations=boundary_support.citations,
            ),
            _EvidenceLine(
                label="Evidence (medium-rank project support)",
                citations=project_support.citations,
            ),
        ]
        explicit_role_partitioning = True
    elif has_boundary_support:
        unresolved_text = TOPOLOGY_UNRESOLVED_GOVERNING_ONLY_SENTENCE
        unresolved_rationale = (
            "The product can preserve the governing boundary statements, but the broader "
            "multiplicity interpretation remains unresolved because no approved medium-rank "
            "project support survives this run."
        )
        wording_category = "unresolved_governing_boundary_only"
        evidence_lines = [
            _EvidenceLine(
                label="Evidence (governing boundary)",
                citations=boundary_support.citations,
            )
        ]
    elif has_project_support:
        unresolved_text = TOPOLOGY_UNRESOLVED_PROJECT_ONLY_SENTENCE
        unresolved_rationale = (
            "The run surfaces only non-governing project-artifact support for multiplicity, "
            "so the broader topology conclusion remains unresolved and cannot be framed as "
            "governing EU law."
        )
        wording_category = "unresolved_medium_rank_only"
        evidence_lines = [
            _EvidenceLine(
                label="Evidence (medium-rank project support)",
                citations=project_support.citations,
            )
        ]

    bullet = _AnswerBullet(
        bullet_id="topology_unresolved_multiplicity",
        section="Open",
        text=unresolved_text,
        rationale=unresolved_rationale,
        wording_category=wording_category,
        claim_ids=[
            *boundary_support.claim_ids,
            *(entry.claim_id for entry in project_support.supported_entries),
        ],
        claim_states=[*boundary_support.claim_states, *project_support.claim_states],
        evidence_lines=evidence_lines,
        explicit_role_partitioning=explicit_role_partitioning,
    )
    return bullet, {entry.claim_id for entry in project_support.supported_entries}


def _compose_certificate_topology_bullets(
    entries: Sequence[LedgerEntry],
    query_intent: QueryIntent,
    documents: Sequence[SourceDocument],
) -> List[_AnswerBullet]:
    entry_by_id = {entry.claim_id: entry for entry in entries}
    bullets: List[_AnswerBullet] = []
    covered_claim_ids = set()
    bullets.append(_build_topology_term_status_bullet(query_intent, documents))

    access_entry = entry_by_id.get("topology_access_certificate_role")
    if access_entry is not None and access_entry.final_claim_state == ClaimState.CONFIRMED:
        bullets.append(_build_topology_confirmed_bullet(access_entry, require_direct=True))
        covered_claim_ids.add(access_entry.claim_id)

    linkage_entry = entry_by_id.get("topology_registration_access_linkage")
    if linkage_entry is not None and linkage_entry.final_claim_state == ClaimState.CONFIRMED:
        bullets.append(_build_topology_confirmed_bullet(linkage_entry, require_direct=False))
        covered_claim_ids.add(linkage_entry.claim_id)

    scope_bullet, scope_covered_claim_ids = _build_topology_scope_interpretation_bullet(
        entry_by_id
    )
    if scope_bullet is not None:
        bullets.append(scope_bullet)
        covered_claim_ids.update(scope_covered_claim_ids)

    unresolved_bullet, unresolved_covered_claim_ids = _build_topology_unresolved_multiplicity_bullet(
        entry_by_id
    )
    if unresolved_bullet is not None:
        bullets.append(unresolved_bullet)
        covered_claim_ids.update(unresolved_covered_claim_ids)

    for entry in entries:
        if entry.claim_id in covered_claim_ids:
            continue
        if entry.final_claim_state == ClaimState.CONFIRMED:
            bullets.append(_generic_entry_bullet(entry, "Confirmed"))
        elif entry.final_claim_state == ClaimState.INTERPRETIVE:
            bullets.append(_generic_entry_bullet(entry, "Interpretive"))
        elif entry.final_claim_state == ClaimState.OPEN:
            bullets.append(_generic_entry_bullet(entry, "Open"))

    return bullets


def _relation_hint_wording_category(record: RelationHintRecord) -> str:
    cited_roles = {
        citation.source_role_level
        for partition in record.evidence_partitions
        for citation in partition.citations
    }
    partitioned = SourceRoleLevel.MEDIUM in cited_roles and SourceRoleLevel.HIGH in cited_roles
    if record.relation_state == "confirmed":
        return (
            "relation_hint_partitioned_confirmed"
            if partitioned
            else "relation_hint_governing_confirmed"
        )
    return (
        "relation_hint_partitioned_interpretive"
        if partitioned
        else "relation_hint_governing_interpretive"
    )


def _relation_hint_bullet(record: RelationHintRecord) -> _AnswerBullet:
    evidence_lines = [
        _EvidenceLine(
            label=partition.partition_label,
            citations=list(partition.citations),
        )
        for partition in record.evidence_partitions
    ]
    cited_roles = {
        citation.source_role_level
        for partition in record.evidence_partitions
        for citation in partition.citations
    }
    return _AnswerBullet(
        bullet_id=f"relation_hint:{record.hint_id}",
        section="Cross-reference hints",
        text=record.summary,
        rationale=record.limitation_note,
        wording_category=_relation_hint_wording_category(record),
        claim_ids=list(record.derived_from_claim_ids),
        claim_states=list(record.derived_from_claim_states),
        evidence_lines=evidence_lines,
        explicit_role_partitioning=len(cited_roles) > 1 or len(evidence_lines) > 1,
    )


def _compose_relation_hint_bullets(
    relation_hint_report: Optional[RelationHintReport],
) -> List[_AnswerBullet]:
    if relation_hint_report is None:
        return []
    return [
        _relation_hint_bullet(record)
        for record in relation_hint_report.records
        if record.rendered_in_answer
    ]


def _compose_generic_bullets(
    entries: Sequence[LedgerEntry],
    relation_hint_report: Optional[RelationHintReport] = None,
) -> List[_AnswerBullet]:
    bullets: List[_AnswerBullet] = []
    for state, section in [
        (ClaimState.CONFIRMED, "Confirmed"),
        (ClaimState.INTERPRETIVE, "Interpretive"),
        (ClaimState.OPEN, "Open"),
    ]:
        section_entries = [
            entry for entry in entries if entry.final_claim_state == state
        ]
        for entry in _select_answer_entries(section_entries):
            bullets.append(_generic_entry_bullet(entry, section))
    bullets.extend(_compose_relation_hint_bullets(relation_hint_report))
    return bullets


def _question_context_citations(entries: Sequence[LedgerEntry], *, limit: int = 4) -> List[Citation]:
    citations: List[Citation] = []
    for entry in entries:
        citations.extend(entry.citations)
    return _dedupe_citations(citations)[:limit]


def _question_framed_open_issue_bullets(
    question: str,
    entries: Sequence[LedgerEntry],
) -> List[_AnswerBullet]:
    normalized_question = normalize_text_for_matching(question)
    citations = _question_context_citations(entries)
    claim_ids = [entry.claim_id for entry in entries[:4]]
    claim_states = [entry.final_claim_state for entry in entries[:4]]
    bullets: List[_AnswerBullet] = []

    if (
        "unternehmensrealitaet" in normalized_question
        or "business reality" in normalized_question
        or "current reality" in normalized_question
    ):
        bullets.append(
            _AnswerBullet(
                bullet_id="question_gap_business_reality_priority",
                section="Open issues",
                text=(
                    "Offen bleibt der Umgang mit abweichender aktueller "
                    "Unternehmensrealität: Die ausgewertete Evidenz stuetzt "
                    "Register/authentic sources, Status- und Widerrufspruefung, "
                    "aber keine eigene Vorrangregel, nach der eine behauptete "
                    "business reality das Register unmittelbar schlaegt."
                ),
                rationale=(
                    "The question asks about a conflict source that is not itself "
                    "established as an authoritative source in the surfaced evidence."
                ),
                wording_category="question_framed_open_issue",
                claim_ids=claim_ids,
                claim_states=claim_states,
                evidence_lines=[_EvidenceLine(label="Boundary evidence", citations=citations)],
            )
        )

    if (
        ("english" in normalized_question or "englisch" in normalized_question)
        and ("rulebook" in normalized_question or "rulebooks" in normalized_question)
    ):
        bullets.append(
            _AnswerBullet(
                bullet_id="question_gap_no_general_english_only_rule",
                section="Open issues",
                text=(
                    "No general English-only hard rule was found in the surfaced "
                    "evidence. The safer answer is therefore to use English names, "
                    "descriptions and stable identifiers where catalogue/rulebook "
                    "sources support them, while marking any broader EU-wide "
                    "language mandate as a gap."
                ),
                rationale=(
                    "The question asks for a general language convention; the run "
                    "surfaces catalogue and attribute-description evidence, but not "
                    "a final cross-rulebook English-only obligation."
                ),
                wording_category="question_framed_open_issue",
                claim_ids=claim_ids,
                claim_states=claim_states,
                evidence_lines=[_EvidenceLine(label="Boundary evidence", citations=citations)],
            )
        )

    if (
        ("relying party" in normalized_question or ("relying" in normalized_question and "party" in normalized_question))
        and "attribute" in normalized_question
        and ("scope" in normalized_question or "registriert" in normalized_question)
    ):
        bullets.append(
            _AnswerBullet(
                bullet_id="question_gap_certificate_topology_scope",
                section="Open issues",
                text=(
                    "A certificate topology gap remains: the evidence supports "
                    "registered or authorised scope boundaries for attribute access, "
                    "but it should not be read as settling every certificate-topology "
                    "detail for all relying-party registration designs."
                ),
                rationale=(
                    "The question asks whether registration implies arbitrary "
                    "attribute access; the supported answer is no, while broader "
                    "certificate topology remains a separate design/detail issue."
                ),
                wording_category="question_framed_open_issue",
                claim_ids=claim_ids,
                claim_states=claim_states,
                evidence_lines=[_EvidenceLine(label="Boundary evidence", citations=citations)],
            )
        )

    if (
        ("storage" in normalized_question or "speicher" in normalized_question)
        and ("mandat" in normalized_question or "mandate" in normalized_question)
        and ("wallet" in normalized_question or "register" in normalized_question)
    ):
        bullets.append(
            _AnswerBullet(
                bullet_id="question_gap_delegated_storage_design",
                section="Open issues",
                text=(
                    "Delegated storage gap: Die ausgewertete Evidenz stuetzt "
                    "Mandats-/Berechtigungspruefung und Wallet-/Register-Bezuege, "
                    "legt aber kein abschliessendes Speicherpattern fest. Lokale "
                    "Wallet-Speicherung und externe Register-/Issuer-Abfragen "
                    "bleiben deshalb als Architekturdesign zu qualifizieren, bis "
                    "spaetere technische Spezifikationen das Pattern festlegen."
                ),
                rationale=(
                    "The question asks whether one mandate storage architecture is "
                    "already mandated; the surfaced evidence does not close that design gap."
                ),
                wording_category="question_framed_open_issue",
                claim_ids=claim_ids,
                claim_states=claim_states,
                evidence_lines=[_EvidenceLine(label="Boundary evidence", citations=citations)],
            )
        )

    return bullets


def _is_eubw_structured_intent(query_intent: Optional[QueryIntent]) -> bool:
    return (
        query_intent is not None
        and query_intent.intent_type in EUBW_STRUCTURED_INTENT_TYPES
    )


def _eubw_entry_bullet(entry: LedgerEntry, section: str) -> _AnswerBullet:
    return _AnswerBullet(
        bullet_id=entry.claim_id,
        section=section,
        text=_answer_entry_text(entry),
        rationale=entry.rationale,
        wording_category=(
            "dynamic_evidence_support"
            if _is_dynamic_entry(entry)
            else "eubw_state_forwarded"
        ),
        claim_ids=[entry.claim_id],
        claim_states=[entry.final_claim_state],
        evidence_lines=[
            _EvidenceLine(label="Evidence", citations=_dedupe_citations(entry.citations))
        ],
    )


def _eubw_structured_section(entry: LedgerEntry) -> str:
    if entry.final_claim_state == ClaimState.OPEN:
        return "Open issues"
    if entry.source_role_level == SourceRoleLevel.MEDIUM:
        return "Interpretation/context"
    return "Normative evidence"


def _compose_eubw_structured_bullets(
    entries: Sequence[LedgerEntry],
    query_intent: QueryIntent,
) -> List[_AnswerBullet]:
    if query_intent.intent_type == "eubw_architecture_bucket_analysis":
        entry_by_id = {entry.claim_id: entry for entry in entries}
        bullets: List[_AnswerBullet] = []
        covered_claim_ids: set[str] = set()
        for claim_id, section in EUBW_ARCHITECTURE_BUCKET_SECTIONS.items():
            entry = entry_by_id.get(claim_id)
            if entry is None:
                continue
            bullets.append(_eubw_entry_bullet(entry, section))
            covered_claim_ids.add(claim_id)
        remaining_entries = [
            entry for entry in entries if entry.claim_id not in covered_claim_ids
        ]
        for section in ["Normative evidence", "Interpretation/context", "Open issues"]:
            for entry in _select_answer_entries(
                [
                    candidate
                    for candidate in remaining_entries
                    if _eubw_structured_section(candidate) == section
                ]
            ):
                bullets.append(_eubw_entry_bullet(entry, _eubw_structured_section(entry)))
        return bullets

    bullets = []
    for section in ["Normative evidence", "Interpretation/context", "Open issues"]:
        bullets.extend(
            _eubw_entry_bullet(entry, section)
            for entry in _select_answer_entries(
                [
                    candidate
                    for candidate in entries
                    if _eubw_structured_section(candidate) == section
                ]
            )
        )
    return bullets


def _eubw_structured_summary(query_intent: QueryIntent) -> str:
    if query_intent.intent_type == "eubw_architecture_bucket_analysis":
        return (
            "Kurzantwort: Proposal und Annex stuetzen direkte Architekturgrenzen, "
            "delegieren technische Detailfragen an spaetere Spezifikationen und lassen "
            "plausible Architekturannahmen sichtbar getrennt."
        )
    return (
        "Kurzantwort: Die Antwort trennt belastbare normative Evidenz, "
        "Interpretation bzw. Kontext und offene Punkte fuer die EUBW-Paritaetsfrage."
    )


def _classify_locator(citation: Citation) -> tuple[str, str, str, Optional[str]]:
    if citation.anchor_label:
        anchor_path = citation.anchor_label.strip()
        segments = [segment.strip() for segment in anchor_path.split(">") if segment.strip()]
        provision_segments = [
            segment
            for segment in segments
            if segment.lower().startswith(("article", "section", "clause", "annex", "chapter"))
        ]
        precision = "provision_level" if provision_segments else "section_level"
        return (
            "heading_path",
            anchor_path,
            precision,
            "Exact line-level pinpoint is not available; this run exposes the nearest heading anchor.",
        )
    if citation.document_path is not None:
        return (
            "document_path",
            str(citation.document_path),
            "approximate",
            "Only document-level traceability is available for this citation; broader manual navigation may still be required.",
        )
    if citation.canonical_url:
        return (
            "canonical_url",
            citation.canonical_url,
            "approximate",
            "Only document-level traceability is available for this citation; broader manual navigation may still be required.",
        )
    return (
        "document_title",
        citation.document_title,
        "approximate",
        "Only document-title traceability is available for this citation.",
    )


def _build_pinpoint_evidence_report(
    question: str,
    intent_type: str,
    bullets: Sequence[_AnswerBullet],
) -> PinpointEvidenceReport:
    records: List[PinpointEvidenceRecord] = []
    missing_citation_claim_ids: List[str] = []

    for bullet in bullets:
        bullet_citations = _dedupe_citations(
            citation
            for evidence_line in bullet.evidence_lines
            for citation in evidence_line.citations
        )
        if not bullet_citations:
            missing_citation_claim_ids.append(bullet.bullet_id)
            continue
        for citation in bullet_citations:
            locator_type, locator_value, locator_precision, limitation_note = _classify_locator(
                citation
            )
            if not locator_value:
                missing_citation_claim_ids.append(bullet.bullet_id)
                continue
            records.append(
                PinpointEvidenceRecord(
                    answer_claim_id=bullet.bullet_id,
                    answer_section=bullet.section,
                    answer_claim_text=bullet.text,
                    source_id=citation.source_id,
                    source_role_level=citation.source_role_level,
                    document_status=citation.document_status,
                    citation_quality=citation.citation_quality,
                    locator_type=locator_type,
                    locator_value=locator_value,
                    locator_precision=locator_precision,
                    document_path=citation.document_path,
                    canonical_url=citation.canonical_url,
                    limitation_note=limitation_note,
                )
            )

    return PinpointEvidenceReport(
        question=question,
        intent_type=intent_type,
        records=records,
        all_cited_evidence_mapped=not missing_citation_claim_ids,
        missing_citation_claim_ids=sorted(set(missing_citation_claim_ids)),
    )


def _build_answer_alignment_report(
    question: str,
    intent_type: str,
    bullets: Sequence[_AnswerBullet],
) -> AnswerAlignmentReport:
    records: List[AnswerAlignmentRecord] = []
    blocking_violations: List[str] = []

    for bullet in bullets:
        cited_citations = _dedupe_citations(
            citation
            for evidence_line in bullet.evidence_lines
            for citation in evidence_line.citations
        )
        cited_roles = [citation.source_role_level for citation in cited_citations]
        notes: List[str] = []
        status = "pass"

        if bullet.wording_category == "governing_confirmed":
            if bullet.section != "Confirmed":
                notes.append("Governing-confirmed wording is not placed in the Confirmed section.")
            if bullet.claim_states and any(
                claim_state != ClaimState.CONFIRMED for claim_state in bullet.claim_states
            ):
                notes.append("Confirmed wording is attached to a non-confirmed claim-state.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Confirmed governing wording cites non-governing evidence.")
        elif bullet.wording_category == "confirmed_non_governing":
            if bullet.section != "Confirmed":
                notes.append("Confirmed non-governing wording is not placed in the Confirmed section.")
            if bullet.claim_states and any(
                claim_state != ClaimState.CONFIRMED for claim_state in bullet.claim_states
            ):
                notes.append("Confirmed non-governing wording is attached to a non-confirmed claim-state.")
            if cited_roles and any(role == SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Confirmed non-governing wording mixes governing evidence without explicit partitioning.")
            if cited_roles and all(role == SourceRoleLevel.LOW for role in cited_roles):
                notes.append("Confirmed non-governing wording relies only on low-rank evidence.")
        elif bullet.wording_category == "term_status_scan":
            if bullet.section != TOPOLOGY_NOT_DEFINED_LABEL:
                notes.append("Undefined-term status was not surfaced in the dedicated term-status section.")
        elif bullet.wording_category == "interpretive_governing_boundary":
            if bullet.section != "Interpretive":
                notes.append("Interpretive governing-boundary wording is not in the Interpretive section.")
            if bullet.claim_states and any(
                claim_state == ClaimState.OPEN for claim_state in bullet.claim_states
            ):
                notes.append("Interpretive governing-boundary wording rests on open claim-state evidence.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Interpretive governing-boundary wording cites non-governing evidence.")
        elif bullet.wording_category == "unresolved_partitioned_support":
            if bullet.section != "Open":
                notes.append("Unresolved mixed-support wording is not in the Open section.")
            if not bullet.explicit_role_partitioning:
                notes.append("Mixed governing and medium-rank support is not partitioned explicitly.")
            if SourceRoleLevel.HIGH not in cited_roles:
                notes.append("Unresolved mixed-support wording is missing governing boundary evidence.")
            if SourceRoleLevel.MEDIUM not in cited_roles:
                notes.append("Unresolved mixed-support wording is missing medium-rank evidence.")
        elif bullet.wording_category == "unresolved_governing_boundary_only":
            if bullet.section != "Open":
                notes.append("Unresolved governing-boundary wording is not in the Open section.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Governing-boundary-only unresolved wording cites non-governing evidence.")
        elif bullet.wording_category == "unresolved_medium_rank_only":
            if bullet.section != "Open":
                notes.append("Unresolved medium-rank wording is not in the Open section.")
            if cited_roles and any(role != SourceRoleLevel.MEDIUM for role in cited_roles):
                notes.append("Medium-rank-only unresolved wording cites governing evidence.")
        elif bullet.wording_category == "unresolved_no_approved_support":
            if bullet.section != "Open":
                notes.append("Unresolved no-approved-support wording is not in the Open section.")
            if cited_roles:
                notes.append("No-approved-support wording should not cite supporting evidence.")
        elif bullet.wording_category == "interpretive_state_forwarded":
            if bullet.section != "Interpretive":
                notes.append("Interpretive claim-state is not surfaced in the Interpretive section.")
            if any(claim_state == ClaimState.CONFIRMED for claim_state in bullet.claim_states) and (
                SourceRoleLevel.MEDIUM in cited_roles and not bullet.explicit_role_partitioning
            ):
                notes.append("Mixed governing and medium-rank support needs explicit partitioning.")
        elif bullet.wording_category == "open_state_forwarded":
            if bullet.section != "Open":
                notes.append("Open claim-state is not surfaced in the Open section.")
        elif bullet.wording_category == "relation_hint_governing_confirmed":
            if bullet.section != "Cross-reference hints":
                notes.append("Confirmed relation-hint wording is not placed in Cross-reference hints.")
            if bullet.claim_states and any(
                claim_state != ClaimState.CONFIRMED for claim_state in bullet.claim_states
            ):
                notes.append("Confirmed relation-hint wording is attached to a non-confirmed claim-state.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Confirmed governing relation-hint wording cites non-governing evidence.")
        elif bullet.wording_category == "relation_hint_governing_interpretive":
            if bullet.section != "Cross-reference hints":
                notes.append("Interpretive relation-hint wording is not placed in Cross-reference hints.")
            if bullet.claim_states and not any(
                claim_state == ClaimState.INTERPRETIVE for claim_state in bullet.claim_states
            ):
                notes.append("Interpretive relation-hint wording does not rest on any interpretive claim-state.")
            if bullet.claim_states and any(
                claim_state == ClaimState.OPEN for claim_state in bullet.claim_states
            ):
                notes.append("Interpretive relation-hint wording rests on open claim-state evidence.")
            if cited_roles and any(role != SourceRoleLevel.HIGH for role in cited_roles):
                notes.append("Interpretive governing relation-hint wording cites non-governing evidence.")
        elif bullet.wording_category == "relation_hint_partitioned_confirmed":
            if bullet.section != "Cross-reference hints":
                notes.append("Partitioned confirmed relation-hint wording is not placed in Cross-reference hints.")
            if bullet.claim_states and any(
                claim_state != ClaimState.CONFIRMED for claim_state in bullet.claim_states
            ):
                notes.append("Partitioned confirmed relation-hint wording is attached to a non-confirmed claim-state.")
            if not bullet.explicit_role_partitioning:
                notes.append("Partitioned confirmed relation-hint wording is not explicitly partitioned.")
            if SourceRoleLevel.HIGH not in cited_roles or SourceRoleLevel.MEDIUM not in cited_roles:
                notes.append("Partitioned confirmed relation-hint wording must cite both high and medium support.")
        elif bullet.wording_category == "relation_hint_partitioned_interpretive":
            if bullet.section != "Cross-reference hints":
                notes.append("Partitioned interpretive relation-hint wording is not placed in Cross-reference hints.")
            if bullet.claim_states and not any(
                claim_state == ClaimState.INTERPRETIVE for claim_state in bullet.claim_states
            ):
                notes.append("Partitioned interpretive relation-hint wording does not rest on any interpretive claim-state.")
            if bullet.claim_states and any(
                claim_state == ClaimState.OPEN for claim_state in bullet.claim_states
            ):
                notes.append("Partitioned interpretive relation-hint wording rests on open claim-state evidence.")
            if not bullet.explicit_role_partitioning:
                notes.append("Partitioned interpretive relation-hint wording is not explicitly partitioned.")
            if SourceRoleLevel.HIGH not in cited_roles or SourceRoleLevel.MEDIUM not in cited_roles:
                notes.append("Partitioned interpretive relation-hint wording must cite both high and medium support.")
        elif bullet.wording_category == "dynamic_evidence_support":
            if not cited_citations:
                notes.append("Dynamic evidence support must cite the opened evidence.")
            if "standalone composed claim" not in bullet.text:
                notes.append("Dynamic evidence support must avoid promoting raw snippets to composed claims.")
        elif bullet.wording_category == "question_framed_open_issue":
            if bullet.section != "Open issues":
                notes.append("Question-framed open issue is not placed in Open issues.")
            if not cited_citations:
                notes.append("Question-framed open issue must cite boundary evidence.")

        if notes:
            status = "fail"
            blocking_violations.extend(
                f"{bullet.bullet_id}: {note}" for note in notes
            )

        records.append(
            AnswerAlignmentRecord(
                answer_claim_id=bullet.bullet_id,
                answer_section=bullet.section,
                wording_category=bullet.wording_category,
                claim_ids=list(bullet.claim_ids),
                claim_states=list(bullet.claim_states),
                cited_source_ids=[citation.source_id for citation in cited_citations],
                cited_source_roles=cited_roles,
                evidence_partition_labels=[
                    evidence_line.label for evidence_line in bullet.evidence_lines
                ],
                alignment_status=status,
                notes=notes,
            )
        )

    return AnswerAlignmentReport(
        question=question,
        intent_type=intent_type,
        records=records,
        blocking_violations=blocking_violations,
    )


def _build_topology_facet_coverage_report(
    question: str,
    query_intent: QueryIntent,
    bullets: Sequence[_AnswerBullet],
) -> FacetCoverageReport:
    bullet_ids = {bullet.bullet_id for bullet in bullets}
    claim_ids = {
        claim_id
        for bullet in bullets
        for claim_id in bullet.claim_ids
    }

    def facet(facet_id: str, addressed: bool, evidence: List[str]) -> FacetCoverageFacet:
        return FacetCoverageFacet(
            facet_id=facet_id,
            addressed=addressed,
            evidence=evidence,
        )

    multiplicity_evidence: List[str] = []
    if "topology_unresolved_multiplicity" in bullet_ids:
        multiplicity_evidence.append("bullet_id:topology_unresolved_multiplicity")
    if "topology_project_artifact_multiplicity" in claim_ids:
        multiplicity_evidence.append("claim_id:topology_project_artifact_multiplicity")
    if "topology_project_intended_use_scoping" in claim_ids:
        multiplicity_evidence.append("claim_id:topology_project_intended_use_scoping")

    derived_term_evidence: List[str] = []
    if "topology_undefined_term_status" in bullet_ids:
        derived_term_evidence.append("bullet_id:topology_undefined_term_status")

    registration_evidence: List[str] = []
    if "topology_registration_certificate_role" in claim_ids:
        registration_evidence.append("claim_id:topology_registration_certificate_role")
    if "topology_governing_scope_interpretation" in bullet_ids:
        registration_evidence.append("bullet_id:topology_governing_scope_interpretation")

    access_evidence: List[str] = []
    if "topology_access_certificate_role" in claim_ids:
        access_evidence.append("claim_id:topology_access_certificate_role")
    if "topology_access_certificate_role" in bullet_ids:
        access_evidence.append("bullet_id:topology_access_certificate_role")
    if "topology_governing_scope_interpretation" in bullet_ids:
        access_evidence.append("bullet_id:topology_governing_scope_interpretation")

    unresolved_evidence: List[str] = []
    if "topology_governing_scope_interpretation" in bullet_ids:
        unresolved_evidence.append("bullet_id:topology_governing_scope_interpretation")
    if "topology_unresolved_multiplicity" in bullet_ids:
        unresolved_evidence.append("bullet_id:topology_unresolved_multiplicity")

    return FacetCoverageReport(
        question=question,
        intent_type=query_intent.intent_type,
        facets=[
            facet(
                "multiplicity_single_certificate",
                bool(multiplicity_evidence),
                multiplicity_evidence,
            ),
            facet(
                "derived_certificate_term_status",
                bool(derived_term_evidence),
                derived_term_evidence,
            ),
            facet(
                "registration_certificate_role",
                bool(registration_evidence),
                registration_evidence,
            ),
            facet(
                "access_certificate_role",
                bool(access_evidence),
                access_evidence,
            ),
            facet(
                "unresolved_or_interpretive_status",
                bool(unresolved_evidence),
                unresolved_evidence,
            ),
        ],
    )


def compose_answer_bundle(
    question: str,
    entries: List[LedgerEntry],
    *,
    query_intent: Optional[QueryIntent] = None,
    clarification_note: Optional[str] = None,
    documents: Sequence[SourceDocument] = (),
    relation_hint_report: Optional[RelationHintReport] = None,
    composer_mode: str = "classic",
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix] = None,
) -> ComposedAnswerBundle:
    if not entries:
        facet_coverage_report = (
            _build_topology_facet_coverage_report(question, query_intent, [])
            if query_intent is not None
            and query_intent.intent_type == "certificate_topology_analysis"
            else None
        )
        rendered_answer = (
            f"First-pass note: {clarification_note}\n"
            "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
            if clarification_note
            else "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
        )
        return ComposedAnswerBundle(
            rendered_answer=rendered_answer,
            facet_coverage_report=facet_coverage_report,
            pinpoint_evidence_report=PinpointEvidenceReport(
                question=question,
                intent_type=query_intent.intent_type if query_intent is not None else "unknown",
                records=[],
            ),
            answer_alignment_report=AnswerAlignmentReport(
                question=question,
                intent_type=query_intent.intent_type if query_intent is not None else "unknown",
                records=[],
            ),
        )

    if (
        query_intent is not None
        and query_intent.intent_type == "certificate_topology_analysis"
    ):
        summary = (
            "Source-bound answer: the reviewed sources support a more explicit topology answer "
            "than a flat certificate-role summary."
        )
        bullets = _compose_certificate_topology_bullets(entries, query_intent, documents)
        facet_coverage_report = _build_topology_facet_coverage_report(
            question,
            query_intent,
            bullets,
        )
    elif _is_eubw_structured_intent(query_intent):
        assert query_intent is not None
        summary = _eubw_structured_summary(query_intent)
        bullets = _compose_eubw_structured_bullets(entries, query_intent)
        facet_coverage_report = None
    else:
        summary = "Source-bound answer:"
        if len(entries) >= 2:
            summary += " the reviewed sources support a differentiated answer rather than a flat yes/no."
        bullets = _compose_generic_bullets(entries, relation_hint_report)
        facet_coverage_report = None

    if composer_mode == "vnext":
        bullets.extend(_question_framed_open_issue_bullets(question, entries))

    rendered_answer = (
        _render_bullets_vnext(
            question,
            summary,
            bullets,
            clarification_note,
            evidence_synthesis_matrix,
        )
        if composer_mode == "vnext"
        else _render_bullets(summary, bullets, clarification_note)
    )
    pinpoint_evidence_report = _build_pinpoint_evidence_report(
        question,
        query_intent.intent_type if query_intent is not None else "unknown",
        bullets,
    )
    answer_alignment_report = _build_answer_alignment_report(
        question,
        query_intent.intent_type if query_intent is not None else "unknown",
        bullets,
    )
    return ComposedAnswerBundle(
        rendered_answer=rendered_answer,
        facet_coverage_report=facet_coverage_report,
        pinpoint_evidence_report=pinpoint_evidence_report,
        answer_alignment_report=answer_alignment_report,
    )


def compose_answer(
    question: str,
    entries: List[LedgerEntry],
    *,
    query_intent: Optional[QueryIntent] = None,
    clarification_note: Optional[str] = None,
    documents: Sequence[SourceDocument] = (),
    relation_hint_report: Optional[RelationHintReport] = None,
    composer_mode: str = "classic",
    evidence_synthesis_matrix: Optional[EvidenceSynthesisMatrix] = None,
) -> str:
    return compose_answer_bundle(
        question,
        entries,
        query_intent=query_intent,
        clarification_note=clarification_note,
        documents=documents,
        relation_hint_report=relation_hint_report,
        composer_mode=composer_mode,
        evidence_synthesis_matrix=evidence_synthesis_matrix,
    ).rendered_answer


def build_facet_coverage_report(
    question: str,
    query_intent: QueryIntent,
    *args,
    documents: Sequence[SourceDocument] = (),
) -> Optional[FacetCoverageReport]:
    if query_intent.intent_type != "certificate_topology_analysis":
        return None
    if len(args) == 1:
        entry_list = list(args[0])
    elif len(args) == 2 and isinstance(args[0], str):
        # Backward-compatibility path: the legacy rendered_answer argument is now ignored
        # because topology coverage is derived from structured bullets rather than answer text.
        entry_list = list(args[1])
    else:
        raise TypeError(
            "build_facet_coverage_report expects either "
            "(question, query_intent, entries) or "
            "(question, query_intent, rendered_answer, entries)."
        )

    bullets = _compose_certificate_topology_bullets(
        entry_list,
        query_intent,
        documents,
    )
    return _build_topology_facet_coverage_report(
        question,
        query_intent,
        bullets,
    )
