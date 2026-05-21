from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from eubw_researcher.answering import supports_relation_hints
from eubw_researcher import ResearchRuntimeFacade
from eubw_researcher.config import (
    load_real_question_pack,
    load_runtime_config,
    runtime_config_digest,
)
from eubw_researcher.corpus import is_real_corpus_catalog
from eubw_researcher.evaluation.review import (
    build_manual_review_artifact,
    build_manual_review_report,
    build_manual_review_report_markdown,
)
from eubw_researcher.evaluation.git_metadata import collect_git_metadata
from eubw_researcher.evaluation.runner import write_artifact_bundle
from eubw_researcher.models import (
    ExpectedConceptStatus,
    ManualReviewArtifact,
    RealQuestionPack,
    RealQuestionPackQuestion,
    RealQuestionPackQuestionRunSummary,
    RealQuestionPackRunManifest,
    RealQuestionPackRunTriageSummary,
    ScenarioVerdict,
    dataclass_to_dict,
)

PathLike = Union[str, Path]

DEFAULT_PACK_PATH = Path("configs/real_question_pack.yaml")
DEFAULT_ENTRYPOINT = "scripts/run_real_question_pack.py"
REQUIRED_BUNDLE_ARTIFACTS = [
    "retrieval_plan.json",
    "gap_records.json",
    "web_fetch_records.json",
    "ingestion_report.json",
    "ledger_entries.json",
    "approved_ledger.json",
    "final_answer.txt",
    "pinpoint_evidence.json",
    "answer_alignment.json",
    "blind_validation_report.json",
    "manual_review.json",
    "manual_review_report.md",
]
OPTIONAL_BUNDLE_ARTIFACTS = [
    "provisional_grouping.json",
    "facet_coverage.json",
    "relation_hints.json",
    "evidence_clusters.json",
    "selected_evidence.json",
    "claim_verification.json",
    "relation_graph_slice.json",
    "open_issues.json",
    "navigation_session_trace.json",
    "source_hierarchy_report.json",
    "research_profile_trace.json",
    "reading_plan.json",
    "opened_passages.json",
    "evidence_synthesis_matrix.json",
    "corpus_coverage_report.json",
    "verdict.json",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_real_question_pack_output_dir(
    repo_root: Path,
    *,
    run_id: Optional[str] = None,
) -> Path:
    resolved_run_id = run_id or _utcnow().strftime("%Y%m%dT%H%M%SZ")
    return repo_root / "artifacts" / "real_question_pack_runs" / resolved_run_id


def run_real_question_pack(
    repo_root: PathLike,
    *,
    pack_path: Optional[PathLike] = None,
    question_id: Optional[str] = None,
    catalog_path: Optional[PathLike] = None,
    output_dir: Optional[PathLike] = None,
    runtime_config_path: Optional[PathLike] = None,
) -> tuple[Path, RealQuestionPackRunManifest]:
    resolved_repo_root = Path(repo_root).resolve()
    resolved_pack_path = _resolve_path(
        resolved_repo_root,
        pack_path or DEFAULT_PACK_PATH,
    )
    pack = load_real_question_pack(resolved_pack_path)
    selected_questions = _select_questions(pack, question_id)
    # Capture baseline provenance before default run output creation or cache writes can
    # dirty an otherwise clean repository and falsely report the run as starting dirty.
    git_metadata = _git_metadata(resolved_repo_root)

    run_root = (
        _resolve_path(resolved_repo_root, output_dir)
        if output_dir is not None
        else default_real_question_pack_output_dir(resolved_repo_root)
    )
    _validate_run_root(resolved_repo_root, run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    resolved_runtime_config_path = _resolve_runtime_config_path(
        resolved_repo_root,
        runtime_config_path,
    )
    runtime_config = load_runtime_config(resolved_runtime_config_path)

    facade = ResearchRuntimeFacade(resolved_repo_root)
    pack_digest = hashlib.sha256(resolved_pack_path.read_bytes()).hexdigest()

    question_runs = []
    runtime_contract_version: Optional[str] = None
    resolved_catalog_path: Optional[Path] = None
    corpus_state_id: Optional[str] = None

    for question in selected_questions:
        question_output_dir = run_root / question.question_id
        _prepare_question_output_dir(question_output_dir)
        response = facade.run_evidence_only(
            question.question,
            catalog_path=catalog_path,
            runtime_config_path=resolved_runtime_config_path,
        )
        expected_artifacts = _expected_bundle_artifacts(
            response.result,
            response.catalog_path,
        )
        review_artifact = build_manual_review_artifact(
            response.result,
            scenario_id=question.question_id,
        )
        verdict = _build_question_verdict(
            question,
            response.result,
            review_artifact=review_artifact,
        )
        report = build_manual_review_report(
            response.result,
            verdict,
            scenario_id=question.question_id,
            catalog_path=str(response.catalog_path),
            corpus_state_id=response.corpus_state_id,
        )
        write_artifact_bundle(
            question_output_dir,
            response.result,
            verdict=verdict,
            scenario_id=question.question_id,
            catalog_path=response.catalog_path,
            corpus_state_id=response.corpus_state_id,
            manual_review_report=report,
            manual_review_artifact=review_artifact,
        )
        actual_artifacts = sorted(
            path.name for path in question_output_dir.iterdir() if path.is_file()
        )
        missing_artifacts = [
            artifact for artifact in expected_artifacts if artifact not in actual_artifacts
        ]
        if missing_artifacts:
            verdict = _build_question_verdict(
                question,
                response.result,
                missing_artifacts=missing_artifacts,
                review_artifact=review_artifact,
            )
            report = build_manual_review_report(
                response.result,
                verdict,
                scenario_id=question.question_id,
                catalog_path=str(response.catalog_path),
                corpus_state_id=response.corpus_state_id,
            )
            (question_output_dir / "verdict.json").write_text(
                json.dumps(dataclass_to_dict(verdict), indent=2),
                encoding="utf-8",
            )
            (question_output_dir / "manual_review_report.md").write_text(
                build_manual_review_report_markdown(report),
                encoding="utf-8",
            )
        actual_artifacts = sorted(
            path.name for path in question_output_dir.iterdir() if path.is_file()
        )
        missing_artifacts = [
            artifact for artifact in expected_artifacts if artifact not in actual_artifacts
        ]
        discovery_record_count = sum(
            1
            for record in response.result.web_fetch_records
            if getattr(record, "record_type", None) == "discovery"
        )
        fetch_record_count = sum(
            1
            for record in response.result.web_fetch_records
            if getattr(record, "record_type", None) == "fetch"
        )
        question_runs.append(
            RealQuestionPackQuestionRunSummary(
                question_id=question.question_id,
                title=question.title,
                review_focus=question.review_focus,
                expected_intent_type=question.expected_intent_type,
                linked_scenario_id=question.seed_from_scenario_id,
                tags=list(question.tags),
                output_dir=str(question_output_dir.resolve()),
                artifacts_present=actual_artifacts,
                missing_artifacts=missing_artifacts,
                has_missing_artifacts=bool(missing_artifacts),
                intent_type=response.result.query_intent.intent_type,
                approved_entry_count=len(response.result.approved_entries),
                gap_record_count=len(response.result.gap_records),
                discovery_record_count=discovery_record_count,
                web_fetch_count=fetch_record_count,
                used_official_web_discovery=bool(discovery_record_count),
                local_corpus_only=not discovery_record_count and not fetch_record_count,
                final_judgment=report.final_judgment,
                usefulness_verdict=report.usefulness_verdict,
                source_bound_verdict=report.source_bound_verdict,
                pinpoint_traceability_verdict=report.pinpoint_traceability_verdict,
                product_output_self_sufficiency_verdict=(
                    report.product_output_self_sufficiency_verdict
                ),
                review_complete=False,
            )
        )
        runtime_contract_version = _stable_value(
            runtime_contract_version,
            response.contract_version,
            "runtime_contract_version",
        )
        resolved_catalog_path = _stable_value(
            resolved_catalog_path,
            response.catalog_path.resolve(),
            "catalog_path",
        )
        corpus_state_id = _stable_value(
            corpus_state_id,
            response.corpus_state_id,
            "corpus_state_id",
        )

    assert runtime_contract_version is not None
    assert resolved_catalog_path is not None
    assert corpus_state_id is not None
    repo_local_artifacts_written = _run_writes_repo_local_artifacts(
        run_root,
        resolved_catalog_path,
        resolved_repo_root,
    )

    run_triage_summary = RealQuestionPackRunTriageSummary(
        total_questions=len(question_runs),
        accepted_question_ids=[
            run.question_id for run in question_runs if run.final_judgment == "accept"
        ],
        rejected_question_ids=[
            run.question_id for run in question_runs if run.final_judgment != "accept"
        ],
        question_ids_with_discovery=[
            run.question_id for run in question_runs if run.used_official_web_discovery
        ],
        question_ids_with_fetch=[
            run.question_id for run in question_runs if run.web_fetch_count
        ],
        question_ids_with_missing_artifacts=[
            run.question_id for run in question_runs if run.has_missing_artifacts
        ],
    )

    manifest = RealQuestionPackRunManifest(
        run_id=run_root.name,
        run_timestamp=_utcnow().isoformat(),
        pack_path=str(resolved_pack_path),
        pack_digest=pack_digest,
        selected_question_ids=[question.question_id for question in selected_questions],
        catalog_path=str(resolved_catalog_path),
        corpus_state_id=corpus_state_id,
        runtime_contract_version=runtime_contract_version,
        runtime_config_path=str(resolved_runtime_config_path),
        runtime_config_digest=runtime_config_digest(resolved_runtime_config_path),
        local_retrieval_backend=runtime_config.local_retrieval_backend,
        entrypoint=DEFAULT_ENTRYPOINT,
        git_commit=git_metadata["commit"],
        git_branch=git_metadata["branch"],
        git_dirty=git_metadata["dirty"],
        repo_local_artifacts_written=repo_local_artifacts_written,
        run_triage_summary=run_triage_summary,
        question_runs=question_runs,
    )
    (run_root / "pack_run_manifest.json").write_text(
        json.dumps(dataclass_to_dict(manifest), indent=2),
        encoding="utf-8",
    )
    return run_root, manifest


def _select_questions(
    pack: RealQuestionPack,
    question_id: Optional[str],
) -> list[RealQuestionPackQuestion]:
    if question_id is None:
        return list(pack.questions)
    matches = [question for question in pack.questions if question.question_id == question_id]
    if not matches:
        raise ValueError(f"Unknown real-question pack question_id: {question_id}")
    return matches


def _resolve_path(repo_root: Path, value: PathLike) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _resolve_runtime_config_path(
    repo_root: Path,
    runtime_config_path: Optional[PathLike],
) -> Path:
    resolved_path = _resolve_path(
        repo_root,
        runtime_config_path or Path("configs/runtime.yaml"),
    )
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Runtime config file not found: {resolved_path}")
    return resolved_path


def _validate_run_root(repo_root: Path, run_root: Path) -> None:
    if run_root == repo_root:
        raise ValueError("Real-question pack output_dir must not resolve to the repository root")
    if run_root.exists() and not run_root.is_dir():
        raise ValueError(f"Real-question pack output_dir must be a directory path: {run_root}")


def _run_writes_repo_local_artifacts(run_root: Path, catalog_path: Path, repo_root: Path) -> bool:
    """Return whether a pack run writes repo-local output directories or real-corpus cache files."""
    return _is_within_root(run_root, repo_root) or _writes_repo_local_real_corpus_cache(
        catalog_path,
        repo_root,
    )


def _writes_repo_local_real_corpus_cache(catalog_path: Path, repo_root: Path) -> bool:
    if not is_real_corpus_catalog(catalog_path):
        return False
    return _is_within_root(catalog_path.parent / "cache", repo_root)


def _is_within_root(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
        return True
    except ValueError:
        return False


def _prepare_question_output_dir(question_output_dir: Path) -> None:
    if question_output_dir.exists() and not question_output_dir.is_dir():
        raise ValueError(
            f"Real-question output path must be a directory: {question_output_dir}"
        )
    question_output_dir.mkdir(parents=True, exist_ok=True)
    for artifact_name in [*REQUIRED_BUNDLE_ARTIFACTS, *OPTIONAL_BUNDLE_ARTIFACTS]:
        artifact_path = question_output_dir / artifact_name
        if artifact_path.exists() and artifact_path.is_file():
            artifact_path.unlink()


def _approved_claim_ids(result) -> set[str]:
    return {
        claim_id
        for claim_id in (
            getattr(entry, "claim_id", None)
            for entry in getattr(result, "approved_entries", [])
        )
        if isinstance(claim_id, str) and claim_id
    }


def _surfaced_requirement_keys(result) -> set[str]:
    surfaced: set[str] = set()
    for claim_id in _approved_claim_ids(result):
        surfaced.add(claim_id)
        surfaced.add(claim_id.casefold())

    for group in getattr(result, "provisional_grouping", []) or []:
        label = getattr(group, "label", None)
        if isinstance(label, str) and label:
            surfaced.add(label)
            surfaced.add(label.casefold())
        for claim_id in getattr(group, "claim_ids", []) or []:
            if isinstance(claim_id, str) and claim_id:
                surfaced.add(claim_id)
                surfaced.add(claim_id.casefold())

    facet_report = getattr(result, "facet_coverage_report", None)
    if facet_report is not None:
        for facet in getattr(facet_report, "facets", []) or []:
            if not getattr(facet, "addressed", False):
                continue
            facet_id = getattr(facet, "facet_id", None)
            if isinstance(facet_id, str) and facet_id:
                surfaced.add(facet_id)
                surfaced.add(facet_id.casefold())
            for evidence in getattr(facet, "evidence", []) or []:
                if isinstance(evidence, str) and evidence:
                    surfaced.add(evidence)
                    surfaced.add(evidence.casefold())

    return surfaced


def _required_facet_satisfied(result, required_facet: str) -> bool:
    normalized = required_facet.casefold()
    surfaced = _surfaced_requirement_keys(result)
    if required_facet in surfaced or normalized in surfaced:
        return True

    rendered_answer = getattr(result, "rendered_answer", "")
    if isinstance(rendered_answer, str) and normalized in rendered_answer.casefold():
        return True

    facet_report = getattr(result, "facet_coverage_report", None)
    if facet_report is None:
        return False
    facet_by_id = getattr(facet_report, "by_id", lambda: {})()
    facet = facet_by_id.get(required_facet)
    if facet is not None and getattr(facet, "addressed", False):
        return True
    return False


def _cluster_text_surface(result) -> str:
    parts: list[str] = []
    for cluster in getattr(result, "evidence_clusters", []) or []:
        parts.append(str(getattr(cluster, "cluster_id", "")))
        parts.append(str(getattr(cluster, "label", "")))
        parts.extend(str(item) for item in getattr(cluster, "matched_concepts", []) or [])
        parts.extend(str(item) for item in getattr(cluster, "candidate_claim_ids", []) or [])
        parts.extend(str(item) for item in getattr(cluster, "source_ids", []) or [])
        for record in getattr(cluster, "records", []) or []:
            parts.append(str(getattr(record, "source_id", "")))
            parts.append(str(getattr(record, "chunk_id", "")))
            parts.append(str(getattr(record, "locator", "") or ""))
            parts.append(str(getattr(record, "snippet", "")))
    return "\n".join(parts).casefold()


def _result_text_surface(result) -> str:
    parts = [_cluster_text_surface(result), str(getattr(result, "rendered_answer", ""))]
    for gap in getattr(result, "gap_records", []) or []:
        parts.append(str(getattr(gap, "sub_question", "")))
        parts.append(str(getattr(gap, "reason_local_evidence_insufficient", "")))
        parts.append(str(getattr(gap, "next_allowed_action", "")))
    for record in getattr(result, "claim_verification", []) or []:
        parts.append(str(getattr(record, "claim_id", "")))
        parts.append(str(getattr(record, "decision_reason", "")))
        parts.extend(str(item) for item in getattr(record, "source_ids", []) or [])
        parts.extend(str(item) for item in getattr(record, "locators", []) or [])
    matrix = getattr(result, "evidence_synthesis_matrix", None)
    if matrix is not None:
        for record in getattr(matrix, "records", []) or []:
            parts.append(str(getattr(record, "statement", "")))
            parts.extend(str(item) for item in getattr(record, "source_ids", []) or [])
            parts.extend(str(item) for item in getattr(record, "caveats", []) or [])
    return "\n".join(parts).casefold()


def _expected_concept_satisfied(result, concept_candidate) -> bool:
    surface = _result_text_surface(result)
    terms = list(getattr(concept_candidate, "terms", []) or [])
    if not terms:
        terms = [getattr(concept_candidate, "concept_id", "")]
    term_hit = any(str(term).casefold() in surface for term in terms if str(term).strip())
    source_ids = list(getattr(concept_candidate, "source_ids", []) or [])
    if not source_ids:
        return term_hit
    surfaced_sources = _cluster_source_ids(result)
    surfaced_sources.update(
        citation.source_id
        for entry in getattr(result, "ledger_entries", []) or []
        for citation in getattr(entry, "citations", []) or []
    )
    return term_hit and any(source_id in surfaced_sources for source_id in source_ids)


def _cluster_source_ids(result) -> set[str]:
    source_ids: set[str] = set()
    for cluster in getattr(result, "evidence_clusters", []) or []:
        source_ids.update(str(item) for item in getattr(cluster, "source_ids", []) or [])
        for record in getattr(cluster, "records", []) or []:
            source_id = getattr(record, "source_id", None)
            if source_id:
                source_ids.add(str(source_id))
    return source_ids


def _build_question_verdict(
    question: RealQuestionPackQuestion,
    result,
    missing_artifacts: Optional[list[str]] = None,
    review_artifact: Optional[ManualReviewArtifact] = None,
) -> ScenarioVerdict:
    checks: list[str] = []
    passed = True

    if question.expected_intent_type:
        actual_intent_type = result.query_intent.intent_type
        if actual_intent_type == question.expected_intent_type:
            checks.append(f"intent_type:{question.expected_intent_type}:ok")
        else:
            checks.append(
                "intent_type:"
                f"{question.expected_intent_type}:fail:{actual_intent_type}"
            )
            passed = False
    else:
        checks.append("intent_type:not_specified")

    min_approved_claims = getattr(question, "min_approved_claims", 0)
    if min_approved_claims:
        approved_count = len(result.approved_entries)
        if approved_count >= min_approved_claims:
            checks.append(f"approved_claims:min:{min_approved_claims}:ok:{approved_count}")
        else:
            checks.append(
                f"approved_claims:min:{min_approved_claims}:fail:{approved_count}"
            )
            passed = False

    min_evidence_clusters = getattr(question, "min_evidence_clusters", 0)
    if min_evidence_clusters:
        cluster_count = len(getattr(result, "evidence_clusters", []) or [])
        if cluster_count >= min_evidence_clusters:
            checks.append(
                f"evidence_clusters:min:{min_evidence_clusters}:ok:{cluster_count}"
            )
        else:
            checks.append(
                f"evidence_clusters:min:{min_evidence_clusters}:fail:{cluster_count}"
            )
            passed = False

    if getattr(question, "require_claim_verification", False):
        verification_count = len(getattr(result, "claim_verification", []) or [])
        if verification_count:
            checks.append(f"claim_verification:present:ok:{verification_count}")
        else:
            checks.append("claim_verification:present:fail:0")
            passed = False

    approved_claim_ids = _approved_claim_ids(result)
    forbidden_claim_ids = set(getattr(question, "forbidden_claim_ids", []) or [])
    if forbidden_claim_ids:
        forbidden_present = sorted(approved_claim_ids & forbidden_claim_ids)
        if forbidden_present:
            checks.append("forbidden_claim_ids:fail:" + ",".join(forbidden_present))
            passed = False
        else:
            checks.append("forbidden_claim_ids:none:ok")

    for required_facet in getattr(question, "required_facets", []) or []:
        if _required_facet_satisfied(result, required_facet):
            checks.append(f"required_facet:{required_facet}:ok")
        else:
            checks.append(f"required_facet:{required_facet}:fail")
            passed = False

    cluster_surface = _cluster_text_surface(result)
    for required_cluster_term in getattr(question, "required_cluster_terms", []) or []:
        normalized = required_cluster_term.casefold()
        if normalized in cluster_surface:
            checks.append(f"required_cluster_term:{required_cluster_term}:ok")
        else:
            checks.append(f"required_cluster_term:{required_cluster_term}:fail")
            passed = False

    surfaced_cluster_source_ids = _cluster_source_ids(result)
    for required_source_id in getattr(question, "required_cluster_source_ids", []) or []:
        if required_source_id in surfaced_cluster_source_ids:
            checks.append(f"required_cluster_source_id:{required_source_id}:ok")
        else:
            checks.append(f"required_cluster_source_id:{required_source_id}:fail")
            passed = False

    for expected_concept in getattr(question, "expected_concept_candidates", []) or []:
        satisfied = _expected_concept_satisfied(result, expected_concept)
        status = getattr(expected_concept, "status", None)
        if status == ExpectedConceptStatus.SOURCE_BACKED_REQUIRED:
            if satisfied:
                checks.append(f"expected_concept:{expected_concept.concept_id}:required:ok")
            else:
                checks.append(f"expected_concept:{expected_concept.concept_id}:required:fail")
                passed = False
        elif status == ExpectedConceptStatus.LEGACY_ONLY_GAP:
            if satisfied:
                checks.append(f"expected_concept:{expected_concept.concept_id}:legacy_gap:ok")
            else:
                checks.append(f"expected_concept:{expected_concept.concept_id}:legacy_gap:not_surfaced")
        elif status == ExpectedConceptStatus.REJECTED_OR_OUTDATED:
            checks.append(f"expected_concept:{expected_concept.concept_id}:rejected_or_outdated:reference_only")
        else:
            checks.append(
                f"expected_concept:{expected_concept.concept_id}:optional:"
                + ("ok" if satisfied else "not_surfaced")
            )

    if missing_artifacts:
        checks.append(
            "required_artifacts:missing:" + ",".join(sorted(missing_artifacts))
        )
        passed = False

    if review_artifact is not None:
        for check in review_artifact.checks:
            if check.status != "pass":
                checks.append(f"review_check:{check.check_id}:fail")
                passed = False

    return ScenarioVerdict(
        scenario_id=question.question_id,
        passed=passed,
        checks=checks,
    )


def _expected_bundle_artifacts(result, catalog_path: Path) -> list[str]:
    expected = list(REQUIRED_BUNDLE_ARTIFACTS) + ["verdict.json"]
    if result.query_intent.intent_type == "certificate_topology_analysis":
        expected.append("facet_coverage.json")
    if supports_relation_hints(result.query_intent.intent_type):
        expected.append("relation_hints.json")
    if result.provisional_grouping:
        expected.append("provisional_grouping.json")
    if getattr(result, "evidence_clusters", None):
        expected.append("evidence_clusters.json")
    if getattr(result, "selected_evidence", None):
        expected.append("selected_evidence.json")
    if getattr(result, "claim_verification", None):
        expected.append("claim_verification.json")
    if getattr(result, "relation_graph_slice", None):
        expected.append("relation_graph_slice.json")
    if getattr(result, "open_issues", None):
        expected.append("open_issues.json")
    if getattr(result, "navigation_session_trace", None):
        expected.append("navigation_session_trace.json")
    if getattr(result, "source_hierarchy_report", None):
        expected.append("source_hierarchy_report.json")
    if getattr(result, "research_profile_trace", None):
        expected.append("research_profile_trace.json")
    if getattr(result, "reading_plan", None):
        expected.append("reading_plan.json")
    if getattr(result, "opened_passages", None):
        expected.append("opened_passages.json")
    if getattr(result, "evidence_synthesis_matrix", None):
        expected.append("evidence_synthesis_matrix.json")
    if is_real_corpus_catalog(catalog_path):
        expected.append("corpus_coverage_report.json")
    return sorted(expected)


def _stable_value(current, candidate, label: str):
    if current is None:
        return candidate
    if current != candidate:
        raise ValueError(f"Real-question pack run produced inconsistent {label}.")
    return current


def _git_metadata(repo_root: Path) -> dict[str, Optional[Union[str, bool]]]:
    return collect_git_metadata(repo_root)
