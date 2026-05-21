from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import List

from eubw_researcher.models import (
    ArchiveCorpusConfig,
    ArchiveSourceSelection,
    BindingLevel,
    ClaimState,
    ClaimType,
    ClaimTypeGovernanceRule,
    DiscoveryEntrypoint,
    DocumentStatus,
    EffectiveDatePolicy,
    EvidenceTier,
    EvaluationScenario,
    ExpectedConceptCandidate,
    ExpectedConceptStatus,
    TerminologyAlias,
    RealQuestionPack,
    RealQuestionPackQuestion,
    HierarchyRule,
    ResearchProfile,
    ResearchProfileConfig,
    RuntimeConfig,
    SourceHierarchyConfig,
    SourceKind,
    SourceGovernanceConfig,
    SourceOrigin,
    SourceRoleLevel,
    TerminologyConfig,
    TerminologyMapping,
    WebDomainPolicy,
    WebAllowlistConfig,
)


def _load_json_yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base_dir / path).resolve()


def _optional_stripped(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _stripped_string_list(
    value: object,
    *,
    field_name: str,
    owner_id: str,
    path: Path,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(
            f"Real-question pack question '{owner_id}' field '{field_name}' must be a list: {path}"
        )
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"Real-question pack question '{owner_id}' field '{field_name}' must contain only strings: {path}"
            )
        stripped = item.strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _non_negative_int(
    value: object,
    *,
    field_name: str,
    owner_id: str,
    path: Path,
) -> int:
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"Real-question pack question '{owner_id}' field '{field_name}' must be a non-negative integer: {path}"
        )
    if value < 0:
        raise ValueError(
            f"Real-question pack question '{owner_id}' field '{field_name}' must be a non-negative integer: {path}"
        )
    return value


def _optional_bool(
    value: object,
    *,
    field_name: str,
    owner_id: str,
    path: Path,
) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError(
            f"Real-question pack question '{owner_id}' field '{field_name}' must be a boolean: {path}"
        )
    return value


def _validate_safe_config_id(
    *,
    raw_id: str,
    id_label: str,
    path: Path,
) -> str:
    normalized = raw_id.strip()
    if not normalized:
        raise ValueError(f"{id_label} contains a blank id: {path}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
        raise ValueError(
            f"{id_label} must use only letters, numbers, periods, underscores, or hyphens: "
            f"{normalized}"
        )
    if normalized.startswith("."):
        raise ValueError(
            f"{id_label} must not be '.' or '..' and must not start with a period: "
            f"{normalized}"
        )
    return normalized


def load_source_hierarchy(path: Path) -> SourceHierarchyConfig:
    payload = _load_json_yaml(path)
    rules = [
        HierarchyRule(
            source_kind=SourceKind(item["source_kind"]),
            source_role_level=SourceRoleLevel(item["source_role_level"]),
            rank=int(item["rank"]),
        )
        for item in payload["levels"]
    ]
    return SourceHierarchyConfig(
        rules=rules,
        default_eu_first=bool(payload.get("default_eu_first", True)),
    )


def load_source_governance(path: Path) -> SourceGovernanceConfig:
    payload = _load_json_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Source-governance config must be a JSON/YAML object: {path}")
    raw_compatibility = payload.get("claim_type_compatibility", {})
    if not isinstance(raw_compatibility, dict):
        raise ValueError(
            f"Source-governance config field 'claim_type_compatibility' must be an object: {path}"
        )
    claim_type_compatibility: dict[ClaimType, ClaimTypeGovernanceRule] = {}
    for raw_claim_type, raw_rule in raw_compatibility.items():
        if not isinstance(raw_rule, dict):
            raise ValueError(
                f"Source-governance rule for '{raw_claim_type}' must be an object: {path}"
            )
        claim_type = ClaimType(str(raw_claim_type))
        raw_allowed_levels = raw_rule.get("allowed_binding_levels", [])
        if not isinstance(raw_allowed_levels, list):
            raise ValueError(
                f"Source-governance rule for '{raw_claim_type}' must define list allowed_binding_levels: {path}"
            )
        claim_type_compatibility[claim_type] = ClaimTypeGovernanceRule(
            allowed_binding_levels=[
                BindingLevel(str(level)) for level in raw_allowed_levels
            ],
            binding_required_for_current_law=bool(
                raw_rule.get("binding_required_for_current_law", False)
            ),
        )
    raw_effective_date_policy = payload.get("effective_date_policy", {})
    if raw_effective_date_policy is None:
        raw_effective_date_policy = {}
    if not isinstance(raw_effective_date_policy, dict):
        raise ValueError(
            f"Source-governance config field 'effective_date_policy' must be an object: {path}"
        )
    return SourceGovernanceConfig(
        policy_version=str(payload.get("policy_version", "source_governance.unknown")),
        claim_type_compatibility=claim_type_compatibility,
        effective_date_policy=EffectiveDatePolicy(
            current_law_claims_require_effective_date_or_final_status=bool(
                raw_effective_date_policy.get(
                    "current_law_claims_require_effective_date_or_final_status",
                    True,
                )
            ),
            adopted_pending_effective_date_must_be_qualified=bool(
                raw_effective_date_policy.get(
                    "adopted_pending_effective_date_must_be_qualified",
                    True,
                )
            ),
            proposal_must_not_support_final_law_wording=bool(
                raw_effective_date_policy.get(
                    "proposal_must_not_support_final_law_wording",
                    True,
                )
            ),
        ),
    )


def load_web_allowlist(path: Path) -> WebAllowlistConfig:
    payload = _load_json_yaml(path)

    def _load_discovery_entrypoints(item: dict) -> List[DiscoveryEntrypoint]:
        configured = item.get("discovery_entrypoints")
        if configured is not None:
            return [
                DiscoveryEntrypoint(
                    entrypoint_id=str(entry["entrypoint_id"]).strip(),
                    url_template=str(entry["url_template"]).strip(),
                    strategy=str(entry["strategy"]).strip(),
                )
                for entry in configured
            ]
        return [
            DiscoveryEntrypoint(
                entrypoint_id=f"{item.get('policy_id', item['domain'] + ':' + item['source_kind'])}:legacy:{index + 1}",
                url_template=str(url).strip(),
                strategy="index_crawl",
            )
            for index, url in enumerate(item.get("discovery_urls", []))
            if str(url).strip()
        ]

    domain_policies = [
        WebDomainPolicy(
            domain=item["domain"],
            source_kind=SourceKind(item["source_kind"]),
            source_role_level=SourceRoleLevel(item["source_role_level"]),
            jurisdiction=item["jurisdiction"],
            policy_id=item.get("policy_id"),
            allowed_intent_types=list(item.get("allowed_intent_types", [])),
            seed_urls=list(item.get("seed_urls", [])),
            discovery_entrypoints=_load_discovery_entrypoints(item),
            crawl_path_prefixes=list(
                item.get("crawl_path_prefixes", item.get("allowed_path_prefixes", []))
            ),
            admission_path_prefixes=list(
                item.get("admission_path_prefixes", item.get("allowed_path_prefixes", []))
            ),
            blocked_url_keywords=list(item.get("blocked_url_keywords", [])),
            allowed_cross_domain_domains=list(item.get("allowed_cross_domain_domains", [])),
            discovery_urls=(
                []
                if item.get("discovery_entrypoints") is not None
                else list(item.get("discovery_urls", []))
            ),
            allowed_path_prefixes=list(item.get("allowed_path_prefixes", [])),
        )
        for item in payload.get("domain_policies", [])
    ]
    return WebAllowlistConfig(
        allowed_domains=list(payload["allowed_domains"]),
        domain_policies=domain_policies,
    )


def load_archive_corpus_config(path: Path) -> ArchiveCorpusConfig:
    payload = _load_json_yaml(path)
    base_dir = path.parent
    return ArchiveCorpusConfig(
        archive_root=_resolve_path(base_dir, payload["archive_root"]),
        archive_catalog=_resolve_path(base_dir, payload["archive_catalog"]),
        sources=[
            ArchiveSourceSelection(
                archive_source_id=item["archive_source_id"],
                source_id=item["source_id"],
                title=item["title"],
                source_kind=SourceKind(item["source_kind"]),
                source_role_level=SourceRoleLevel(item["source_role_level"]),
                jurisdiction=item["jurisdiction"],
                publication_status=item.get("publication_status"),
                publication_date=item.get("publication_date"),
                document_status=DocumentStatus(item.get("document_status", "final")),
                source_origin=SourceOrigin(item.get("source_origin", "local")),
                anchorability_hints=list(item.get("anchorability_hints", [])),
                admission_reason=item.get("admission_reason"),
                source_family_id=item.get("source_family_id"),
                successor_candidate_urls=list(item.get("successor_candidate_urls", [])),
                evidence_tier=EvidenceTier(item.get("evidence_tier", "unknown")),
                binding_level=BindingLevel(item.get("binding_level", "unknown")),
                archive_source_id_aliases=list(item.get("archive_source_id_aliases", [])),
                legacy_source_ids=list(item.get("legacy_source_ids", [])),
                version_date=item.get("version_date"),
                effective_date=item.get("effective_date"),
                content_digest=item.get("content_digest"),
                locator_strategy=item.get("locator_strategy"),
                predecessor_source_ids=list(item.get("predecessor_source_ids", [])),
                successor_source_ids=list(item.get("successor_source_ids", [])),
                governance_metadata=dict(item.get("governance_metadata", {})),
            )
            for item in payload["sources"]
        ],
    )


def load_runtime_config(path: Path) -> RuntimeConfig:
    payload = _load_json_yaml(path)
    retrieval = payload["retrieval"]
    knowledge_service = payload.get("knowledge_service", {})
    reading_loop = knowledge_service.get("reading_loop", {})
    if reading_loop is None:
        reading_loop = {}
    if not isinstance(reading_loop, dict):
        raise ValueError(f"Runtime config field knowledge_service.reading_loop must be an object: {path}")
    answer_composer = payload.get("answer_composer", {})
    if answer_composer is None:
        answer_composer = {}
    if not isinstance(answer_composer, dict):
        raise ValueError(f"Runtime config field answer_composer must be an object: {path}")
    return RuntimeConfig(
        logging_level=payload["logging"]["level"],
        retrieval_top_k=int(retrieval["top_k"]),
        lexical_weight=float(retrieval["lexical_weight"]),
        semantic_weight=float(retrieval["semantic_weight"]),
        min_combined_score=float(retrieval["min_combined_score"]),
        semantic_expansions={
            key: list(value) for key, value in retrieval["semantic_expansions"].items()
        },
        web_timeout_seconds=int(retrieval.get("web_timeout_seconds", 10)),
        web_discovery_max_depth=int(retrieval.get("web_discovery_max_depth", 1)),
        web_discovery_max_pages=int(retrieval.get("web_discovery_max_pages", 8)),
        web_discovery_max_candidates_per_kind=int(
            retrieval.get("web_discovery_max_candidates_per_kind", 5)
        ),
        web_max_admitted_per_domain=int(retrieval.get("web_max_admitted_per_domain", 10)),
        web_max_admitted_per_run=int(retrieval.get("web_max_admitted_per_run", 25)),
        local_retrieval_backend=str(
            retrieval.get("local_retrieval_backend", "sqlite_fts")
        ).strip(),
        local_index_candidate_pool=int(
            retrieval.get("local_index_candidate_pool", retrieval["top_k"])
        ),
        knowledge_service_enabled=bool(knowledge_service.get("enabled", False)),
        knowledge_service_emit_clusters=bool(knowledge_service.get("emit_clusters", False)),
        knowledge_service_discovery_mode=str(
            knowledge_service.get("discovery_mode", "shadow")
        ).strip(),
        knowledge_service_strict_verification_required=bool(
            knowledge_service.get("strict_verification_required", True)
        ),
        knowledge_service_reading_loop_enabled=bool(
            reading_loop.get("enabled", False)
        ),
        knowledge_service_max_reading_clusters=int(
            reading_loop.get("max_clusters", 5)
        ),
        knowledge_service_max_opened_passages=int(
            reading_loop.get("max_opened_passages", 10)
        ),
        knowledge_service_max_adjacent_passages_per_cluster=int(
            reading_loop.get("max_adjacent_passages_per_cluster", 1)
        ),
        knowledge_service_reading_timeout_seconds=int(
            reading_loop.get("timeout_seconds", 30)
        ),
        knowledge_service_legacy_assets_root=(
            str(knowledge_service["legacy_assets_root"]).strip()
            if knowledge_service.get("legacy_assets_root")
            else None
        ),
        knowledge_service_max_candidate_claim_targets=int(
            knowledge_service.get("max_candidate_claim_targets", 8)
        ),
        answer_composer_mode=str(answer_composer.get("mode", "classic")).strip(),
    )


def runtime_config_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_terminology_config(path: Path) -> TerminologyConfig:
    payload = _load_json_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Terminology config must be a JSON/YAML object: {path}")
    raw_mappings = payload.get("mappings")
    if not isinstance(raw_mappings, list):
        raise ValueError(f"Terminology config must define a list 'mappings': {path}")

    generator_owned = payload.get("generator_owned", False)
    if not isinstance(generator_owned, bool):
        raise ValueError(f"Terminology config field 'generator_owned' must be a bool: {path}")

    policy_version = payload.get("policy_version")
    if policy_version is not None and not isinstance(policy_version, str):
        raise ValueError(f"Terminology config field 'policy_version' must be a string: {path}")

    archive_catalog_path = payload.get("archive_catalog_path")
    if archive_catalog_path is not None and not isinstance(archive_catalog_path, str):
        raise ValueError(
            f"Terminology config field 'archive_catalog_path' must be a string: {path}"
        )

    curated_catalog_path = payload.get("curated_catalog_path")
    if curated_catalog_path is not None and not isinstance(curated_catalog_path, str):
        raise ValueError(
            f"Terminology config field 'curated_catalog_path' must be a string: {path}"
        )

    seen_canonical_terms: dict[str, str] = {}
    seen_trigger_terms: dict[str, str] = {}
    mappings: list[TerminologyMapping] = []

    for index, item in enumerate(raw_mappings, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Terminology mapping #{index} must be an object with canonical_term and aliases: {path}"
            )
        canonical_term = _optional_stripped(item.get("canonical_term"))
        if canonical_term is None:
            raise ValueError(f"Terminology mapping #{index} is missing canonical_term: {path}")

        canonical_key = canonical_term.casefold()
        if canonical_key in seen_canonical_terms:
            raise ValueError(
                f"Terminology config contains duplicate canonical_term '{canonical_term}': {path}"
            )
        seen_canonical_terms[canonical_key] = canonical_term

        raw_aliases = item.get("aliases")
        if not isinstance(raw_aliases, list):
            raise ValueError(
                f"Terminology mapping '{canonical_term}' must define a list 'aliases': {path}"
            )
        alias_rules: list[TerminologyAlias] = []
        seen_mapping_aliases: set[str] = set()
        for raw_alias in raw_aliases:
            if isinstance(raw_alias, dict):
                alias = _optional_stripped(raw_alias.get("term"))
                raw_alias_contexts = raw_alias.get("context_aliases", [])
                if not isinstance(raw_alias_contexts, list):
                    raise ValueError(
                        f"Terminology alias object for '{canonical_term}' must define list context_aliases when present: {path}"
                    )
            elif isinstance(raw_alias, str):
                alias = _optional_stripped(raw_alias)
                raw_alias_contexts = []
            else:
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' aliases must be strings or alias objects: {path}"
                )
            if alias is None:
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' contains a blank alias: {path}"
                )
            alias_key = alias.casefold()
            if alias_key == canonical_key:
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' must not repeat the canonical term as an alias: {path}"
                )
            if alias_key in seen_mapping_aliases:
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' contains duplicate alias '{alias}': {path}"
                )
            seen_mapping_aliases.add(alias_key)
            alias_context_aliases: list[str] = []
            seen_alias_contexts: set[str] = set()
            for raw_alias_context in raw_alias_contexts:
                if not isinstance(raw_alias_context, str):
                    raise ValueError(
                        f"Terminology alias '{alias}' for '{canonical_term}' context aliases must be strings: {path}"
                    )
                alias_context = _optional_stripped(raw_alias_context)
                if alias_context is None:
                    raise ValueError(
                        f"Terminology alias '{alias}' for '{canonical_term}' contains a blank context alias: {path}"
                    )
                alias_context_key = alias_context.casefold()
                if alias_context_key in seen_alias_contexts:
                    raise ValueError(
                        f"Terminology alias '{alias}' for '{canonical_term}' contains duplicate context alias '{alias_context}': {path}"
                    )
                seen_alias_contexts.add(alias_context_key)
                alias_context_aliases.append(alias_context)
            alias_rules.append(
                TerminologyAlias(
                    term=alias,
                    context_aliases=tuple(alias_context_aliases),
                )
            )

        if not alias_rules:
            raise ValueError(
                f"Terminology mapping '{canonical_term}' must define at least one alias: {path}"
            )

        raw_context_aliases = item.get("context_aliases", [])
        if not isinstance(raw_context_aliases, list):
            raise ValueError(
                f"Terminology mapping '{canonical_term}' must define list context_aliases when present: {path}"
            )
        context_aliases: list[str] = []
        seen_context_aliases: set[str] = set()
        for raw_context_alias in raw_context_aliases:
            if not isinstance(raw_context_alias, str):
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' context_aliases must contain only strings: {path}"
                )
            context_alias = _optional_stripped(raw_context_alias)
            if context_alias is None:
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' contains a blank context alias: {path}"
                )
            context_key = context_alias.casefold()
            if context_key in seen_context_aliases:
                raise ValueError(
                    f"Terminology mapping '{canonical_term}' contains duplicate context alias '{context_alias}': {path}"
                )
            seen_context_aliases.add(context_key)
            context_aliases.append(context_alias)

        for trigger_term in [canonical_term, *(alias.term for alias in alias_rules)]:
            trigger_key = trigger_term.casefold()
            existing = seen_trigger_terms.get(trigger_key)
            if existing is not None and existing != canonical_term:
                raise ValueError(
                    f"Terminology config reuses trigger term '{trigger_term}' for both '{existing}' and '{canonical_term}': {path}"
                )
            seen_trigger_terms[trigger_key] = canonical_term

        mappings.append(
            TerminologyMapping(
                canonical_term=canonical_term,
                alias_rules=tuple(alias_rules),
                context_aliases=tuple(context_aliases),
            )
        )

    return TerminologyConfig(
        mappings=tuple(mappings),
        generator_owned=generator_owned,
        policy_version=policy_version,
        archive_catalog_path=archive_catalog_path,
        curated_catalog_path=curated_catalog_path,
    )


def load_evaluation_scenarios(path: Path) -> List[EvaluationScenario]:
    payload = _load_json_yaml(path)
    scenarios = [
        EvaluationScenario(
            scenario_id=_validate_safe_config_id(
                raw_id=str(item["scenario_id"]),
                id_label="Evaluation scenario scenario_id",
                path=path,
            ),
            question=item["question"],
            expectation=item["expectation"],
            required_intent_type=item.get("required_intent_type"),
            required_states=[ClaimState(value) for value in item.get("required_states", [])],
            allowed_states=[ClaimState(value) for value in item.get("allowed_states", [])],
            required_sources=list(item.get("required_sources", [])),
            forbidden_sources=list(item.get("forbidden_sources", [])),
            required_answer_substrings=list(item.get("required_answer_substrings", [])),
            forbidden_answer_substrings=list(item.get("forbidden_answer_substrings", [])),
            required_gap_reason_substrings=list(item.get("required_gap_reason_substrings", [])),
            required_gap_actions=list(item.get("required_gap_actions", [])),
            required_retrieval_prefix_kinds=[
                SourceKind(value) for value in item.get("required_retrieval_prefix_kinds", [])
            ],
            required_clarification_substring=item.get("required_clarification_substring"),
            required_web_discovery_count=int(item.get("required_web_discovery_count", 0)),
            required_web_discovered_link_count=int(item.get("required_web_discovered_link_count", 0)),
            required_web_fetch_count=int(item.get("required_web_fetch_count", 0)),
            required_web_domains=[str(value).strip() for value in item.get("required_web_domains", []) if str(value).strip()],
            require_provisional_grouping=bool(item.get("require_provisional_grouping", False)),
            require_manual_review_accept=bool(item.get("require_manual_review_accept", False)),
            spawned_validator_gate_eligible=bool(
                item.get("spawned_validator_gate_eligible", False)
            ),
            spawned_validator_release_gate=bool(
                item.get("spawned_validator_release_gate", False)
            ),
            min_gap_records=int(item.get("min_gap_records", 0)),
            min_ledger_entries=int(item.get("min_ledger_entries", 1)),
        )
        for item in payload["scenarios"]
    ]
    seen_scenario_ids: set[str] = set()
    for scenario in scenarios:
        if scenario.scenario_id in seen_scenario_ids:
            raise ValueError(
                f"Evaluation scenarios contain duplicate scenario_id '{scenario.scenario_id}': {path}"
            )
        if (
            scenario.spawned_validator_release_gate
            and not scenario.spawned_validator_gate_eligible
        ):
            raise ValueError(
                "Evaluation scenario marked for spawned-validator release gate must also be "
                f"spawned-validator eligible: {scenario.scenario_id}"
            )
        seen_scenario_ids.add(scenario.scenario_id)
    return scenarios


def load_real_question_pack(path: Path) -> RealQuestionPack:
    payload = _load_json_yaml(path)

    def _expected_concept_candidates(item: dict) -> list[ExpectedConceptCandidate]:
        question_id = item["question_id"].strip()
        raw_candidates = item.get("expected_concept_candidates", [])
        if not isinstance(raw_candidates, list):
            raise ValueError(
                f"Real-question pack question '{question_id}' field 'expected_concept_candidates' must be a list: {path}"
            )
        candidates: list[ExpectedConceptCandidate] = []
        seen_concept_ids: set[str] = set()
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                raise ValueError(
                    f"Real-question pack question '{question_id}' expected_concept_candidates entries must be objects: {path}"
                )
            concept_id = _validate_safe_config_id(
                raw_id=str(raw_candidate["concept_id"]),
                id_label=f"Real-question pack question '{question_id}' expected concept_id",
                path=path,
            )
            if concept_id in seen_concept_ids:
                raise ValueError(
                    f"Real-question pack question '{question_id}' contains duplicate expected concept '{concept_id}': {path}"
                )
            seen_concept_ids.add(concept_id)
            candidates.append(
                ExpectedConceptCandidate(
                    concept_id=concept_id,
                    status=ExpectedConceptStatus(str(raw_candidate["status"])),
                    terms=_stripped_string_list(
                        raw_candidate.get("terms"),
                        field_name=f"expected_concept_candidates.{concept_id}.terms",
                        owner_id=question_id,
                        path=path,
                    ),
                    source_ids=_stripped_string_list(
                        raw_candidate.get("source_ids"),
                        field_name=f"expected_concept_candidates.{concept_id}.source_ids",
                        owner_id=question_id,
                        path=path,
                    ),
                    rationale=_optional_stripped(raw_candidate.get("rationale")),
                )
            )
        return candidates

    questions = [
        RealQuestionPackQuestion(
            question_id=item["question_id"].strip(),
            title=item["title"].strip(),
            question=item["question"].strip(),
            review_focus=item["review_focus"].strip(),
            expected_intent_type=_optional_stripped(item.get("expected_intent_type")),
            min_approved_claims=_non_negative_int(
                item.get("min_approved_claims"),
                field_name="min_approved_claims",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            min_evidence_clusters=_non_negative_int(
                item.get("min_evidence_clusters"),
                field_name="min_evidence_clusters",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            require_claim_verification=_optional_bool(
                item.get("require_claim_verification"),
                field_name="require_claim_verification",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            required_facets=_stripped_string_list(
                item.get("required_facets"),
                field_name="required_facets",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            required_cluster_terms=_stripped_string_list(
                item.get("required_cluster_terms"),
                field_name="required_cluster_terms",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            required_cluster_source_ids=_stripped_string_list(
                item.get("required_cluster_source_ids"),
                field_name="required_cluster_source_ids",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            expected_concept_candidates=_expected_concept_candidates(item),
            forbidden_claim_ids=_stripped_string_list(
                item.get("forbidden_claim_ids"),
                field_name="forbidden_claim_ids",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            tags=_stripped_string_list(
                item.get("tags"),
                field_name="tags",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            review_prompts=_stripped_string_list(
                item.get("review_prompts"),
                field_name="review_prompts",
                owner_id=item["question_id"].strip(),
                path=path,
            ),
            seed_from_scenario_id=_optional_stripped(item.get("seed_from_scenario_id")),
        )
        for item in payload["questions"]
    ]
    if not questions:
        raise ValueError(f"Real-question pack must define at least one question: {path}")

    seen_question_ids: set[str] = set()
    for question in questions:
        _validate_safe_config_id(
            raw_id=question.question_id,
            id_label="Real-question pack question_id",
            path=path,
        )
        if question.question_id in seen_question_ids:
            raise ValueError(
                f"Real-question pack contains duplicate question_id '{question.question_id}': {path}"
            )
        if not question.title:
            raise ValueError(
                f"Real-question pack question '{question.question_id}' is missing a title: {path}"
            )
        if not question.question:
            raise ValueError(
                f"Real-question pack question '{question.question_id}' is missing a question: {path}"
            )
        if not question.review_focus:
            raise ValueError(
                f"Real-question pack question '{question.question_id}' is missing review_focus: {path}"
            )
        if not question.review_prompts:
            raise ValueError(
                f"Real-question pack question '{question.question_id}' must define review_prompts: {path}"
            )
        seen_question_ids.add(question.question_id)

    return RealQuestionPack(questions=questions)


def load_research_profiles(path: Path) -> ResearchProfileConfig:
    payload = _load_json_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Research profiles config must be an object: {path}")
    raw_profiles = payload.get("profiles", [])
    if not isinstance(raw_profiles, list):
        raise ValueError(f"Research profiles config must define a list 'profiles': {path}")
    profiles: list[ResearchProfile] = []
    seen_ids: set[str] = set()
    for raw_profile in raw_profiles:
        if not isinstance(raw_profile, dict):
            raise ValueError(f"Research profile entries must be objects: {path}")
        profile_id = _validate_safe_config_id(
            raw_id=str(raw_profile["profile_id"]),
            id_label="Research profile profile_id",
            path=path,
        )
        if profile_id in seen_ids:
            raise ValueError(f"Research profiles contain duplicate profile_id '{profile_id}': {path}")
        seen_ids.add(profile_id)
        profiles.append(
            ResearchProfile(
                profile_id=profile_id,
                description=str(raw_profile.get("description", "")).strip(),
                concepts=[
                    str(value).strip()
                    for value in raw_profile.get("concepts", [])
                    if str(value).strip()
                ],
                source_roles=[
                    SourceRoleLevel(str(value))
                    for value in raw_profile.get("source_roles", [])
                ],
                claim_types=[
                    ClaimType(str(value))
                    for value in raw_profile.get("claim_types", [])
                ],
                relation_types=[
                    str(value).strip()
                    for value in raw_profile.get("relation_types", [])
                    if str(value).strip()
                ],
                negative_controls=[
                    str(value).strip()
                    for value in raw_profile.get("negative_controls", [])
                    if str(value).strip()
                ],
                preferred_source_kinds=[
                    SourceKind(str(value))
                    for value in raw_profile.get("preferred_source_kinds", [])
                ],
                benchmark_specific_risk=str(
                    raw_profile.get("benchmark_specific_risk", "low")
                ).strip(),
            )
        )
    return ResearchProfileConfig(profiles=profiles)


def configure_logging(runtime_config: RuntimeConfig) -> None:
    level = getattr(logging, runtime_config.logging_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s")
