from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="Natural-language question to answer.")
    parser.add_argument(
        "--catalog",
        help="Optional internal source catalog path. Defaults to the real-corpus catalog.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for the reviewable artifact bundle.",
    )
    parser.add_argument(
        "--artifacts-only",
        action="store_true",
        help="Write the reviewable artifact bundle and return only the bundle summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher import AgentRuntimeFacade
    from eubw_researcher.models import dataclass_to_dict

    runtime = AgentRuntimeFacade(repo_root)
    if args.artifacts_only:
        if not args.output_dir:
            raise SystemExit(
                "The --artifacts-only flag requires --output-dir so the artifact bundle has a destination."
            )
        response = runtime.write_reviewable_artifact_bundle(
            args.question,
            catalog_path=args.catalog,
            output_dir=args.output_dir,
        )
    else:
        response = runtime.answer_question(
            args.question,
            catalog_path=args.catalog,
            output_dir=args.output_dir,
        )
    print(json.dumps(dataclass_to_dict(response), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
