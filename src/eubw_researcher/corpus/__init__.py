"""Curated corpus catalog and ingestion helpers."""

from .archive import build_catalog_from_archive
from .catalog import load_source_catalog, write_source_catalog
from .ingest import ingest_catalog, ingest_text_entry
from .runtime import (
    build_corpus_coverage_report,
    is_real_corpus_catalog,
    load_or_build_ingestion_bundle,
    write_corpus_coverage_report,
)

__all__ = [
    "build_catalog_from_archive",
    "build_corpus_coverage_report",
    "load_source_catalog",
    "is_real_corpus_catalog",
    "load_or_build_ingestion_bundle",
    "write_source_catalog",
    "write_corpus_coverage_report",
    "ingest_catalog",
    "ingest_text_entry",
]
