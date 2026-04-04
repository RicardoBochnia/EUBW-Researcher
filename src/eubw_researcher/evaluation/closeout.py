from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from eubw_researcher.models import ScenarioVerdict

from .spawned_validator_gate import run_spawned_validator_gate

SCENARIO_D_ID = "scenario_d_certificate_topology_anchor"


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
    )
    scenario_dir = output_dir / SCENARIO_D_ID
    return scenario_dir, results[0][1]
