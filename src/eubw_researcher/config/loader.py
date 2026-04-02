from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from eubw_researcher.models import (
    ArchiveCorpusConfig,
    ArchiveSourceSelection,
    ClaimState,
    EvaluationScenario,
    RealQuestionPack,
    RealQuestionPackQuestion,
    HierarchyRule,
    RuntimeConfig,
    SourceHierarchyConfig,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    WebDomainPolicy,
    WebAllowlistConfig,
)


def _load_json_yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base_dir / path).resolve()


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


def load_web_allowlist(path: Path) -> WebAllowlistConfig:
    payload = _load_json_yaml(path)
    domain_policies = [
        WebDomainPolicy(
            domain=item["domain"],
            source_kind=SourceKind(item["source_kind"]),
            source_role_level=SourceRoleLevel(item["source_role_level"]),
            jurisdiction=item["jurisdiction"],
            seed_urls=list(item.get("seed_urls", [])),
            discovery_urls=list(item.get("discovery_urls", [])),
            allowed_path_prefixes=list(item.get("allowed_path_prefixes", [])),
            blocked_url_keywords=list(item.get("blocked_url_keywords", [])),
            allowed_cross_domain_domains=list(item.get("allowed_cross_domain_domains", [])),
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
                source_origin=SourceOrigin(item.get("source_origin", "local")),
                anchorability_hints=list(item.get("anchorability_hints", [])),
                admission_reason=item.get("admission_reason"),
            )
            for item in payload["sources"]
        ],
    )


def load_runtime_config(path: Path) -> RuntimeConfig:
    payload = _load_json_yaml(path)
    retrieval = payload["retrieval"]
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
    )


def load_evaluation_scenarios(path: Path) -> List[EvaluationScenario]:
    payload = _load_json_yaml(path)
    return [
        EvaluationScenario(
            scenario_id=item["scenario_id"],
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
            required_web_fetch_count=int(item.get("required_web_fetch_count", 0)),
            require_provisional_grouping=bool(item.get("require_provisional_grouping", False)),
            require_manual_review_accept=bool(item.get("require_manual_review_accept", False)),
            min_gap_records=int(item.get("min_gap_records", 0)),
            min_ledger_entries=int(item.get("min_ledger_entries", 1)),
        )
        for item in payload["scenarios"]
    ]


def load_real_question_pack(path: Path) -> RealQuestionPack:
    payload = _load_json_yaml(path)
    questions = [
        RealQuestionPackQuestion(
            question_id=item["question_id"].strip(),
            title=item["title"].strip(),
            question=item["question"].strip(),
            review_focus=item["review_focus"].strip(),
            expected_intent_type=item.get("expected_intent_type"),
            tags=[tag.strip() for tag in item.get("tags", []) if tag.strip()],
            review_prompts=[
                prompt.strip() for prompt in item.get("review_prompts", []) if prompt.strip()
            ],
            seed_from_scenario_id=item.get("seed_from_scenario_id"),
        )
        for item in payload["questions"]
    ]
    if not questions:
        raise ValueError(f"Real-question pack must define at least one question: {path}")

    seen_question_ids: set[str] = set()
    for question in questions:
        if not question.question_id:
            raise ValueError(f"Real-question pack contains a blank question_id: {path}")
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


def configure_logging(runtime_config: RuntimeConfig) -> None:
    level = getattr(logging, runtime_config.logging_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s")
