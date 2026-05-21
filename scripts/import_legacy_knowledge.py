#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eubw_researcher.corpus import load_source_catalog
from eubw_researcher.knowledge.legacy_import import import_legacy_knowledge


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy EUBW knowledge as candidate evidence assets.")
    parser.add_argument(
        "--legacy-root",
        default="/mnt/c/Users/Admin/PycharmProjects/EUBW/knowledge",
        help="Legacy EUBW knowledge root. Tests should use an in-repo fixture path.",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/knowledge/imported_legacy",
        help="Output directory for imported candidate assets.",
    )
    parser.add_argument(
        "--catalog",
        default=None,
        help="Optional EUBW-Researcher source catalog for source-ID crosswalk validation.",
    )
    args = parser.parse_args()

    catalog = load_source_catalog(Path(args.catalog)) if args.catalog else None
    report = import_legacy_knowledge(
        Path(args.legacy_root),
        Path(args.output_root),
        catalog=catalog,
    )
    print(
        "Imported "
        f"{report.chunks_imported} chunks, "
        f"{report.claims_imported} claims, "
        f"{report.relations_imported} relations, "
        f"{report.open_issues_imported} open issues, "
        f"{report.benchmark_questions_imported} benchmark questions, "
        f"{report.reference_answers_imported} reference answers."
    )
    if report.unresolved_source_ids:
        print(f"Unresolved source IDs: {len(report.unresolved_source_ids)}")
    if report.rejected_records:
        print(f"Rejected records: {len(report.rejected_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
