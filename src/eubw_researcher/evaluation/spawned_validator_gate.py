from __future__ import annotations

import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple

from eubw_researcher.config import load_evaluation_scenarios
from eubw_researcher.models import (
    BlindValidationRawRead,
    BlindValidationReport,
    EvaluationScenario,
    ScenarioVerdict,
    SpawnedValidatorGateManifest,
    SpawnedValidatorGateScenarioRunSummary,
    SpawnedValidatorResult,
    dataclass_to_dict,
)
from eubw_researcher.runtime_facade import ResearchRuntimeFacade
from eubw_researcher.trust import build_blind_validation_report, merge_spawned_validator_result

from .runner import (
    _evaluate_scenario,
    _run_pipeline,
    _scenario_config_path,
    write_artifact_bundle,
)

SPAWNED_VALIDATOR_REQUEST_FILENAME = "spawned_validator_request.json"
SPAWNED_VALIDATOR_RESULT_FILENAME = "spawned_validator_result.json"
SPAWNED_VALIDATOR_MANIFEST_FILENAME = "spawned_validator_gate_manifest.json"
VALIDATOR_ALLOWED_RAW_DOCUMENT_DEPENDENCIES = {
    "none",
    "minor_confirmation",
    "central_reconstruction",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_spawned_validator_output_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "spawned_validator_gate_runs"


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
            "Derive your answer primarily from the generated artifact bundle. "
            "You may read raw source documents only for minor confirmation of citations already discoverable "
            "from that bundle."
        ),
        "prohibited": [
            "Do not use prior analysis or inherited thread context.",
            "Do not rely on an expected answer.",
            "Do not reconstruct the main argument from raw source documents.",
        ],
    }


def _clear_spawned_validator_sidecar_files(scenario_dir: Path) -> None:
    for filename in [
        SPAWNED_VALIDATOR_REQUEST_FILENAME,
        SPAWNED_VALIDATOR_RESULT_FILENAME,
    ]:
        path = scenario_dir / filename
        if path.exists():
            path.unlink()


def _require_bool_field(payload: dict[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _decode_process_output(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="backslashreplace")
    if isinstance(value, str):
        return value
    return str(value)


def _parse_raw_document_reads(payload: Any) -> List[BlindValidationRawRead]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("raw_document_reads must be a list.")
    reads: List[BlindValidationRawRead] = []
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
    return SpawnedValidatorResult(
        passed=False,
        context_inherited=False,
        artifacts_used=[],
        raw_document_reads=[],
        raw_document_dependency="central_reconstruction",
        product_output_self_sufficient=False,
        summary="Spawned validator did not produce a usable result.",
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
        stdout=_decode_process_output(stdout),
        stderr=_decode_process_output(stderr),
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
            text=False,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_data = getattr(exc, "stdout", getattr(exc, "output", None))
        stderr_data = getattr(exc, "stderr", None)
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=None,
            stdout=_decode_process_output(stdout_data),
            stderr=_decode_process_output(stderr_data),
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
                stdout=_decode_process_output(completed.stdout),
                stderr=_decode_process_output(completed.stderr),
                error="Validator output file was not valid UTF-8.",
            )

    if completed.returncode != 0:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=_decode_process_output(completed.stdout) or raw_output_text,
            stderr=_decode_process_output(completed.stderr),
            error=(
                f"Validator exited with code {completed.returncode}. "
                "A non-zero exit is a gate failure even if it emitted JSON."
            ),
        )
    if raw_output_text is None:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=_decode_process_output(completed.stdout),
            stderr=_decode_process_output(completed.stderr),
            error="Validator did not write the required output JSON file.",
        )
    try:
        payload = json.loads(raw_output_text)
    except json.JSONDecodeError:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=_decode_process_output(completed.stdout) or raw_output_text,
            stderr=_decode_process_output(completed.stderr),
            error="Validator output file did not contain valid JSON.",
        )
    if not isinstance(payload, dict):
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=_decode_process_output(completed.stdout) or raw_output_text,
            stderr=_decode_process_output(completed.stderr),
            error="Validator output file must contain a JSON object.",
        )
    try:
        return _parse_spawned_validator_payload(
            payload,
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=_decode_process_output(completed.stdout),
            stderr=_decode_process_output(completed.stderr),
        )
    except ValueError as exc:
        return _spawned_validator_error(
            validator_command=validator_command,
            exit_code=completed.returncode,
            stdout=_decode_process_output(completed.stdout) or raw_output_text,
            stderr=_decode_process_output(completed.stderr),
            error=str(exc),
        )


def _build_spawned_validator_verdict(
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
    else:
        checks.append("spawned_validator_output_contract:fail")
        passed = False
        checks.append("spawned_validator_context_inherited:unknown")
        checks.append("spawned_validator_raw_document_dependency:unknown")
        checks.append("spawned_validator_passed:unknown")
    if merged_report.passed:
        checks.append("blind_validation_spawned_validator_gate:ok")
    else:
        checks.append("blind_validation_spawned_validator_gate:fail")
        passed = False
    return ScenarioVerdict(
        scenario_id=structural_verdict.scenario_id,
        passed=passed,
        checks=checks,
    )


def build_spawned_validator_gate_manifest(
    *,
    scenario_config_path: Path,
    catalog_path: Path,
    corpus_state_id: str,
    runtime_contract_version: str,
    gate_target: str,
    validator_command: str,
    scenario_runs: List[SpawnedValidatorGateScenarioRunSummary],
) -> SpawnedValidatorGateManifest:
    return SpawnedValidatorGateManifest(
        run_timestamp=_utcnow().isoformat(),
        scenario_config_path=str(scenario_config_path.resolve()),
        catalog_path=str(catalog_path.resolve()),
        corpus_state_id=corpus_state_id,
        runtime_contract_version=runtime_contract_version,
        gate_target=gate_target,
        validator_command=validator_command,
        overall_passed=bool(scenario_runs) and all(item.final_passed for item in scenario_runs),
        scenario_runs=scenario_runs,
    )


def write_spawned_validator_gate_manifest(
    manifest: SpawnedValidatorGateManifest,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclass_to_dict(manifest), indent=2), encoding="utf-8")


def load_spawned_validator_gate_manifest(path: Path) -> SpawnedValidatorGateManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SpawnedValidatorGateManifest(
        run_timestamp=payload["run_timestamp"],
        scenario_config_path=payload["scenario_config_path"],
        catalog_path=payload["catalog_path"],
        corpus_state_id=payload["corpus_state_id"],
        runtime_contract_version=payload["runtime_contract_version"],
        gate_target=payload["gate_target"],
        validator_command=payload["validator_command"],
        overall_passed=payload["overall_passed"],
        scenario_runs=[
            SpawnedValidatorGateScenarioRunSummary(
                scenario_id=item["scenario_id"],
                deterministic_passed=item["deterministic_passed"],
                spawned_validator_invoked=item["spawned_validator_invoked"],
                spawned_validator_contract_passed=item.get(
                    "spawned_validator_contract_passed"
                ),
                spawned_validator_passed=item.get("spawned_validator_passed"),
                final_passed=item["final_passed"],
                output_dir=item["output_dir"],
                verdict_path=item["verdict_path"],
                blind_validation_report_path=item["blind_validation_report_path"],
                spawned_validator_request_path=item.get(
                    "spawned_validator_request_path"
                ),
                spawned_validator_result_path=item.get("spawned_validator_result_path"),
            )
            for item in payload.get("scenario_runs", [])
        ],
    )


def _resolve_selected_scenarios(
    scenarios: Sequence[EvaluationScenario],
    *,
    scenario_ids: Optional[Sequence[str]],
    release_gate: bool,
    require_eligibility: bool,
) -> List[EvaluationScenario]:
    by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    if scenario_ids:
        selected: List[EvaluationScenario] = []
        for scenario_id in scenario_ids:
            if scenario_id not in by_id:
                raise ValueError(f"Scenario with id {scenario_id!r} not found.")
            selected.append(by_id[scenario_id])
        if require_eligibility:
            ineligible = [
                scenario.scenario_id
                for scenario in selected
                if not scenario.spawned_validator_gate_eligible
            ]
            if ineligible:
                raise ValueError(
                    "Selected scenarios are not configured for the spawned-validator gate: "
                    + ", ".join(ineligible)
                )
        return selected
    if release_gate:
        selected = [
            scenario for scenario in scenarios if scenario.spawned_validator_release_gate
        ]
        if not selected:
            raise ValueError(
                "No scenarios are configured for the spawned-validator release gate."
            )
        return selected
    raise ValueError("Pass one or more scenario_ids or enable release_gate.")


def run_spawned_validator_gate(
    *,
    repo_root: Path,
    output_dir: Path,
    validator_command: str,
    timeout_seconds: float,
    scenario_ids: Optional[Sequence[str]] = None,
    release_gate: bool = False,
    catalog_path: Optional[Path] = None,
    scenarios_path: Optional[Path] = None,
    reviewer_name: str = "Codex",
    require_eligibility: bool = True,
    load_scenarios: Callable[[Path], List[EvaluationScenario]] = load_evaluation_scenarios,
    scenario_config_resolver: Callable[[Path, Optional[Path], Optional[Path]], Path] = _scenario_config_path,
    pipeline_runner: Callable[..., Tuple[Any, Any, str, Path]] = _run_pipeline,
    bundle_writer: Callable[..., Any] = write_artifact_bundle,
) -> Tuple[List[Tuple[str, ScenarioVerdict]], Path]:
    resolved_scenarios_path = scenario_config_resolver(repo_root, catalog_path, scenarios_path)
    scenarios = load_scenarios(resolved_scenarios_path)
    selected_scenarios = _resolve_selected_scenarios(
        scenarios,
        scenario_ids=scenario_ids,
        release_gate=release_gate,
        require_eligibility=require_eligibility,
    )
    pipeline, coverage_report, corpus_state_id, resolved_catalog_path = pipeline_runner(
        repo_root,
        catalog_path=catalog_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Tuple[str, ScenarioVerdict]] = []
    manifest_runs: List[SpawnedValidatorGateScenarioRunSummary] = []
    for scenario in selected_scenarios:
        result = pipeline.answer_question(scenario.question)
        result.corpus_coverage_report = coverage_report
        structural_verdict = _append_corpus_coverage_gate(
            _evaluate_scenario(scenario, result),
            coverage_report,
        )
        if result.blind_validation_report is None:
            result.blind_validation_report = build_blind_validation_report(result)
        scenario_dir = output_dir / scenario.scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        _clear_spawned_validator_sidecar_files(scenario_dir)
        request_path = scenario_dir / SPAWNED_VALIDATOR_REQUEST_FILENAME
        spawned_result_path = scenario_dir / SPAWNED_VALIDATOR_RESULT_FILENAME
        if not structural_verdict.passed:
            final_verdict = ScenarioVerdict(
                scenario_id=scenario.scenario_id,
                passed=False,
                checks=structural_verdict.checks
                + ["spawned_validator:skipped_deterministic_gate_failed"],
            )
            bundle_writer(
                scenario_dir,
                result,
                verdict=final_verdict,
                scenario_id=scenario.scenario_id,
                catalog_path=resolved_catalog_path,
                corpus_state_id=corpus_state_id,
                reviewer_name=reviewer_name,
            )
            results.append((scenario.scenario_id, final_verdict))
            manifest_runs.append(
                SpawnedValidatorGateScenarioRunSummary(
                    scenario_id=scenario.scenario_id,
                    deterministic_passed=False,
                    spawned_validator_invoked=False,
                    spawned_validator_contract_passed=None,
                    spawned_validator_passed=None,
                    final_passed=False,
                    output_dir=str(scenario_dir.resolve()),
                    verdict_path=str((scenario_dir / "verdict.json").resolve()),
                    blind_validation_report_path=str(
                        (scenario_dir / "blind_validation_report.json").resolve()
                    ),
                )
            )
            continue

        bundle_writer(
            scenario_dir,
            result,
            verdict=structural_verdict,
            scenario_id=scenario.scenario_id,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
            reviewer_name=reviewer_name,
        )
        request_payload = _build_spawned_validator_request(scenario_dir, scenario.question)
        request_path.write_text(json.dumps(request_payload, indent=2), encoding="utf-8")
        spawned_validator = _invoke_spawned_validator(
            repo_root=repo_root,
            validator_command=validator_command,
            request_path=request_path,
            result_path=spawned_result_path,
            timeout_seconds=timeout_seconds,
        )
        spawned_result_path.write_text(
            json.dumps(dataclass_to_dict(spawned_validator), indent=2),
            encoding="utf-8",
        )
        result.blind_validation_report = merge_spawned_validator_result(
            result.blind_validation_report,
            spawned_validator,
        )
        final_verdict = _build_spawned_validator_verdict(
            structural_verdict,
            result.blind_validation_report,
            spawned_validator,
        )
        bundle_writer(
            scenario_dir,
            result,
            verdict=final_verdict,
            scenario_id=scenario.scenario_id,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
            reviewer_name=reviewer_name,
        )
        results.append((scenario.scenario_id, final_verdict))
        manifest_runs.append(
            SpawnedValidatorGateScenarioRunSummary(
                scenario_id=scenario.scenario_id,
                deterministic_passed=True,
                spawned_validator_invoked=True,
                spawned_validator_contract_passed=spawned_validator.error is None,
                spawned_validator_passed=(
                    spawned_validator.passed
                    if spawned_validator.error is None
                    else None
                ),
                final_passed=final_verdict.passed,
                output_dir=str(scenario_dir.resolve()),
                verdict_path=str((scenario_dir / "verdict.json").resolve()),
                blind_validation_report_path=str(
                    (scenario_dir / "blind_validation_report.json").resolve()
                ),
                spawned_validator_request_path=str(request_path.resolve()),
                spawned_validator_result_path=str(spawned_result_path.resolve()),
            )
        )

    gate_target = "release_gate" if release_gate else "named_scenarios"
    manifest = build_spawned_validator_gate_manifest(
        scenario_config_path=resolved_scenarios_path,
        catalog_path=resolved_catalog_path,
        corpus_state_id=corpus_state_id,
        runtime_contract_version=ResearchRuntimeFacade.CONTRACT_VERSION,
        gate_target=gate_target,
        validator_command=validator_command,
        scenario_runs=manifest_runs,
    )
    manifest_path = output_dir / SPAWNED_VALIDATOR_MANIFEST_FILENAME
    write_spawned_validator_gate_manifest(manifest, manifest_path)
    return results, manifest_path
