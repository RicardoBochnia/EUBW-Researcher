from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="Natural-language question to answer.")
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Internal source catalog path.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for answer, ledger, retrieval-plan, and gap-record artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher import (
        AgentRuntimeMode,
        AgentRuntimeRequest,
        ResearchRuntimeFacade,
    )
    facade = ResearchRuntimeFacade(repo_root)
    try:
        response = facade.run(
            AgentRuntimeRequest(
                question=args.question,
                mode=(
                    AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE
                    if args.output_dir
                    else AgentRuntimeMode.ANSWER_QUESTION
                ),
                catalog_path=args.catalog,
                output_dir=args.output_dir,
            )
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(response.result.rendered_answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
