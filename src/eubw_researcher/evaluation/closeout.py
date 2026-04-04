from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from eubw_researcher.models import ScenarioVerdict
from eubw_researcher.trust import build_blind_validation_report, merge_spawned_validator_result

from . import spawned_validator_gate as _spawned_validator_gate
from .spawned_validator_gate import run_spawned_validator_gate

_append_corpus_coverage_gate = _spawned_validator_gate._append_corpus_coverage_gate
_build_spawned_validator_request = _spawned_validator_gate._build_spawned_validator_request
_clear_closeout_sidecar_files = _spawned_validator_gate._clear_spawned_validator_sidecar_files
_decode_process_output = _spawned_validator_gate._decode_process_output
_parse_raw_document_reads = _spawned_validator_gate._parse_raw_document_reads
_parse_spawned_validator_payload = _spawned_validator_gate._parse_spawned_validator_payload
_require_bool_field = _spawned_validator_gate._require_bool_field
_spawned_validator_error = _spawned_validator_gate._spawned_validator_error
subprocess = _spawned_validator_gate.subprocess

SCENARIO_D_ID = "scenario_d_certificate_topology_anchor"


def load_evaluation_scenarios(*args, **kwargs):
    return _spawned_validator_gate.load_evaluation_scenarios(*args, **kwargs)


def _run_pipeline(*args, **kwargs):
    return _spawned_validator_gate._run_pipeline(*args, **kwargs)


def _scenario_config_path(*args, **kwargs):
    return _spawned_validator_gate._scenario_config_path(*args, **kwargs)


def write_artifact_bundle(*args, **kwargs):
    return _spawned_validator_gate.write_artifact_bundle(*args, **kwargs)


def _evaluate_scenario(*args, **kwargs):
    return _spawned_validator_gate._evaluate_scenario(*args, **kwargs)


def _build_closeout_verdict(*args, **kwargs) -> ScenarioVerdict:
    verdict = _spawned_validator_gate._build_spawned_validator_verdict(*args, **kwargs)
    return ScenarioVerdict(
        scenario_id=verdict.scenario_id,
        passed=verdict.passed,
        checks=[
            check.replace(
                "blind_validation_spawned_validator_gate:",
                "blind_validation_closeout:",
            )
            for check in verdict.checks
        ],
    )


def _invoke_spawned_validator(*args, **kwargs):
    result = _spawned_validator_gate._invoke_spawned_validator(*args, **kwargs)
    if result.error is not None:
        result.error = result.error.replace("gate failure", "closeout failure")
    return result


def default_closeout_output_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "scenario_d_closeout"


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
    results, _manifest_path = run_spawned_validator_gate(
        repo_root=repo_root,
        output_dir=output_dir,
        validator_command=validator_command,
        timeout_seconds=timeout_seconds,
        scenario_ids=[SCENARIO_D_ID],
        catalog_path=catalog_path,
        scenarios_path=scenarios_path,
        reviewer_name=reviewer_name,
        require_eligibility=False,
        load_scenarios=load_evaluation_scenarios,
        scenario_config_resolver=_scenario_config_path,
        evaluate_scenario=_evaluate_scenario,
        blind_validation_report_builder=build_blind_validation_report,
        blind_validation_merger=merge_spawned_validator_result,
        pipeline_runner=_run_pipeline,
        bundle_writer=write_artifact_bundle,
    )
    scenario_dir = output_dir / SCENARIO_D_ID
    return scenario_dir, results[0][1]
