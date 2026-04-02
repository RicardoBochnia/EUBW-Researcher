from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="Scenario id from configs/evaluation_scenarios.yaml")
    parser.add_argument("--all", action="store_true", help="Run all configured evaluation scenarios.")
    parser.add_argument(
        "--catalog",
        help="Optional internal source catalog path. Defaults to the fixture catalog.",
    )
    parser.add_argument(
        "--scenarios-config",
        help="Optional scenario-config path. Defaults to the existing eval routing.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for evaluation artifact bundles.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.scenario:
        raise SystemExit("Pass --scenario <id> or --all.")
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher import AgentRuntimeFacade
    from eubw_researcher.models import dataclass_to_dict

    runtime = AgentRuntimeFacade(repo_root)
    if args.all:
        response = runtime.run_all_evaluations(
            output_dir=args.output_dir,
            catalog_path=args.catalog,
            scenarios_path=args.scenarios_config,
        )
    else:
        response = runtime.run_named_evaluation(
            args.scenario,
            output_dir=args.output_dir,
            catalog_path=args.catalog,
            scenarios_path=args.scenarios_config,
        )

    print(json.dumps(dataclass_to_dict(response), indent=2))
    return 0 if all(result.passed for result in response.results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
