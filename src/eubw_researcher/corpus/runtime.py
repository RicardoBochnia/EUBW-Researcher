from __future__ import annotations

import json
import pickle
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from eubw_researcher.corpus.catalog import load_source_catalog
from eubw_researcher.corpus.freshness import (
    build_manifest_sources,
    compute_corpus_state_id,
    default_corpus_manifest_path,
    load_corpus_manifest,
)
from eubw_researcher.corpus.ingest import ingest_catalog
from eubw_researcher.models import (
    CorpusManifestSource,
    CorpusCoverageFamily,
    CorpusCoverageReport,
    IngestionBundle,
    NormalizationStatus,
    SourceCatalog,
    SourceCatalogEntry,
    SourceKind,
    dataclass_to_dict,
)


def is_real_corpus_catalog(catalog_path: Optional[Path]) -> bool:
    return (
        catalog_path is not None
        and "real_corpus" in catalog_path.parts
        and catalog_path.name == "curated_catalog.json"
    )


def _catalog_state_id(catalog_path: Path, catalog: SourceCatalog) -> str:
    del catalog_path
    return compute_corpus_state_id(build_manifest_sources(catalog))


def _cache_paths(catalog_path: Path) -> tuple[Path, Path]:
    cache_dir = catalog_path.parent / "cache"
    return cache_dir / "normalized_bundle.pkl", cache_dir / "normalized_bundle_meta.json"


def _cache_artifact_is_current(
    catalog_path: Path,
    catalog: SourceCatalog,
    artifact_path: Path,
) -> bool:
    try:
        artifact_mtime = artifact_path.stat().st_mtime_ns
        if catalog_path.stat().st_mtime_ns > artifact_mtime:
            return False
    except OSError:
        return False

    for entry in catalog.entries:
        if entry.local_path is None:
            continue
        try:
            if entry.local_path.stat().st_mtime_ns > artifact_mtime:
                return False
        except OSError:
            return False
    return True


def _load_cached_corpus_state_id(
    catalog_path: Path,
    catalog: SourceCatalog,
) -> Optional[str]:
    resolved_catalog_path = str(catalog_path.resolve())
    catalog_source_ids = {entry.source_id for entry in catalog.entries}
    manifest_path = default_corpus_manifest_path(catalog_path)
    if manifest_path.exists() and _cache_artifact_is_current(catalog_path, catalog, manifest_path):
        manifest = load_corpus_manifest(manifest_path)
        manifest_source_ids = (
            {source.source_id for source in manifest.sources}
            if manifest is not None
            else set()
        )
        if (
            manifest is not None
            and manifest.corpus_state_id
            and manifest.catalog_path == resolved_catalog_path
            and manifest_source_ids == catalog_source_ids
        ):
            return manifest.corpus_state_id

    _, metadata_path = _cache_paths(catalog_path)
    if metadata_path.exists() and _cache_artifact_is_current(catalog_path, catalog, metadata_path):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None
        corpus_state_id = metadata.get("corpus_state_id")
        if (
            isinstance(corpus_state_id, str)
            and corpus_state_id
            and metadata.get("catalog_path") == resolved_catalog_path
        ):
            return corpus_state_id
    return None


def _entry_is_admitted(entry) -> bool:
    return (
        entry.normalization_status == NormalizationStatus.SUCCESS
        and entry.chunk_count > 0
    )


def _matches_arf(entry: SourceCatalogEntry) -> bool:
    lowered = f"{entry.source_id} {entry.title}".lower()
    return "arf" in lowered or "architecture and reference framework" in lowered


def _matches_rp_project(entry: SourceCatalogEntry) -> bool:
    if entry.source_kind != SourceKind.PROJECT_ARTIFACT:
        return False
    lowered = f"{entry.source_id} {entry.title}".lower()
    return any(
        token in lowered
        for token in [
            "relying party",
            "rp_",
            "rp ",
            "registration api",
            "registration information",
            "information to be registered",
        ]
    )


def build_corpus_coverage_report(
    catalog_path: Path,
    bundle: IngestionBundle,
    corpus_state_id: str,
) -> CorpusCoverageReport:
    entries_by_id = bundle.catalog.by_id()
    admitted_reports = [entry for entry in bundle.report if _entry_is_admitted(entry)]
    admitted_entries = [entries_by_id[item.source_id] for item in admitted_reports if item.source_id in entries_by_id]

    admitted_counts_by_kind = Counter(entry.source_kind.value for entry in admitted_entries)

    def family(
        family_id: str,
        minimum_count: int,
        matcher,
    ) -> CorpusCoverageFamily:
        source_ids = sorted(entry.source_id for entry in admitted_entries if matcher(entry))
        return CorpusCoverageFamily(
            family_id=family_id,
            minimum_count=minimum_count,
            admitted_count=len(source_ids),
            admitted_source_ids=source_ids,
            missing=len(source_ids) < minimum_count,
        )

    families = [
        family(
            "governing_eu_regulation",
            1,
            lambda entry: entry.source_kind == SourceKind.REGULATION,
        ),
        family(
            "implementing_act_or_annex",
            1,
            lambda entry: entry.source_kind == SourceKind.IMPLEMENTING_ACT,
        ),
        family(
            "current_technical_standards",
            2,
            lambda entry: entry.source_kind == SourceKind.TECHNICAL_STANDARD,
        ),
        family(
            "arf_source",
            1,
            _matches_arf,
        ),
        family(
            "official_project_artifacts_registration_information",
            2,
            _matches_rp_project,
        ),
    ]

    passed = all(not family_report.missing for family_report in families)
    return CorpusCoverageReport(
        catalog_path=str(catalog_path.resolve()),
        corpus_state_id=corpus_state_id,
        generation_timestamp=datetime.now(timezone.utc).isoformat(),
        admitted_source_counts_by_kind=dict(sorted(admitted_counts_by_kind.items())),
        families=families,
        passed=passed,
    )


def write_corpus_coverage_report(report: CorpusCoverageReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclass_to_dict(report), indent=2), encoding="utf-8")


def load_or_build_ingestion_bundle(
    catalog_path: Path,
    *,
    manifest_sources: Optional[list[CorpusManifestSource]] = None,
    corpus_state_id: Optional[str] = None,
) -> Tuple[SourceCatalog, IngestionBundle, Optional[CorpusCoverageReport], str]:
    catalog = load_source_catalog(catalog_path)
    resolved_corpus_state_id = corpus_state_id
    if resolved_corpus_state_id is None:
        if manifest_sources is not None:
            resolved_corpus_state_id = compute_corpus_state_id(manifest_sources)
        elif is_real_corpus_catalog(catalog_path):
            resolved_corpus_state_id = _load_cached_corpus_state_id(catalog_path, catalog)
            if resolved_corpus_state_id is None:
                resolved_corpus_state_id = _catalog_state_id(catalog_path, catalog)
        else:
            resolved_corpus_state_id = _catalog_state_id(catalog_path, catalog)

    if not is_real_corpus_catalog(catalog_path):
        bundle = ingest_catalog(catalog)
        return catalog, bundle, None, resolved_corpus_state_id

    bundle_cache_path, metadata_path = _cache_paths(catalog_path)
    bundle_cache_path.parent.mkdir(parents=True, exist_ok=True)

    bundle: Optional[IngestionBundle] = None
    if bundle_cache_path.exists() and metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("corpus_state_id") == resolved_corpus_state_id:
                with bundle_cache_path.open("rb") as handle:
                    bundle = pickle.load(handle)
        except Exception:
            bundle = None

    if bundle is None:
        bundle = ingest_catalog(catalog)
        with bundle_cache_path.open("wb") as handle:
            pickle.dump(bundle, handle)
        metadata_path.write_text(
            json.dumps(
                {
                    "catalog_path": str(catalog_path.resolve()),
                    "corpus_state_id": resolved_corpus_state_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    coverage_report = build_corpus_coverage_report(
        catalog_path=catalog_path,
        bundle=bundle,
        corpus_state_id=resolved_corpus_state_id,
    )
    return catalog, bundle, coverage_report, resolved_corpus_state_id
