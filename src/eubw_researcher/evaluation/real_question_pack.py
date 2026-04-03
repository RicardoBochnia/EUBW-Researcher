from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from eubw_researcher import ResearchRuntimeFacade
from eubw_researcher.config import load_real_question_pack
from eubw_researcher.corpus import is_real_corpus_catalog
from eubw_researcher.evaluation.review import build_manual_review_report
from eubw_researcher.evaluation.runner import write_artifact_bundle
from eubw_researcher.models import (
    RealQuestionPack,
    RealQuestionPackQuestion,
    RealQuestionPackQuestionRunSummary,
    RealQuestionPackRunManifest,
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
) -> tuple[Path, RealQuestionPackRunManifest]:
    resolved_repo_root = Path(repo_root).resolve()
    resolved_pack_path = _resolve_path(
        resolved_repo_root,
        pack_path or DEFAULT_PACK_PATH,
    )
    pack = load_real_question_pack(resolved_pack_path)
    selected_questions = _select_questions(pack, question_id)

    run_root = (
        _resolve_path(resolved_repo_root, output_dir)
        if output_dir is not None
        else default_real_question_pack_output_dir(resolved_repo_root)
    )
    _validate_run_root(resolved_repo_root, run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    facade = ResearchRuntimeFacade(resolved_repo_root)
    git_metadata = _git_metadata(resolved_repo_root)
    pack_digest = hashlib.sha256(resolved_pack_path.read_bytes()).hexdigest()

    question_runs = []
    runtime_contract_version: Optional[str] = None
    resolved_catalog_path: Optional[Path] = None
    corpus_state_id: Optional[str] = None

    for question in selected_questions:
        question_output_dir = run_root / question.question_id
        _prepare_question_output_dir(question_output_dir)
        response = facade.write_reviewable_artifact_bundle(
            question.question,
            question_output_dir,
            catalog_path=catalog_path,
        )
        actual_artifacts = sorted(
            path.name for path in question_output_dir.iterdir() if path.is_file()
        )
        expected_artifacts = _expected_bundle_artifacts(
            response.result,
            response.catalog_path,
        )
        missing_artifacts = [
            artifact for artifact in expected_artifacts if artifact not in actual_artifacts
        ]
        verdict = _build_question_verdict(
            question,
            response.result,
            missing_artifacts=missing_artifacts,
        )
        write_artifact_bundle(
            question_output_dir,
            response.result,
            verdict=verdict,
            scenario_id=question.question_id,
            catalog_path=response.catalog_path,
            corpus_state_id=response.corpus_state_id,
        )
        report = build_manual_review_report(
            response.result,
            verdict,
            scenario_id=question.question_id,
            catalog_path=str(response.catalog_path),
            corpus_state_id=response.corpus_state_id,
        )
        actual_artifacts = sorted(
            path.name for path in question_output_dir.iterdir() if path.is_file()
        )
        question_runs.append(
            RealQuestionPackQuestionRunSummary(
                question_id=question.question_id,
                title=question.title,
                expected_intent_type=question.expected_intent_type,
                output_dir=str(question_output_dir.resolve()),
                artifacts_present=actual_artifacts,
                missing_artifacts=missing_artifacts,
                intent_type=response.result.query_intent.intent_type,
                approved_entry_count=len(response.result.approved_entries),
                gap_record_count=len(response.result.gap_records),
                web_fetch_count=sum(
                    1
                    for record in response.result.web_fetch_records
                    if getattr(record, "record_type", None) == "fetch"
                ),
                final_judgment=report.final_judgment,
                usefulness_verdict=report.usefulness_verdict,
                source_bound_verdict=report.source_bound_verdict,
                pinpoint_traceability_verdict=report.pinpoint_traceability_verdict,
                product_output_self_sufficiency_verdict=(
                    report.product_output_self_sufficiency_verdict
                ),
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

    manifest = RealQuestionPackRunManifest(
        run_id=run_root.name,
        run_timestamp=_utcnow().isoformat(),
        pack_path=str(resolved_pack_path),
        pack_digest=pack_digest,
        selected_question_ids=[question.question_id for question in selected_questions],
        catalog_path=str(resolved_catalog_path),
        corpus_state_id=corpus_state_id,
        runtime_contract_version=runtime_contract_version,
        entrypoint=DEFAULT_ENTRYPOINT,
        git_commit=git_metadata["commit"],
        git_branch=git_metadata["branch"],
        git_dirty=git_metadata["dirty"],
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


def _validate_run_root(repo_root: Path, run_root: Path) -> None:
    if run_root == repo_root:
        raise ValueError("Real-question pack output_dir must not resolve to the repository root")
    if run_root.exists() and not run_root.is_dir():
        raise ValueError(f"Real-question pack output_dir must be a directory path: {run_root}")


def _prepare_question_output_dir(question_output_dir: Path) -> None:
    if question_output_dir.exists():
        if not question_output_dir.is_dir():
            raise ValueError(
                f"Real-question output path must be a directory: {question_output_dir}"
            )
        shutil.rmtree(question_output_dir)
    question_output_dir.mkdir(parents=True, exist_ok=True)


def _build_question_verdict(
    question: RealQuestionPackQuestion,
    result,
    *,
    missing_artifacts: list[str],
) -> ScenarioVerdict:
    checks: list[str] = []
    passed = True

    if question.expected_intent_type:
        if result.query_intent.intent_type == question.expected_intent_type:
            checks.append(f"intent_type:{question.expected_intent_type}:ok")
        else:
            checks.append(
                "intent_type:"
                f"{question.expected_intent_type}:fail:{result.query_intent.intent_type}"
            )
            passed = False
    else:
        checks.append("intent_type:not_specified")

    if missing_artifacts:
        checks.append("required_artifacts:fail:" + ",".join(sorted(missing_artifacts)))
        passed = False
    else:
        checks.append("required_artifacts:ok")

    return ScenarioVerdict(
        scenario_id=question.question_id,
        passed=passed,
        checks=checks,
    )


def _expected_bundle_artifacts(result, catalog_path: Path) -> list[str]:
    expected = list(REQUIRED_BUNDLE_ARTIFACTS)
    if result.query_intent.intent_type == "certificate_topology_analysis":
        expected.append("facet_coverage.json")
    if result.provisional_grouping:
        expected.append("provisional_grouping.json")
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
    branch = _run_git_command(repo_root, "branch", "--show-current")
    commit = _run_git_command(repo_root, "rev-parse", "HEAD")
    status = _run_git_command(repo_root, "status", "--short")
    return {
        "branch": branch,
        "commit": commit,
        "dirty": bool(status),
    }


def _run_git_command(repo_root: Path, *args: str) -> Optional[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None
