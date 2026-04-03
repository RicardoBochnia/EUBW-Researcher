from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _catalog_path import resolve_catalog_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--all",
        action="store_true",
        help="Run every configured real-question pack question.",
    )
    selection.add_argument(
        "--question-id",
        help="Run one configured real-question pack question.",
    )
    parser.add_argument(
        "--pack",
        help="Optional real-question pack config path. Defaults to configs/real_question_pack.yaml.",
    )
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Internal source catalog path.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Optional run directory. Defaults to "
            "artifacts/real_question_pack_runs/<timestamp>."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    catalog_path = resolve_catalog_path(repo_root, args.catalog)

    from eubw_researcher.evaluation import run_real_question_pack

    try:
        run_root, manifest = run_real_question_pack(
            repo_root=repo_root,
            pack_path=args.pack,
            question_id=args.question_id,
            catalog_path=catalog_path,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(run_root)
    print(",".join(manifest.selected_question_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
