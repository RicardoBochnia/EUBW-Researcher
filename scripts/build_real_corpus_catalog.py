from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/real_corpus_selection.yaml",
        help="Archive-selection config for the real local corpus.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Where to write the generated internal source catalog.",
    )
    parser.add_argument(
        "--report",
        default="artifacts/real_corpus/ingestion_report.json",
        help="Where to write the ingestion report for the generated catalog.",
    )
    parser.add_argument(
        "--coverage-report",
        default="artifacts/real_corpus/corpus_coverage_report.json",
        help="Where to write the corpus coverage gate report.",
    )
    parser.add_argument(
        "--manifest",
        default="artifacts/real_corpus/corpus_manifest.json",
        help="Where to write the reviewer-visible corpus manifest for refresh tracking.",
    )
    parser.add_argument(
        "--refresh-summary",
        default="artifacts/real_corpus/corpus_refresh_summary.json",
        help="Where to write the reviewer-visible corpus refresh summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.config import load_archive_corpus_config
    from eubw_researcher.corpus import (
        build_catalog_from_archive,
        build_corpus_manifest,
        build_corpus_refresh_summary,
        build_manifest_sources,
        compute_corpus_state_id,
        load_corpus_manifest,
        load_or_build_ingestion_bundle,
        write_corpus_manifest,
        write_corpus_refresh_summary,
        write_source_catalog,
        write_corpus_coverage_report,
    )
    from eubw_researcher.models import dataclass_to_dict

    archive_config = load_archive_corpus_config((repo_root / args.config).resolve())
    catalog = build_catalog_from_archive(archive_config)
    output_path = (repo_root / args.output).resolve()
    write_source_catalog(catalog, output_path)

    manifest_sources = build_manifest_sources(catalog)
    corpus_state_id = compute_corpus_state_id(manifest_sources)
    _, bundle, coverage_report, _ = load_or_build_ingestion_bundle(
        output_path,
        manifest_sources=manifest_sources,
        corpus_state_id=corpus_state_id,
    )
    manifest_path = (repo_root / args.manifest).resolve()
    previous_manifest = load_corpus_manifest(manifest_path)
    manifest = build_corpus_manifest(
        output_path,
        catalog,
        sources=manifest_sources,
        corpus_state_id=corpus_state_id,
        bundle=bundle,
        coverage_report=coverage_report,
        selection_config_path=(repo_root / args.config).resolve(),
    )
    refresh_summary = build_corpus_refresh_summary(manifest, previous_manifest)
    write_corpus_manifest(manifest, manifest_path)
    write_corpus_refresh_summary(
        refresh_summary,
        (repo_root / args.refresh_summary).resolve(),
    )
    report_path = (repo_root / args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(dataclass_to_dict(bundle.report), indent=2),
        encoding="utf-8",
    )
    if coverage_report is not None:
        write_corpus_coverage_report(
            coverage_report,
            (repo_root / args.coverage_report).resolve(),
        )

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
