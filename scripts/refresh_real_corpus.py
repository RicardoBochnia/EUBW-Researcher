from __future__ import annotations

import argparse
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
        "--allowlist",
        default="configs/web_allowlist.yaml",
        help="Allowlisted official-source policy config for refresh checks.",
    )
    parser.add_argument(
        "--runtime-config",
        default="configs/runtime.yaml",
        help="Runtime config used for bounded refresh fetches.",
    )
    parser.add_argument(
        "--stage-dir",
        default="artifacts/real_corpus/refresh_staging",
        help="Where to stage changed or missing source candidates.",
    )
    parser.add_argument(
        "--report",
        default="artifacts/real_corpus/refresh_staging/refresh_report.json",
        help="Where to write the machine-readable refresh report.",
    )
    parser.add_argument(
        "--report-markdown",
        default="artifacts/real_corpus/refresh_staging/refresh_report.md",
        help="Where to write the human-readable refresh report.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply staged updates to the accepted local archive and update the archive catalog metadata.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.config import (
        load_archive_corpus_config,
        load_runtime_config,
        load_web_allowlist,
    )
    from eubw_researcher.corpus import (
        refresh_archive_sources,
        render_archive_refresh_report_markdown,
        write_archive_refresh_report,
    )

    config_path = (repo_root / args.config).resolve()
    config = load_archive_corpus_config(config_path)
    allowlist = load_web_allowlist((repo_root / args.allowlist).resolve())
    runtime_config = load_runtime_config((repo_root / args.runtime_config).resolve())
    report = refresh_archive_sources(
        config,
        allowlist,
        runtime_config,
        stage_root=(repo_root / args.stage_dir).resolve(),
        config_path=config_path,
        apply_updates=args.apply,
    )

    report_path = (repo_root / args.report).resolve()
    write_archive_refresh_report(report, report_path)
    report_markdown_path = (repo_root / args.report_markdown).resolve()
    report_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    report_markdown_path.write_text(
        render_archive_refresh_report_markdown(report),
        encoding="utf-8",
    )

    print(report_markdown_path)
    if report.failed_sources > 0:
        print(
            f"Refresh completed with {report.failed_sources} failed source fetch(es). "
            f"See report: {report_markdown_path}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
