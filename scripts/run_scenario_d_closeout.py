from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Internal source catalog path. Defaults to the real-corpus catalog.",
    )
    parser.add_argument(
        "--validator-command",
        required=True,
        help=(
            "Command for the spawned validator. The harness appends "
            "`--input <request.json> --output <result.json>`."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Timeout in seconds for the validator subprocess.",
    )
    parser.add_argument(
        "--scenarios-config",
        help="Optional scenario-config path. Defaults to the real-corpus scenario config.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory root for the closeout bundle. "
            "Defaults to artifacts/scenario_d_closeout."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.evaluation import (
        default_closeout_output_dir,
        run_scenario_d_closeout,
    )

    catalog_path = (repo_root / args.catalog).resolve()
    output_dir = (
        (repo_root / args.output_dir).resolve()
        if args.output_dir
        else default_closeout_output_dir(repo_root).resolve()
    )
    scenarios_path = (repo_root / args.scenarios_config).resolve() if args.scenarios_config else None
    scenario_dir, verdict = run_scenario_d_closeout(
        repo_root=repo_root,
        output_dir=output_dir,
        validator_command=args.validator_command,
        timeout_seconds=args.timeout,
        catalog_path=catalog_path,
        scenarios_path=scenarios_path,
    )
    print(scenario_dir)
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
