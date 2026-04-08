from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PR_CI_TRIGGER_PATTERN = re.compile(
    r"^(?:\.github/workflows/|configs/|pyproject\.toml$|scripts/|src/|tests/|tests_closeout/)"
)
INTEGRATION_PATTERN = re.compile(
    r"^(?:"
    r"pyproject\.toml$|"
    r"configs/|"
    r"scripts/(?:"
    r"_test_runner\.py|"
    r"answer_question\.py|"
    r"build_real_corpus_catalog\.py|"
    r"refresh_real_corpus\.py|"
    r"report_validated_current_state\.py|"
    r"run_eval\.py|"
    r"run_integration_tests\.py|"
    r"run_real_question_pack\.py|"
    r"run_tests\.py"
    r")|"
    r"src/eubw_researcher/|"
    r"tests/fixtures/|"
    r"tests/integration/"
    r")"
)
CLOSEOUT_PATTERN = re.compile(
    r"^(?:"
    r"pyproject\.toml$|"
    r"configs/|"
    r"scripts/(?:"
    r"_test_runner\.py|"
    r"run_closeout_tests\.py|"
    r"run_scenario_d_closeout\.py|"
    r")|"
    r"src/eubw_researcher/(?:"
    r"answering/|"
    r"config/|"
    r"corpus/|"
    r"evaluation/|"
    r"evidence/|"
    r"models/|"
    r"pipeline\.py|"
    r"retrieval/|"
    r"trust\.py"
    r"|web/"
    r")|"
    r"tests_closeout/"
    r")"
)


@dataclass(frozen=True)
class TestRoutingDecision:
    run_ci: bool
    run_integration: bool
    run_closeout: bool


def changed_files_between(base_sha: str, head_sha: str, *, repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def classify_changed_files(changed_files: Iterable[str]) -> TestRoutingDecision:
    files = tuple(changed_files)
    run_ci = any(PR_CI_TRIGGER_PATTERN.search(path) for path in files)
    return TestRoutingDecision(
        run_ci=run_ci,
        run_integration=any(INTEGRATION_PATTERN.search(path) for path in files),
        run_closeout=any(CLOSEOUT_PATTERN.search(path) for path in files),
    )
