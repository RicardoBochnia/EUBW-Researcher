from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from _catalog_path import resolve_catalog_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a compact validated current-state report for the real-corpus eval gate."
    )
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Path to the curated source catalog.",
    )
    parser.add_argument(
        "--eval-manifest",
        default="artifacts/eval_runs_real_corpus/eval_run_manifest.json",
        help="Path to the top-level eval manifest produced by run_eval.py --all.",
    )
    parser.add_argument(
        "--real-question-pack-manifest",
        help="Optional pack_run_manifest.json path to record as supplemental evidence.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/current_state",
        help="Directory where the validated current-state artifacts are written.",
    )
    return parser.parse_args()


def _run_git_command(repo_root: Path, *args: str) -> Optional[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _git_metadata(repo_root: Path) -> dict[str, Optional[object]]:
    branch = _run_git_command(repo_root, "branch", "--show-current")
    commit = _run_git_command(repo_root, "rev-parse", "HEAD")
    status = _run_git_command(repo_root, "status", "--short")
    return {
        "branch": branch,
        "commit": commit,
        "dirty": True if status is None else bool(status),
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.corpus import (
        build_corpus_state_snapshot,
        build_validated_current_state_report,
        load_or_build_ingestion_bundle,
        render_corpus_coverage_summary_md,
        render_corpus_selection_summary_md,
        render_validated_current_state_report_md,
        write_corpus_coverage_report,
        write_corpus_state_snapshot,
    )
    from eubw_researcher.evaluation import load_eval_run_manifest
    from eubw_researcher.models import dataclass_to_dict
    from eubw_researcher.runtime_facade import ResearchRuntimeFacade

    catalog_path_for_snapshot = Path(args.catalog)
    catalog_path = resolve_catalog_path(repo_root, args.catalog)
    eval_manifest_path = (repo_root / args.eval_manifest).resolve()
    if not eval_manifest_path.is_file():
        raise SystemExit(f"Eval manifest not found: {eval_manifest_path}")
    output_dir = (repo_root / args.output_dir).resolve()
    if output_dir == repo_root:
        raise SystemExit("output-dir must not resolve to the repository root")
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog, _bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(
        catalog_path
    )

    selection_path = output_dir / "corpus_selection_summary.md"
    selection_path.write_text(
        render_corpus_selection_summary_md(catalog), encoding="utf-8"
    )

    coverage_report_path = None
    coverage_summary_path = None
    if coverage_report is not None:
        coverage_report_path = output_dir / "corpus_coverage_report.json"
        coverage_summary_path = output_dir / "corpus_coverage_summary.md"
        write_corpus_coverage_report(coverage_report, coverage_report_path)
        coverage_summary_path.write_text(
            render_corpus_coverage_summary_md(coverage_report), encoding="utf-8"
        )

    snapshot_path = output_dir / "corpus_state_snapshot.json"
    snapshot = build_corpus_state_snapshot(
        catalog,
        corpus_state_id,
        catalog_path_for_snapshot,
    )
    write_corpus_state_snapshot(snapshot, snapshot_path)

    eval_manifest = load_eval_run_manifest(eval_manifest_path)

    pack_manifest = None
    pack_manifest_path = None
    if args.real_question_pack_manifest:
        pack_manifest_path = (repo_root / args.real_question_pack_manifest).resolve()
        if not pack_manifest_path.is_file():
            raise SystemExit(
                f"Real-question pack manifest not found: {pack_manifest_path}"
            )
        pack_manifest = json.loads(pack_manifest_path.read_text(encoding="utf-8"))

    report = build_validated_current_state_report(
        snapshot,
        eval_manifest=eval_manifest,
        eval_manifest_path=eval_manifest_path,
        runtime_contract_version=ResearchRuntimeFacade.CONTRACT_VERSION,
        coverage_report_path=coverage_report_path,
        coverage_summary_path=coverage_summary_path,
        corpus_selection_summary_path=selection_path,
        corpus_state_snapshot_path=snapshot_path,
        real_question_pack_manifest=pack_manifest,
        real_question_pack_manifest_path=pack_manifest_path,
        git_metadata=_git_metadata(repo_root),
    )

    report_json_path = output_dir / "validated_current_state_report.json"
    report_markdown_path = output_dir / "validated_current_state_report.md"
    report_json_path.write_text(
        json.dumps(dataclass_to_dict(report), indent=2),
        encoding="utf-8",
    )
    report_markdown_path.write_text(
        render_validated_current_state_report_md(report),
        encoding="utf-8",
    )

    print(report_json_path)
    print(report_markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
