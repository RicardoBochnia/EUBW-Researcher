"""Curated corpus catalog and ingestion helpers."""

from .archive import build_catalog_from_archive
from .catalog import load_source_catalog, write_source_catalog
from .ingest import ingest_catalog, ingest_text_entry
from .refresh import (
    refresh_archive_sources,
    render_archive_refresh_report_markdown,
    write_archive_refresh_report,
)
from .reporting import (
    build_corpus_state_snapshot,
    render_corpus_coverage_summary_md,
    render_corpus_selection_summary_md,
    write_corpus_state_snapshot,
)
from .runtime import (
    build_corpus_coverage_report,
    is_real_corpus_catalog,
    load_or_build_ingestion_bundle,
    write_corpus_coverage_report,
)

__all__ = [
    "build_catalog_from_archive",
    "build_corpus_coverage_report",
    "build_corpus_state_snapshot",
    "load_source_catalog",
    "is_real_corpus_catalog",
    "load_or_build_ingestion_bundle",
    "refresh_archive_sources",
    "render_archive_refresh_report_markdown",
    "render_corpus_coverage_summary_md",
    "render_corpus_selection_summary_md",
    "write_source_catalog",
    "write_archive_refresh_report",
    "write_corpus_coverage_report",
    "write_corpus_state_snapshot",
    "ingest_catalog",
    "ingest_text_entry",
]
