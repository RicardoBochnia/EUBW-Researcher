from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate corpus selection, coverage, and state-snapshot artifacts."
    )
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Path to the curated source catalog.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/real_corpus",
        help="Directory where the three artifacts are written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.corpus import (
        build_corpus_state_snapshot,
        load_or_build_ingestion_bundle,
        render_corpus_coverage_summary_md,
        render_corpus_selection_summary_md,
        write_corpus_state_snapshot,
    )
    from eubw_researcher.corpus.runtime import write_corpus_coverage_report

    catalog_path = (repo_root / args.catalog).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog, _bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(
        catalog_path
    )

    selection_path = output_dir / "corpus_selection_summary.md"
    selection_path.write_text(
        render_corpus_selection_summary_md(catalog), encoding="utf-8"
    )

    coverage_summary_path = output_dir / "corpus_coverage_summary.md"
    if coverage_report is not None:
        coverage_summary_path.write_text(
            render_corpus_coverage_summary_md(coverage_report, catalog), encoding="utf-8"
        )
        write_corpus_coverage_report(coverage_report, output_dir / "corpus_coverage_report.json")

    snapshot_path = output_dir / "corpus_state_snapshot.json"
    write_corpus_state_snapshot(
        build_corpus_state_snapshot(catalog, corpus_state_id, catalog_path),
        snapshot_path,
    )

    print(selection_path)
    if coverage_report is not None:
        print(coverage_summary_path)
    print(snapshot_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
