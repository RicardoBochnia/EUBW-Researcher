from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple

from eubw_researcher.config import load_evaluation_scenarios
from eubw_researcher.models import (
    BlindValidationRawRead,
    BlindValidationReport,
    ScenarioVerdict,
    SpawnedValidatorResult,
    dataclass_to_dict,
)
from eubw_researcher.trust import build_blind_validation_report, merge_spawned_validator_result

from .runner import (
    _evaluate_scenario,
    _run_pipeline,
    _scenario_config_path,
    write_artifact_bundle,
)

SCENARIO_D_ID = "scenario_d_certificate_topology_anchor"
VALIDATOR_ALLOWED_RAW_DOCUMENT_DEPENDENCIES = {
    "none",
    "minor_confirmation",
    "central_reconstruction",
}


def default_closeout_output_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "scenario_d_closeout"


def _append_corpus_coverage_gate(verdict: ScenarioVerdict, coverage_report) -> ScenarioVerdict:
    checks = list(verdict.checks)
    passed = verdict.passed
    if coverage_report is not None:
        if coverage_report.passed:
            checks.append("corpus_coverage_gate:ok")
        else:
            checks.append("corpus_coverage_gate:fail")
            passed = False
    return ScenarioVerdict(
        scenario_id=verdict.scenario_id,
        passed=passed,
        checks=checks,
    )


def _build_spawned_validator_request(bundle_dir: Path, question: str) -> dict[str, Any]:
    return {
        "bundle_dir": str(bundle_dir),
        "question": question,
        "required_artifacts": [
            "final_answer.txt",
            "approved_ledger.json",
            "facet_coverage.json",
            "pinpoint_evidence.json",
            "answer_alignment.json",
            "manual_review_report.md",
        ],
        "instructions": (
            "Derive your answer primarily from the generated Scenario D bundle. "
            "You may read raw source documents only for minor confirmation of citations already discoverable "
            "from the product artifacts."
        ),
        "prohibited": [
            "Do not use prior analysis or inherited thread context.",
            "Do not rely on an expected answer.",
            "Do not reconstruct the main argument from raw source documents.",
        ],
    }


def _clear_closeout_sidecar_files(scenario_dir: Path) -> None:
    for filename in [
        "spawned_validator_request.json",
        "spawned_validator_result.json",
    ]:
        path = scenario_dir / filename
        if path.exists():
            path.unlink()


def _require_bool_field(payload: dict[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _parse_raw_document_reads(payload: Any) -> list[BlindValidationRawRead]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("raw_document_reads must be a list.")
    reads: list[BlindValidationRawRead] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each raw_document_reads item must be an object.")
        document_path_value = item.get("document_path")
        if document_path_value is not None and not isinstance(document_path_value, str):
            raise ValueError("raw_document_reads.document_path must be a string when present.")
        reads.append(
            BlindValidationRawRead(
                source_id=str(item.get("source_id", "")),
                document_path=Path(document_path_value) if document_path_value else None,
                purpose=str(item.get("purpose", "")),
                classification=str(item.get("classification", "")),
            )
        )
    return reads


def _spawned_validator_error(
    *,
    validator_command: str,
    exit_code: Optional[int],
    stdout: Optional[str],
    stderr: Optional[str],
    error: str,
) -> SpawnedValidatorResult:
    # Fail closed: if the validator cannot be trusted or did not complete,
    # treat the closeout as requiring central reconstruction rather than
    # claiming artifact-only self-sufficiency.
    return SpawnedValidatorResult(
        passed=False,
        context_inherited=False,
        artifacts_used=[],
        raw_document_reads=[],
        raw_document_dependency="central_reconstruction",
        product_output_self_sufficient=False,
        summary="Spawned validator did not produce a usable closeout result.",
        validator_answer="",
        notes=None,
        validator_command=validator_command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        error=error,
    )


def _parse_spawned_validator_payload(
    payload: dict[str, Any],
    *,
    validator_command: str,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> SpawnedValidatorResult:
    missing = [
        key
        for key in [
            "passed",
            "context_inherited",
            "artifacts_used",
            "raw_document_dependency",
            "product_output_self_sufficient",
            "summary",
            "validator_answer",
        ]
        if key not in payload
    ]
    if missing:
        raise ValueError("Missing required validator output fields: " + ", ".join(missing))
    raw_document_dependency = str(payload["raw_document_dependency"])
    if raw_document_dependency not in VALIDATOR_ALLOWED_RAW_DOCUMENT_DEPENDENCIES:
        raise ValueError(
            "raw_document_dependency must be one of "
            + ", ".join(sorted(VALIDATOR_ALLOWED_RAW_DOCUMENT_DEPENDENCIES))
        )
    artifacts_used = payload["artifacts_used"]
    if not isinstance(artifacts_used, list) or not all(
        isinstance(item, str) for item in artifacts_used
    ):
        raise ValueError("artifacts_used must be a list of strings.")
    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("notes must be a string when present.")
    return SpawnedValidatorResult(
        passed=_require_bool_field(payload, "passed"),
        context_inherited=_require_bool_field(payload, "context_inherited"),
        artifacts_used=list(artifacts_used),
        raw_document_reads=_parse_raw_document_reads(payload.get("raw_document_reads")),
        raw_document_dependency=raw_document_dependency,
        product_output_self_sufficient=_require_bool_field(
            payload,
            "product_output_self_sufficient",
        ),
        summary=str(payload["summary"]),
        validator_answer=str(payload["validator_answer"]),
        notes=notes,
        validator_command=validator_command,
        exit_code=exit_code,
        stdout=stdout or None,
        stderr=stderr or None,
        error=None,
    )


def _invoke_spawned_validator(
    *,
    repo_root: Path,
    validator_command: str,
    request_path: Path,
    result_path: Path,
    timeout_seconds: float,
) -> SpawnedValidatorResult:
    try:
        command = shlex.split(validator_command)
    except ValueError as exc:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=None,
            stdout=None,
            stderr=None,
            error=f"Validator command could not be parsed: {exc}",
        )
    if not command:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=None,
            stdout=None,
            stderr=None,
            error="Validator command is empty.",
        )
    if result_path.exists():
        result_path.unlink()
    try:
        completed = subprocess.run(
            command + ["--input", str(request_path), "--output", str(result_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=None,
            stdout=exc.stdout,
            stderr=exc.stderr,
            error=f"Validator timed out after {timeout_seconds:.1f} seconds.",
        )
    except OSError as exc:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=None,
            stdout=None,
            stderr=None,
            error=f"Validator could not be started: {exc}.",
        )

    raw_output_text = None
    if result_path.exists():
        try:
            raw_output_text = result_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return _spawned_validator_error(
                validator_command=validator_command,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                error="Validator output file was not valid UTF-8.",
            )

    if completed.returncode != 0:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=completed.stdout or raw_output_text,
            stderr=completed.stderr,
            error=(
                f"Validator exited with code {completed.returncode}. "
                "A non-zero exit is a closeout failure even if it emitted JSON."
            ),
        )
    if raw_output_text is None:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            error="Validator did not write the required output JSON file.",
        )
    try:
        payload = json.loads(raw_output_text)
    except json.JSONDecodeError:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=completed.stdout or raw_output_text,
            stderr=completed.stderr,
            error="Validator output file did not contain valid JSON.",
        )
    if not isinstance(payload, dict):
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=completed.stdout or raw_output_text,
            stderr=completed.stderr,
            error="Validator output file must contain a JSON object.",
        )
    try:
        return _parse_spawned_validator_payload(
            payload,
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except ValueError as exc:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=completed.stdout or raw_output_text,
            stderr=completed.stderr,
            error=str(exc),
        )


def _build_closeout_verdict(
    structural_verdict: ScenarioVerdict,
    merged_report: BlindValidationReport,
    spawned_validator: SpawnedValidatorResult,
) -> ScenarioVerdict:
    checks = list(structural_verdict.checks)
    passed = structural_verdict.passed
    checks.append("spawned_validator_invoked:ok")
    if spawned_validator.exit_code == 0:
        checks.append("spawned_validator_exit_code:ok")
    else:
        exit_label = (
            str(spawned_validator.exit_code)
            if spawned_validator.exit_code is not None
            else "missing"
        )
        checks.append(f"spawned_validator_exit_code:fail:{exit_label}")
        passed = False
    if spawned_validator.error is None:
        checks.append("spawned_validator_output_contract:ok")
    else:
        checks.append("spawned_validator_output_contract:fail")
        passed = False
    if not spawned_validator.context_inherited:
        checks.append("spawned_validator_context_inherited:false:ok")
    else:
        checks.append("spawned_validator_context_inherited:false:fail")
        passed = False
    if spawned_validator.raw_document_dependency in {"none", "minor_confirmation"}:
        checks.append(
            "spawned_validator_raw_document_dependency:"
            f"{spawned_validator.raw_document_dependency}:ok"
        )
    else:
        checks.append(
            "spawned_validator_raw_document_dependency:"
            f"{spawned_validator.raw_document_dependency}:fail"
        )
        passed = False
    if spawned_validator.passed:
        checks.append("spawned_validator_passed:ok")
    else:
        checks.append("spawned_validator_passed:fail")
        passed = False
    if merged_report.passed:
        checks.append("blind_validation_closeout:ok")
    else:
        checks.append("blind_validation_closeout:fail")
        passed = False
    return ScenarioVerdict(
        scenario_id=structural_verdict.scenario_id,
        passed=passed,
        checks=checks,
    )


def run_scenario_d_closeout(
    *,
    repo_root: Path,
    output_dir: Path,
    validator_command: str,
    timeout_seconds: float,
    catalog_path: Optional[Path] = None,
    scenarios_path: Optional[Path] = None,
    reviewer_name: str = "Codex",
) -> Tuple[Path, ScenarioVerdict]:
    resolved_scenarios_path = _scenario_config_path(repo_root, catalog_path, scenarios_path)
    scenarios = load_evaluation_scenarios(resolved_scenarios_path)
    scenario = next(item for item in scenarios if item.scenario_id == SCENARIO_D_ID)
    pipeline, coverage_report, corpus_state_id, resolved_catalog_path = _run_pipeline(
        repo_root,
        catalog_path=catalog_path,
    )
    result = pipeline.answer_question(scenario.question)
    result.corpus_coverage_report = coverage_report
    structural_verdict = _append_corpus_coverage_gate(
        _evaluate_scenario(scenario, result),
        coverage_report,
    )
    if result.blind_validation_report is None:
        result.blind_validation_report = build_blind_validation_report(result)

    scenario_dir = output_dir / SCENARIO_D_ID
    scenario_dir.mkdir(parents=True, exist_ok=True)
    _clear_closeout_sidecar_files(scenario_dir)

    if not structural_verdict.passed:
        closeout_verdict = ScenarioVerdict(
            scenario_id=SCENARIO_D_ID,
            passed=False,
            checks=structural_verdict.checks + ["spawned_validator:skipped_deterministic_gate_failed"],
        )
        write_artifact_bundle(
            scenario_dir,
            result,
            verdict=closeout_verdict,
            scenario_id=SCENARIO_D_ID,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
            reviewer_name=reviewer_name,
        )
        return scenario_dir, closeout_verdict

    # The validator is supposed to inspect the generated bundle, so write the
    # deterministic artifact set before handing off to the spawned validator.
    write_artifact_bundle(
        scenario_dir,
        result,
        verdict=structural_verdict,
        scenario_id=SCENARIO_D_ID,
        catalog_path=resolved_catalog_path,
        corpus_state_id=corpus_state_id,
        reviewer_name=reviewer_name,
    )
    request_payload = _build_spawned_validator_request(scenario_dir, scenario.question)
    request_path = scenario_dir / "spawned_validator_request.json"
    request_path.write_text(json.dumps(request_payload, indent=2), encoding="utf-8")
    spawned_result_path = scenario_dir / "spawned_validator_result.json"
    spawned_validator = _invoke_spawned_validator(
        repo_root=repo_root,
        validator_command=validator_command,
        request_path=request_path,
        result_path=spawned_result_path,
        timeout_seconds=timeout_seconds,
    )
    # Persist the normalized validator result immediately so the sidecar file
    # is present even if a later bundle rewrite fails.
    spawned_result_path.write_text(
        json.dumps(dataclass_to_dict(spawned_validator), indent=2),
        encoding="utf-8",
    )
    result.blind_validation_report = merge_spawned_validator_result(
        result.blind_validation_report,
        spawned_validator,
    )
    closeout_verdict = _build_closeout_verdict(
        structural_verdict,
        result.blind_validation_report,
        spawned_validator,
    )
    write_artifact_bundle(
        scenario_dir,
        result,
        verdict=closeout_verdict,
        scenario_id=SCENARIO_D_ID,
        catalog_path=resolved_catalog_path,
        corpus_state_id=corpus_state_id,
        reviewer_name=reviewer_name,
    )
    return scenario_dir, closeout_verdict
