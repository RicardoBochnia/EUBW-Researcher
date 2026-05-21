#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eubw_researcher.corpus import load_source_catalog
from eubw_researcher.knowledge import build_source_crosswalk
from eubw_researcher.models import dataclass_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an additive source-ID crosswalk from the curated catalog."
    )
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Path to the curated source catalog.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/real_corpus/source_crosswalk.json",
        help="Path for the generated crosswalk artifact.",
    )
    args = parser.parse_args()

    catalog = load_source_catalog(Path(args.catalog))
    crosswalk = build_source_crosswalk(catalog)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dataclass_to_dict(crosswalk), indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(crosswalk)} source crosswalk entries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
