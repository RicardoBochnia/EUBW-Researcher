from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-catalog",
        default="artifacts/real_corpus/archive/catalog.json",
        help="Archive catalog used to analyze the local corpus.",
    )
    parser.add_argument(
        "--curated-catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Optional curated catalog used as an extra activation signal.",
    )
    parser.add_argument(
        "--output",
        default="configs/terminology.yaml",
        help="Where to write the generated terminology config.",
    )
    parser.add_argument(
        "--report",
        default="artifacts/real_corpus/terminology_generation_report.json",
        help="Where to write the machine-readable generation diagnostics.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed terminology file does not match the generated content.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.config.terminology_generation import (
        build_generated_terminology,
        render_generated_terminology,
    )

    archive_catalog_path = (repo_root / args.archive_catalog).resolve()
    curated_catalog_path = (repo_root / args.curated_catalog).resolve()
    output_path = (repo_root / args.output).resolve()
    report_path = (repo_root / args.report).resolve()

    config_payload, report_payload = build_generated_terminology(
        archive_catalog_path,
        curated_catalog_path=curated_catalog_path if curated_catalog_path.exists() else None,
        archive_catalog_display_path=args.archive_catalog,
        curated_catalog_display_path=args.curated_catalog if curated_catalog_path.exists() else None,
    )
    rendered = render_generated_terminology(config_payload)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    if args.check:
        current = output_path.read_text(encoding="utf-8-sig") if output_path.exists() else ""
        if current != rendered:
            print(
                f"{output_path} is out of date; run python3 scripts/update_terminology_from_corpus.py",
                file=sys.stderr,
            )
            return 1
        print(output_path)
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
