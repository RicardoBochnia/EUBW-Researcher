from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="tests/fixtures/catalog/source_catalog.yaml",
        help="Internal source catalog path to ingest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.corpus import load_or_build_ingestion_bundle
    from eubw_researcher.models import dataclass_to_dict

    _, bundle, coverage_report, _ = load_or_build_ingestion_bundle(
        (repo_root / args.catalog).resolve()
    )
    print(json.dumps(dataclass_to_dict(bundle.report), indent=2))
    if coverage_report is not None:
        print(json.dumps(dataclass_to_dict(coverage_report), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
