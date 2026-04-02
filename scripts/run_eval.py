from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _catalog_path import resolve_catalog_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="Scenario id from configs/evaluation_scenarios.yaml")
    parser.add_argument("--all", action="store_true", help="Run all configured evaluation scenarios.")
    parser.add_argument(
        "--catalog",
        help="Optional internal source catalog path. Defaults to tests/fixtures/catalog/source_catalog.yaml. Real-corpus catalogs auto-select the real-corpus scenario gate.",
    )
    parser.add_argument(
        "--scenarios-config",
        help="Optional scenario-config path. Defaults to configs/evaluation_scenarios.yaml.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory for retrieval-plan, gap-record, ledger, and answer artifacts. "
            "Defaults to artifacts/eval_runs, or artifacts/eval_runs_real_corpus "
            "when the real-corpus catalog is used."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.scenario:
        raise SystemExit("Pass --scenario <id> or --all.")
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    catalog_path = resolve_catalog_path(repo_root, args.catalog)
    from eubw_researcher.evaluation import run_all_scenarios, run_named_scenario
    from eubw_researcher.evaluation.runner import default_output_dir

    output_dir = (
        (repo_root / args.output_dir).resolve()
        if args.output_dir
        else default_output_dir(repo_root, catalog_path).resolve()
    )
    scenarios_path = (repo_root / args.scenarios_config).resolve() if args.scenarios_config else None
    if args.all:
        results = run_all_scenarios(
            repo_root=repo_root,
            output_dir=output_dir,
            catalog_path=catalog_path,
            scenarios_path=scenarios_path,
        )
        for scenario_id, verdict in results:
            print(f"{scenario_id}: {'PASS' if verdict.passed else 'FAIL'}")
        return 0 if all(verdict.passed for _, verdict in results) else 1

    scenario_dir, verdict = run_named_scenario(
        repo_root=repo_root,
        scenario_id=args.scenario,
        output_dir=output_dir,
        catalog_path=catalog_path,
        scenarios_path=scenarios_path,
    )
    print(scenario_dir)
    if not verdict.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
