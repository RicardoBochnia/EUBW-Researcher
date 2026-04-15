from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from eubw_researcher.models import (
    Citation,
    ClaimState,
    LedgerEntry,
    QueryIntent,
    RelationHintEvidencePartition,
    RelationHintRecord,
    RelationHintReport,
    SourceRoleLevel,
)


@dataclass(frozen=True)
class _HintDefinition:
    hint_id: str
    family_id: str
    required_all: tuple[str, ...]
    required_any: tuple[str, ...] = ()


_SUPPORTED_HINTS_BY_INTENT: dict[str, tuple[_HintDefinition, ...]] = {
    "certificate_topology_analysis": (
        _HintDefinition(
            hint_id="topology_registration_access_dependency",
            family_id="certificate_role_topology",
            required_all=(
                "topology_access_certificate_role",
                "topology_registration_access_linkage",
            ),
        ),
        _HintDefinition(
            hint_id="topology_governing_scope_boundary",
            family_id="certificate_role_topology",
            required_all=(
                "topology_registration_certificate_role",
                "topology_access_certificate_role",
                "topology_registration_access_linkage",
            ),
        ),
        _HintDefinition(
            hint_id="topology_non_governing_multiplicity_expansion",
            family_id="certificate_role_topology",
            required_all=("topology_project_artifact_multiplicity",),
            required_any=(
                "topology_project_intended_use_scoping",
                "topology_registration_certificate_role",
                "topology_access_certificate_role",
                "topology_registration_access_linkage",
            ),
        ),
    ),
    "wallet_requirements_summary": (
        _HintDefinition(
            hint_id="layering_requirement_to_annex_detail",
            family_id="registration_requirement_layering",
            required_all=(
                "wallet_access_certificate_requirement",
                "annex_registration_fields",
            ),
        ),
        _HintDefinition(
            hint_id="layering_union_requirement_to_member_state_discretion",
            family_id="registration_requirement_layering",
            required_all=(
                "member_state_discretion",
                "wallet_access_certificate_requirement",
            ),
        ),
        _HintDefinition(
            hint_id="layering_union_requirement_to_national_guidance_boundary",
            family_id="registration_requirement_layering",
            required_all=(
                "wallet_national_guidance_boundary",
                "wallet_access_certificate_requirement",
            ),
        ),
    ),
    "certificate_layer_analysis": (
        _HintDefinition(
            hint_id="layering_certificate_requirement_to_national_guidance_boundary",
            family_id="registration_requirement_layering",
            required_all=(
                "access_certificate_eu_level",
                "national_guidance_boundary",
            ),
        ),
    ),
    "registration_certificate_scope": (
        _HintDefinition(
            hint_id="layering_registration_requirement_to_member_state_discretion",
            family_id="registration_requirement_layering",
            required_all=(
                "registration_certificate_eu_level",
                "member_state_discretion",
            ),
        ),
    ),
    "relying_party_registration_information": (
        _HintDefinition(
            hint_id="layering_annex_requirement_to_categories",
            family_id="registration_requirement_layering",
            required_all=(
                "rp_registration_annex_i_requirement",
                "rp_registration_information_categories",
            ),
        ),
    ),
}

_SUMMARY_TEMPLATES: dict[str, dict[str, str]] = {
    "topology_registration_access_dependency": {
        "confirmed": (
            "Current approved evidence links the governing access-certificate role to the "
            "governing requirement that registration-certificate issuance depends on a valid access certificate."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the governing access-certificate role and the governing registration-issuance dependency belong to the same certificate chain."
        ),
    },
    "topology_governing_scope_boundary": {
        "confirmed": (
            "Current approved evidence places the governing registration-certificate role, access-certificate role, "
            "and registration-to-access linkage on the same governing scope boundary."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the governing registration-certificate role, access-certificate role, and their issuance linkage define the same scope boundary."
        ),
    },
    "topology_non_governing_multiplicity_expansion": {
        "open_partitioned": (
            "Current approved evidence keeps the multiplicity point supplemental: governing EU sources set the certificate-role boundary conditions, "
            "while medium-rank project artifacts make the broader multi-certificate reading more explicit."
        ),
    },
    "layering_requirement_to_annex_detail": {
        "confirmed": (
            "Current approved evidence ties the Union-level access-certificate requirement to Annex-level registration-field detail."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the Union-level access-certificate requirement is elaborated through Annex-level registration-field detail."
        ),
    },
    "layering_union_requirement_to_member_state_discretion": {
        "confirmed": (
            "Current approved evidence links the Union-level requirement layer to the point where Member States retain implementation discretion."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the Union-level requirement layer and Member-State implementation discretion should be read together."
        ),
    },
    "layering_union_requirement_to_national_guidance_boundary": {
        "confirmed": (
            "Current approved evidence links the Union-level requirement layer to the boundary that national guidance may refine procedure but not override Union requirements."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the Union-level requirement layer and the national-guidance non-override boundary should be read together."
        ),
    },
    "layering_certificate_requirement_to_national_guidance_boundary": {
        "confirmed": (
            "Current approved evidence links the Union-level access-certificate requirement to the boundary that national guidance may add procedure without overriding Union requirements."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the Union-level access-certificate requirement and the national-guidance non-override boundary should be read together."
        ),
    },
    "layering_registration_requirement_to_member_state_discretion": {
        "confirmed": (
            "Current approved evidence links the Union-level registration-certificate requirement to the point where Member States retain implementation discretion."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the Union-level registration-certificate requirement and Member-State implementation discretion should be read together."
        ),
    },
    "layering_annex_requirement_to_categories": {
        "confirmed": (
            "Current approved evidence links the Annex I registration-information requirement to the category-level information set used to review those fields."
        ),
        "interpretive": (
            "Current approved evidence supports, but does not fully settle as a straight confirmed statement, "
            "that the Annex I registration-information requirement and the category-level information set should be read together."
        ),
    },
}

_LIMITATION_TEMPLATES = {
    "confirmed": (
        "Supplemental cross-reference only; this hint is derived from already-approved claims and remains source-bound."
    ),
    "interpretive": (
        "Supplemental cross-reference only; at least one contributing claim remains interpretive, so review this as a bounded synthesis rather than a standalone confirmed fact."
    ),
    "open": (
        "Supplemental cross-reference only; at least one contributing claim remains open, so this hint is not answer-renderable in this issue."
    ),
    "open_partitioned": (
        "Supplemental cross-reference only; the broader reading remains partitioned across governing and medium-rank support and is kept artifact-only in this issue."
    ),
}


def supports_relation_hints(intent_type: str) -> bool:
    return intent_type in _SUPPORTED_HINTS_BY_INTENT


def build_relation_hint_report(
    question: str,
    approved_entries: Sequence[LedgerEntry],
    query_intent: QueryIntent,
) -> Optional[RelationHintReport]:
    definitions = _SUPPORTED_HINTS_BY_INTENT.get(query_intent.intent_type)
    if definitions is None:
        return None

    entry_by_claim_id = {entry.claim_id: entry for entry in approved_entries}
    records: list[RelationHintRecord] = []
    for definition in definitions:
        record = _build_relation_hint_record(
            definition,
            entry_by_claim_id,
        )
        if record is not None:
            records.append(record)

    families_considered = list(
        dict.fromkeys(definition.family_id for definition in definitions)
    )
    return RelationHintReport(
        question=question,
        intent_type=query_intent.intent_type,
        families_considered=families_considered,
        records=records,
    )


def _build_relation_hint_record(
    definition: _HintDefinition,
    entry_by_claim_id: dict[str, LedgerEntry],
) -> Optional[RelationHintRecord]:
    entry_options = _resolve_entry_options(definition, entry_by_claim_id)
    if entry_options is None:
        return None

    best_record: Optional[RelationHintRecord] = None
    best_key: Optional[tuple[int, int]] = None
    for option_index, entries in enumerate(entry_options):
        record = _build_relation_hint_record_for_entries(definition, entries)
        if record is None:
            continue
        record_key = (_relation_state_rank(record.relation_state), option_index)
        if best_key is None or record_key < best_key:
            best_record = record
            best_key = record_key
    return best_record


def _build_relation_hint_record_for_entries(
    definition: _HintDefinition,
    entries: Sequence[LedgerEntry],
) -> Optional[RelationHintRecord]:
    if definition.hint_id == "topology_registration_access_dependency":
        return _build_high_only_record(
            definition,
            entries,
            partition_label="Governing linkage support",
            rendered_in_answer=False,
        )
    if definition.hint_id == "topology_governing_scope_boundary":
        return _build_high_only_record(
            definition,
            entries,
            partition_label="Governing scope-boundary support",
            rendered_in_answer=False,
        )
    if definition.hint_id == "topology_non_governing_multiplicity_expansion":
        return _build_topology_multiplicity_record(definition, entries)
    if definition.hint_id == "layering_requirement_to_annex_detail":
        return _build_layering_requirement_to_annex_detail(definition, entries)
    if definition.hint_id == "layering_union_requirement_to_member_state_discretion":
        return _build_high_only_record(
            definition,
            entries,
            partition_label="Union-level requirement and discretion support",
            rendered_in_answer=True,
        )
    if definition.hint_id == "layering_union_requirement_to_national_guidance_boundary":
        return _build_boundary_record(
            definition,
            entries,
            high_claim_ids=(
                "wallet_access_certificate_requirement",
                "annex_registration_fields",
            ),
            medium_claim_ids=("wallet_national_guidance_boundary",),
        )
    if definition.hint_id == "layering_certificate_requirement_to_national_guidance_boundary":
        return _build_boundary_record(
            definition,
            entries,
            high_claim_ids=("access_certificate_eu_level",),
            medium_claim_ids=("national_guidance_boundary",),
        )
    if definition.hint_id == "layering_registration_requirement_to_member_state_discretion":
        return _build_high_only_record(
            definition,
            entries,
            partition_label="Union-level registration requirement and discretion support",
            rendered_in_answer=True,
        )
    if definition.hint_id == "layering_annex_requirement_to_categories":
        return _build_annex_categories_record(definition, entries)
    raise ValueError(f"Unsupported relation-hint definition: {definition.hint_id}")


def _resolve_entry_options(
    definition: _HintDefinition,
    entry_by_claim_id: dict[str, LedgerEntry],
) -> Optional[list[list[LedgerEntry]]]:
    required_entries: list[LedgerEntry] = []
    for claim_id in definition.required_all:
        entry = entry_by_claim_id.get(claim_id)
        if entry is None:
            return None
        required_entries.append(entry)

    if definition.required_any:
        option_entries = [
            _ordered_unique_entries([*required_entries, entry_by_claim_id[claim_id]])
            for claim_id in definition.required_any
            if claim_id in entry_by_claim_id
        ]
        if not option_entries:
            return None
        return option_entries

    return [_ordered_unique_entries(required_entries)]


def _ordered_unique_entries(entries: Sequence[LedgerEntry]) -> list[LedgerEntry]:
    seen: set[str] = set()
    ordered_entries: list[LedgerEntry] = []
    for entry in entries:
        if entry.claim_id in seen:
            continue
        seen.add(entry.claim_id)
        ordered_entries.append(entry)
    return ordered_entries


def _relation_state_rank(relation_state: str) -> int:
    return {
        "confirmed": 0,
        "interpretive": 1,
        "open_partitioned": 2,
        "open": 3,
    }[relation_state]


def _derive_relation_state(
    entries: Sequence[LedgerEntry],
    *,
    forced_state: Optional[str] = None,
) -> str:
    if forced_state is not None:
        return forced_state
    claim_states = [entry.final_claim_state for entry in entries]
    if any(state == ClaimState.OPEN for state in claim_states):
        return "open"
    if any(state == ClaimState.INTERPRETIVE for state in claim_states):
        return "interpretive"
    return "confirmed"


def _build_high_only_record(
    definition: _HintDefinition,
    entries: Sequence[LedgerEntry],
    *,
    partition_label: str,
    rendered_in_answer: bool,
) -> Optional[RelationHintRecord]:
    relation_state = _derive_relation_state(entries)
    if relation_state == "open":
        return None
    partition = _build_partition(
        partition_label,
        entries,
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    if partition is None:
        return None
    return _make_record(
        definition,
        relation_state=relation_state,
        entries=entries,
        partitions=[partition],
        rendered_in_answer=rendered_in_answer,
    )


def _build_topology_multiplicity_record(
    definition: _HintDefinition,
    entries: Sequence[LedgerEntry],
) -> Optional[RelationHintRecord]:
    high_partition = _build_partition(
        "Governing boundary support",
        [
            entry
            for entry in entries
            if entry.claim_id != "topology_project_artifact_multiplicity"
        ],
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    medium_partition = _build_partition(
        "Project-artifact multiplicity support",
        [
            entry
            for entry in entries
            if entry.claim_id in {
                "topology_project_artifact_multiplicity",
                "topology_project_intended_use_scoping",
            }
        ],
        allowed_roles=(SourceRoleLevel.MEDIUM,),
    )
    if high_partition is None or medium_partition is None:
        return None
    return _make_record(
        definition,
        relation_state="open_partitioned",
        entries=entries,
        partitions=[high_partition, medium_partition],
        rendered_in_answer=False,
    )


def _build_layering_requirement_to_annex_detail(
    definition: _HintDefinition,
    entries: Sequence[LedgerEntry],
) -> Optional[RelationHintRecord]:
    relation_state = _derive_relation_state(entries)
    if relation_state == "open":
        return None
    requirement_partition = _build_partition(
        "Union-level requirement support",
        [
            entry
            for entry in entries
            if entry.claim_id == "wallet_access_certificate_requirement"
        ],
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    annex_partition = _build_partition(
        "Annex detail support",
        [
            entry
            for entry in entries
            if entry.claim_id == "annex_registration_fields"
        ],
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    if requirement_partition is None or annex_partition is None:
        return None
    return _make_record(
        definition,
        relation_state=relation_state,
        entries=entries,
        partitions=[requirement_partition, annex_partition],
        rendered_in_answer=True,
    )


def _build_boundary_record(
    definition: _HintDefinition,
    entries: Sequence[LedgerEntry],
    *,
    high_claim_ids: Sequence[str],
    medium_claim_ids: Sequence[str],
) -> Optional[RelationHintRecord]:
    relation_state = _derive_relation_state(entries)
    if relation_state == "open":
        return None
    high_partition = _build_partition(
        "Union-level requirement support",
        [entry for entry in entries if entry.claim_id in set(high_claim_ids)],
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    medium_partition = _build_partition(
        "National-guidance boundary support",
        [entry for entry in entries if entry.claim_id in set(medium_claim_ids)],
        allowed_roles=(SourceRoleLevel.MEDIUM,),
    )
    if high_partition is None or medium_partition is None:
        return None
    return _make_record(
        definition,
        relation_state=relation_state,
        entries=entries,
        partitions=[high_partition, medium_partition],
        rendered_in_answer=True,
    )


def _build_annex_categories_record(
    definition: _HintDefinition,
    entries: Sequence[LedgerEntry],
) -> Optional[RelationHintRecord]:
    relation_state = _derive_relation_state(entries)
    if relation_state == "open":
        return None
    annex_partition = _build_partition(
        "Annex I requirement support",
        [entry for entry in entries if entry.claim_id == "rp_registration_annex_i_requirement"],
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    if annex_partition is None:
        return None
    category_entry = next(
        entry for entry in entries if entry.claim_id == "rp_registration_information_categories"
    )
    high_category_partition = _build_partition(
        "Category-level governing support",
        [category_entry],
        allowed_roles=(SourceRoleLevel.HIGH,),
    )
    medium_category_partition = _build_partition(
        "Category-level supplemental support",
        [category_entry],
        allowed_roles=(SourceRoleLevel.MEDIUM,),
    )
    partitions = [annex_partition]
    if high_category_partition is not None:
        partitions.append(high_category_partition)
    if medium_category_partition is not None:
        partitions.append(medium_category_partition)
    if len(partitions) == 1:
        return None
    return _make_record(
        definition,
        relation_state=relation_state,
        entries=entries,
        partitions=partitions,
        rendered_in_answer=high_category_partition is not None,
    )


def _make_record(
    definition: _HintDefinition,
    *,
    relation_state: str,
    entries: Sequence[LedgerEntry],
    partitions: Sequence[RelationHintEvidencePartition],
    rendered_in_answer: bool,
) -> RelationHintRecord:
    claim_ids = [entry.claim_id for entry in entries]
    claim_states = [entry.final_claim_state for entry in entries]
    supporting_source_ids = _ordered_unique_strings(
        source_id
        for partition in partitions
        for source_id in partition.source_ids
    )
    return RelationHintRecord(
        hint_id=definition.hint_id,
        family_id=definition.family_id,
        relation_state=relation_state,
        summary=_SUMMARY_TEMPLATES[definition.hint_id][relation_state],
        derived_from_claim_ids=claim_ids,
        derived_from_claim_states=claim_states,
        supporting_source_ids=supporting_source_ids,
        evidence_partitions=list(partitions),
        limitation_note=_LIMITATION_TEMPLATES[relation_state],
        rendered_in_answer=rendered_in_answer,
    )


def _build_partition(
    partition_label: str,
    entries: Sequence[LedgerEntry],
    *,
    allowed_roles: Sequence[SourceRoleLevel],
) -> Optional[RelationHintEvidencePartition]:
    if not entries:
        return None
    role_set = set(allowed_roles)
    citations: list[Citation] = []
    claim_ids: list[str] = []
    for entry in entries:
        matching = _entry_citations_for_roles(entry, role_set)
        if not matching:
            continue
        claim_ids.append(entry.claim_id)
        citations.extend(matching)
    citations = _dedupe_citations(citations)
    if not citations:
        return None
    return RelationHintEvidencePartition(
        partition_label=partition_label,
        source_role_levels=_ordered_unique_roles(
            citation.source_role_level for citation in citations
        ),
        claim_ids=claim_ids,
        source_ids=_ordered_unique_strings(citation.source_id for citation in citations),
        citations=citations,
    )


def _entry_citations_for_roles(
    entry: LedgerEntry,
    allowed_roles: set[SourceRoleLevel],
) -> list[Citation]:
    return _dedupe_citations(
        citation for citation in entry.citations if citation.source_role_level in allowed_roles
    )


def _dedupe_citations(citations: Iterable[Citation]) -> list[Citation]:
    seen: set[tuple[object, ...]] = set()
    deduped: list[Citation] = []
    for citation in citations:
        key = (
            citation.source_id,
            citation.document_title,
            citation.source_role_level,
            citation.source_kind,
            citation.jurisdiction,
            citation.citation_quality,
            str(citation.document_path) if citation.document_path is not None else None,
            citation.canonical_url,
            citation.document_status,
            citation.source_origin,
            citation.anchor_label,
            citation.structure_poor,
            citation.anchor_audit_note,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def _ordered_unique_strings(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _ordered_unique_roles(values: Iterable[SourceRoleLevel]) -> list[SourceRoleLevel]:
    ordered: list[SourceRoleLevel] = []
    seen: set[SourceRoleLevel] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
