from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from eubw_researcher.models import (
    BindingLevel,
    CandidateClaimRecord,
    CandidateClaimStatus,
    EvidenceTier,
    OpenIssueRecord,
    RelationGraphEdge,
    RelationReviewStatus,
    SourceCatalog,
    dataclass_to_dict,
)


@dataclass
class LegacyImportReport:
    legacy_root: str
    output_root: str
    chunks_imported: int = 0
    claims_imported: int = 0
    relations_imported: int = 0
    open_issues_imported: int = 0
    benchmark_questions_imported: int = 0
    reference_answers_imported: int = 0
    unresolved_source_ids: list[str] = field(default_factory=list)
    unresolved_locator_claim_ids: list[str] = field(default_factory=list)
    rejected_records: list[str] = field(default_factory=list)


@dataclass
class ImportedKnowledgeAssets:
    candidate_claims: list[CandidateClaimRecord] = field(default_factory=list)
    relation_edges: list[RelationGraphEdge] = field(default_factory=list)
    open_issues: list[OpenIssueRecord] = field(default_factory=list)


def _jsonl_rows(paths: Iterable[Path]):
    for path in paths:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    yield path, line_number, json.loads(stripped)
                except json.JSONDecodeError as exc:
                    yield path, line_number, {"_decode_error": str(exc)}


def _evidence_tier(value: object) -> EvidenceTier:
    try:
        return EvidenceTier(str(value or "unknown"))
    except ValueError:
        return EvidenceTier.UNKNOWN


def _binding_level(value: object) -> BindingLevel:
    try:
        return BindingLevel(str(value or "unknown"))
    except ValueError:
        return BindingLevel.UNKNOWN


def _claim_status(value: object) -> CandidateClaimStatus:
    try:
        status = CandidateClaimStatus(str(value or "candidate"))
    except ValueError:
        return CandidateClaimStatus.CANDIDATE
    if status in {CandidateClaimStatus.APPROVED, CandidateClaimStatus.REVIEWED}:
        return CandidateClaimStatus.CANDIDATE
    return status


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _source_alias_map(catalog: SourceCatalog | None) -> dict[str, str]:
    aliases: dict[str, str] = {}
    if catalog is None:
        return aliases
    for entry in catalog.entries:
        aliases[entry.source_id] = entry.source_id
        if entry.archive_source_id:
            aliases[entry.archive_source_id] = entry.source_id
        for legacy_source_id in entry.legacy_source_ids:
            aliases[legacy_source_id] = entry.source_id
    return aliases


def _map_source_ids(
    source_ids: list[str],
    *,
    source_aliases: dict[str, str],
    report: LegacyImportReport,
) -> list[str]:
    if not source_aliases:
        return source_ids
    mapped: list[str] = []
    for source_id in source_ids:
        mapped_source_id = source_aliases.get(source_id)
        if mapped_source_id is None:
            report.unresolved_source_ids.append(source_id)
            continue
        mapped.append(mapped_source_id)
    return sorted(set(mapped))


def _locator_list(row: dict) -> list[str]:
    locators = _string_list(row.get("article_refs", []))
    if locators:
        return locators
    article_ref = row.get("article_ref")
    if article_ref:
        return _string_list(article_ref)
    locator = row.get("locator")
    if isinstance(locator, dict):
        return [json.dumps(locator, ensure_ascii=False, sort_keys=True)]
    return _string_list(locator)


def import_legacy_knowledge(
    legacy_root: Path,
    output_root: Path,
    *,
    catalog: SourceCatalog | None = None,
) -> LegacyImportReport:
    legacy_root = legacy_root.resolve()
    output_root = output_root.resolve()
    if not legacy_root.exists():
        raise FileNotFoundError(f"Legacy knowledge root not found: {legacy_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    source_aliases = _source_alias_map(catalog)
    known_source_ids = set(source_aliases) if source_aliases else set()
    report = LegacyImportReport(
        legacy_root=str(legacy_root),
        output_root=str(output_root),
    )

    chunks = _load_chunks(legacy_root, report, known_source_ids, source_aliases)
    claims: list[CandidateClaimRecord] = []
    claim_paths = sorted((legacy_root / "claims").glob("*claims_draft.jsonl"))
    claim_paths.extend(sorted((legacy_root / "claims").glob("*claim_candidates.jsonl")))
    seen_claim_ids: set[str] = set()
    for path, line_number, row in _jsonl_rows(claim_paths):
        if "_decode_error" in row:
            report.rejected_records.append(f"{path}:{line_number}:json:{row['_decode_error']}")
            continue
        claim_id = str(row.get("claim_id") or row.get("candidate_id") or "").strip()
        statement = str(
            row.get("statement")
            or row.get("normalized_statement")
            or row.get("seed_statement")
            or row.get("quote_snippet")
            or ""
        ).strip()
        if not claim_id or not statement or claim_id in seen_claim_ids:
            report.rejected_records.append(f"{path}:{line_number}:missing_or_duplicate_claim")
            continue
        seen_claim_ids.add(claim_id)
        source_ids = _string_list(row.get("source_ids", []))
        if not source_ids and row.get("source_id"):
            source_ids = _string_list(row.get("source_id"))
        source_ids = _map_source_ids(
            source_ids,
            source_aliases=source_aliases,
            report=report,
        )
        chunk_ids = _string_list(row.get("chunk_ids", []))
        if known_source_ids:
            source_ids = [source_id for source_id in source_ids if source_id]
        if not chunk_ids:
            report.unresolved_locator_claim_ids.append(claim_id)
        claims.append(
            CandidateClaimRecord(
                claim_id=claim_id,
                normalized_statement=statement,
                source_ids=source_ids,
                chunk_ids=chunk_ids,
                locators=_locator_list(row),
                topic=path.stem.replace("_claims_draft", "").replace("_claim_candidates", ""),
                actor=row.get("actor"),
                action=row.get("action"),
                object=row.get("object"),
                modality=row.get("modality"),
                evidence_tier=_evidence_tier(row.get("evidence_tier")),
                binding_level=_binding_level(row.get("binding_level")),
                status=_claim_status(row.get("status")),
                extraction_provenance=f"{path.name}:{line_number}",
            )
        )

    relations: list[RelationGraphEdge] = []
    for path, line_number, row in _jsonl_rows(sorted((legacy_root / "relations").glob("*.jsonl"))):
        if "_decode_error" in row:
            report.rejected_records.append(f"{path}:{line_number}:json:{row['_decode_error']}")
            continue
        relation_id = str(row.get("relation_id", "")).strip()
        from_claim_id = str(row.get("from_claim_id", "")).strip()
        to_claim_id = str(row.get("to_claim_id", "")).strip()
        if not relation_id or not from_claim_id or not to_claim_id:
            report.rejected_records.append(f"{path}:{line_number}:missing_relation_fields")
            continue
        relations.append(
            RelationGraphEdge(
                edge_id=relation_id,
                relation_type=str(row.get("relation_type") or "related_to"),
                source_id=from_claim_id,
                target_id=to_claim_id,
                confidence=float(row.get("confidence", 0.0)),
                review_status=RelationReviewStatus.SUPPLEMENTAL,
                evidence_source_ids=_map_source_ids(
                    _string_list(row.get("source_ids", [])),
                    source_aliases=source_aliases,
                    report=report,
                ),
            )
        )

    open_issues = _load_open_issues(legacy_root)
    benchmark_questions = _load_benchmark_questions(legacy_root, report)
    reference_answers = _load_reference_answers(legacy_root, report)

    report.chunks_imported = len(chunks)
    report.claims_imported = len(claims)
    report.relations_imported = len(relations)
    report.open_issues_imported = len(open_issues)
    report.benchmark_questions_imported = len(benchmark_questions)
    report.reference_answers_imported = len(reference_answers)
    report.unresolved_source_ids = sorted(set(report.unresolved_source_ids))
    report.unresolved_locator_claim_ids = sorted(set(report.unresolved_locator_claim_ids))

    _write_json(output_root / "chunks.json", chunks)
    _write_json(output_root / "candidate_claims.json", claims)
    _write_json(output_root / "relation_graph_slice.json", relations)
    _write_json(output_root / "open_issues.json", open_issues)
    _write_json(output_root / "benchmark_questions.json", benchmark_questions)
    _write_json(output_root / "reference_answers.json", reference_answers)
    _write_json(output_root / "import_report.json", report)
    return report


def _load_chunks(
    legacy_root: Path,
    report: LegacyImportReport,
    known_source_ids: set[str],
    source_aliases: dict[str, str],
) -> list[dict]:
    records: list[dict] = []
    seen_chunk_ids: set[str] = set()
    for path, line_number, row in _jsonl_rows(sorted((legacy_root / "chunks").glob("*.jsonl"))):
        if "_decode_error" in row:
            report.rejected_records.append(f"{path}:{line_number}:json:{row['_decode_error']}")
            continue
        chunk_id = str(row.get("chunk_id", "")).strip()
        source_id = str(row.get("source_id", "")).strip()
        text = str(row.get("text", "")).strip()
        if not chunk_id or not source_id or not text or chunk_id in seen_chunk_ids:
            report.rejected_records.append(f"{path}:{line_number}:missing_or_duplicate_chunk")
            continue
        seen_chunk_ids.add(chunk_id)
        mapped_source_id = source_aliases.get(source_id, source_id)
        if known_source_ids and source_id not in known_source_ids:
            report.unresolved_source_ids.append(source_id)
        records.append(
            {
                "chunk_id": chunk_id,
                "source_id": mapped_source_id,
                "locator": row.get("locator"),
                "text": text,
                "evidence_tier": str(row.get("evidence_tier", "unknown")),
                "binding_level": str(row.get("binding_level", "unknown")),
                "source_url": row.get("source_url"),
                "local_path": row.get("local_path"),
                "text_sha256": row.get("text_sha256"),
                "extraction_provenance": f"{path.name}:{line_number}",
            }
        )
    return records


def _load_benchmark_questions(
    legacy_root: Path,
    report: LegacyImportReport,
) -> list[dict]:
    records: list[dict] = []
    seen_case_ids: set[str] = set()
    for path, line_number, row in _jsonl_rows(sorted((legacy_root / "benchmarks").glob("*.jsonl"))):
        if "_decode_error" in row:
            report.rejected_records.append(f"{path}:{line_number}:json:{row['_decode_error']}")
            continue
        case_id = str(row.get("case_id") or row.get("question_id") or "").strip()
        question = str(row.get("question", "")).strip()
        if not case_id or not question or case_id in seen_case_ids:
            report.rejected_records.append(f"{path}:{line_number}:missing_or_duplicate_benchmark")
            continue
        seen_case_ids.add(case_id)
        records.append(
            {
                "case_id": case_id,
                "question": question,
                "profile": row.get("profile"),
                "topics": _string_list(row.get("topics", [])),
                "expected_source_ids": _string_list(row.get("expected_source_ids", [])),
                "expected_primary_cites": _string_list(row.get("expected_primary_cites", [])),
                "migration_status": "reference_only",
                "extraction_provenance": f"{path.name}:{line_number}",
            }
        )
    return records


def _load_open_issues(legacy_root: Path) -> list[OpenIssueRecord]:
    issue_paths = sorted((legacy_root / "open_issues").glob("*.jsonl"))
    records: list[OpenIssueRecord] = []
    for path, line_number, row in _jsonl_rows(issue_paths):
        if "_decode_error" in row:
            continue
        issue_id = str(row.get("issue_id") or f"legacy_issue_{len(records) + 1}").strip()
        statement = str(row.get("issue_statement") or row.get("statement") or "").strip()
        if not statement:
            continue
        records.append(
            OpenIssueRecord(
                issue_id=issue_id,
                issue_statement=statement,
                reason_open=str(row.get("reason_open") or row.get("reason") or "Imported legacy open issue."),
                bounded_by_evidence=_string_list(row.get("bounded_by_evidence", row.get("source_ids", []))),
                affected_claim_ids=_string_list(row.get("affected_claim_ids", row.get("claim_ids", []))),
                affected_source_ids=_string_list(row.get("affected_source_ids", row.get("source_ids", []))),
                severity=str(row.get("severity", "medium")),
                answer_impact=str(row.get("answer_impact", "qualifies_answer")),
                review_owner=row.get("review_owner"),
                status=str(row.get("status", "open")),
                last_reviewed_date=row.get("last_reviewed_date"),
            )
        )
    return records


def _load_reference_answers(
    legacy_root: Path,
    report: LegacyImportReport,
) -> list[dict]:
    records: list[dict] = []
    seen_answer_ids: set[str] = set()
    for path in sorted((legacy_root / "answers").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            report.rejected_records.append(f"{path}:json:{exc}")
            continue
        answer_id = str(row.get("answer_id") or row.get("id") or path.stem).strip()
        if not answer_id or answer_id in seen_answer_ids:
            report.rejected_records.append(f"{path}:missing_or_duplicate_answer")
            continue
        seen_answer_ids.add(answer_id)
        records.append(
            {
                "answer_id": answer_id,
                "question": row.get("question"),
                "profile": row.get("profile"),
                "source_ids": _string_list(row.get("source_ids", [])),
                "claim_ids": _string_list(row.get("claim_ids", [])),
                "reference_only": True,
                "extraction_provenance": path.name,
            }
        )
    return records


def load_imported_knowledge_assets(output_root: Path) -> ImportedKnowledgeAssets:
    if not output_root.exists():
        return ImportedKnowledgeAssets()

    candidate_claims: list[CandidateClaimRecord] = []
    claims_path = output_root / "candidate_claims.json"
    if claims_path.exists():
        for item in json.loads(claims_path.read_text(encoding="utf-8")):
            candidate_claims.append(
                CandidateClaimRecord(
                    claim_id=str(item["claim_id"]),
                    normalized_statement=str(item["normalized_statement"]),
                    source_ids=_string_list(item.get("source_ids", [])),
                    chunk_ids=_string_list(item.get("chunk_ids", [])),
                    locators=_string_list(item.get("locators", [])),
                    topic=item.get("topic"),
                    actor=item.get("actor"),
                    action=item.get("action"),
                    object=item.get("object"),
                    modality=item.get("modality"),
                    evidence_tier=_evidence_tier(item.get("evidence_tier")),
                    binding_level=_binding_level(item.get("binding_level")),
                    status=_claim_status(item.get("status")),
                    extraction_provenance=item.get("extraction_provenance"),
                )
            )

    relation_edges: list[RelationGraphEdge] = []
    relations_path = output_root / "relation_graph_slice.json"
    if relations_path.exists():
        for item in json.loads(relations_path.read_text(encoding="utf-8")):
            relation_edges.append(
                RelationGraphEdge(
                    edge_id=str(item["edge_id"]),
                    relation_type=str(item.get("relation_type") or "related_to"),
                    source_id=str(item["source_id"]),
                    target_id=str(item["target_id"]),
                    confidence=float(item.get("confidence", 0.0)),
                    review_status=RelationReviewStatus(
                        item.get("review_status", RelationReviewStatus.SUPPLEMENTAL.value)
                    ),
                    evidence_source_ids=_string_list(item.get("evidence_source_ids", [])),
                )
            )

    open_issues: list[OpenIssueRecord] = []
    issues_path = output_root / "open_issues.json"
    if issues_path.exists():
        for item in json.loads(issues_path.read_text(encoding="utf-8")):
            open_issues.append(
                OpenIssueRecord(
                    issue_id=str(item["issue_id"]),
                    issue_statement=str(item["issue_statement"]),
                    reason_open=str(item["reason_open"]),
                    bounded_by_evidence=_string_list(item.get("bounded_by_evidence", [])),
                    affected_concept_ids=_string_list(item.get("affected_concept_ids", [])),
                    affected_claim_ids=_string_list(item.get("affected_claim_ids", [])),
                    affected_source_ids=_string_list(item.get("affected_source_ids", [])),
                    affected_answer_facets=_string_list(item.get("affected_answer_facets", [])),
                    severity=str(item.get("severity", "medium")),
                    answer_impact=str(item.get("answer_impact", "qualifies_answer")),
                    blocks_claim_ids=_string_list(item.get("blocks_claim_ids", [])),
                    qualifies_claim_ids=_string_list(item.get("qualifies_claim_ids", [])),
                    resolution_condition=item.get("resolution_condition"),
                    review_owner=item.get("review_owner"),
                    status=str(item.get("status", "open")),
                    last_reviewed_date=item.get("last_reviewed_date"),
                )
            )

    return ImportedKnowledgeAssets(
        candidate_claims=candidate_claims,
        relation_edges=relation_edges,
        open_issues=open_issues,
    )


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(dataclass_to_dict(value), indent=2), encoding="utf-8")
