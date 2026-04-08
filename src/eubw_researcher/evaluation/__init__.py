"""Evaluation runners."""

from .closeout import default_closeout_output_dir, run_scenario_d_closeout
from .real_question_pack import (
    default_real_question_pack_output_dir,
    run_real_question_pack,
)
from .review import (
    build_manual_review_artifact,
    build_manual_review_report,
    build_manual_review_report_markdown,
)
from .runner import load_eval_run_manifest, run_all_scenarios, run_named_scenario
from .spawned_validator_gate import (
    default_spawned_validator_output_dir,
    load_spawned_validator_gate_manifest,
    run_spawned_validator_gate,
)
from eubw_researcher.trust import build_blind_validation_report

__all__ = [
    "build_blind_validation_report",
    "build_manual_review_artifact",
    "build_manual_review_report",
    "build_manual_review_report_markdown",
    "default_closeout_output_dir",
    "default_real_question_pack_output_dir",
    "default_spawned_validator_output_dir",
    "load_eval_run_manifest",
    "load_spawned_validator_gate_manifest",
    "run_all_scenarios",
    "run_named_scenario",
    "run_real_question_pack",
    "run_scenario_d_closeout",
    "run_spawned_validator_gate",
]
