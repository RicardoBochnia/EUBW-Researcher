from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_ci_test_routing_module():
    module_path = REPO_ROOT / "src" / "eubw_researcher" / "ci_test_routing.py"
    spec = importlib.util.spec_from_file_location("ci_test_routing_direct", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load CI routing module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CI_TEST_ROUTING = _load_ci_test_routing_module()
changed_files_between = _CI_TEST_ROUTING.changed_files_between
classify_changed_files = _CI_TEST_ROUTING.classify_changed_files


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute which pull-request test suites should run for a diff."
    )
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--github-output")
    return parser


def _write_github_output(output_path: Path, *, run_ci: bool, run_integration: bool, run_closeout: bool) -> None:
    output_path.write_text(
        "\n".join(
            [
                f"run_ci={'true' if run_ci else 'false'}",
                f"run_integration={'true' if run_integration else 'false'}",
                f"run_closeout={'true' if run_closeout else 'false'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _build_parser().parse_args()
    changed_files = changed_files_between(args.base_sha, args.head_sha, repo_root=REPO_ROOT)
    decision = classify_changed_files(changed_files)

    print("Changed files:")
    if changed_files:
        for path in changed_files:
            print(path)
    else:
        print("(none)")

    print(
        json.dumps(
            {
                "run_ci": decision.run_ci,
                "run_integration": decision.run_integration,
                "run_closeout": decision.run_closeout,
            },
            indent=2,
            sort_keys=True,
        )
    )

    if args.github_output:
        _write_github_output(
            Path(args.github_output),
            run_ci=decision.run_ci,
            run_integration=decision.run_integration,
            run_closeout=decision.run_closeout,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
