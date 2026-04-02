"""Curated corpus catalog and ingestion helpers."""

from .archive import build_catalog_from_archive
from .catalog import load_source_catalog, write_source_catalog
from .freshness import (
    build_manifest_sources,
    build_corpus_manifest,
    build_corpus_refresh_summary,
    compute_corpus_state_id,
    default_corpus_manifest_path,
    default_corpus_refresh_summary_path,
    enrich_manifest_sources,
    load_corpus_manifest,
    load_corpus_refresh_summary,
    write_corpus_manifest,
    write_corpus_refresh_summary,
)
from .ingest import ingest_catalog, ingest_text_entry
from .runtime import (
    build_corpus_coverage_report,
    is_real_corpus_catalog,
    load_or_build_ingestion_bundle,
    write_corpus_coverage_report,
)

__all__ = [
    "build_catalog_from_archive",
    "build_manifest_sources",
    "build_corpus_manifest",
    "build_corpus_coverage_report",
    "build_corpus_refresh_summary",
    "compute_corpus_state_id",
    "default_corpus_manifest_path",
    "default_corpus_refresh_summary_path",
    "enrich_manifest_sources",
    "load_source_catalog",
    "load_corpus_manifest",
    "load_corpus_refresh_summary",
    "is_real_corpus_catalog",
    "load_or_build_ingestion_bundle",
    "write_source_catalog",
    "write_corpus_manifest",
    "write_corpus_coverage_report",
    "write_corpus_refresh_summary",
    "ingest_catalog",
    "ingest_text_entry",
]
