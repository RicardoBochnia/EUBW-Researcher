from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _catalog_path import resolve_catalog_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="Scenario id configured for the spawned-validator gate.")
    parser.add_argument(
        "--release-gate",
        action="store_true",
        help="Run the configured spawned-validator release-gate scenario subset.",
    )
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
        help="Optional scenario-config path. Defaults by catalog type.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory root for the validator-gated bundles. "
            "Defaults to artifacts/spawned_validator_gate_runs."
        ),
    )
    parser.add_argument(
        "--runtime-config",
        default="configs/runtime.yaml",
        help="Runtime config path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.scenario) == bool(args.release_gate):
        raise SystemExit("Pass exactly one of --scenario <id> or --release-gate.")
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.evaluation import (
        default_spawned_validator_output_dir,
        run_spawned_validator_gate,
    )

    catalog_path = resolve_catalog_path(repo_root, args.catalog)
    output_dir = (
        (repo_root / args.output_dir).resolve()
        if args.output_dir
        else default_spawned_validator_output_dir(repo_root).resolve()
    )
    scenarios_path = (repo_root / args.scenarios_config).resolve() if args.scenarios_config else None
    results, manifest_path = run_spawned_validator_gate(
        repo_root=repo_root,
        output_dir=output_dir,
        validator_command=args.validator_command,
        timeout_seconds=args.timeout,
        scenario_ids=[args.scenario] if args.scenario else None,
        release_gate=args.release_gate,
        catalog_path=catalog_path,
        scenarios_path=scenarios_path,
        runtime_config_path=(repo_root / args.runtime_config).resolve(),
    )
    for scenario_id, verdict in results:
        print(f"{scenario_id}: {'PASS' if verdict.passed else 'FAIL'}")
    print(manifest_path)
    return 0 if all(verdict.passed for _, verdict in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
