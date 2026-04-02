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

    from eubw_researcher.config import (
        load_runtime_config,
        load_source_hierarchy,
        load_web_allowlist,
    )
    from eubw_researcher.corpus import (
        default_corpus_refresh_summary_path,
        load_corpus_refresh_summary,
        load_or_build_ingestion_bundle,
    )
    from eubw_researcher.evaluation.runner import write_artifact_bundle
    from eubw_researcher.pipeline import ResearchPipeline

    resolved_catalog_path = (repo_root / args.catalog).resolve()
    _, bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(
        resolved_catalog_path
    )
    pipeline = ResearchPipeline(
        runtime_config=load_runtime_config(repo_root / "configs" / "runtime.yaml"),
        hierarchy=load_source_hierarchy(repo_root / "configs" / "source_hierarchy.yaml"),
        allowlist=load_web_allowlist(repo_root / "configs" / "web_allowlist.yaml"),
        ingestion_bundle=bundle,
    )
    result = pipeline.answer_question(args.question)
    result.corpus_coverage_report = coverage_report
    result.corpus_refresh_summary = load_corpus_refresh_summary(
        default_corpus_refresh_summary_path(resolved_catalog_path)
    )

    if args.output_dir:
        output_dir = (repo_root / args.output_dir).resolve()
        write_artifact_bundle(
            output_dir,
            result,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
        )

    print(result.rendered_answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
