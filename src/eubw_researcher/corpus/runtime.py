from __future__ import annotations

import hashlib
import json
import pickle
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from eubw_researcher.corpus.catalog import load_source_catalog
from eubw_researcher.corpus.ingest import ingest_catalog
from eubw_researcher.models import (
    CorpusCoverageFamily,
    CorpusCoverageReport,
    IngestionBundle,
    NormalizationStatus,
    SourceCatalog,
    SourceCatalogEntry,
    SourceKind,
    dataclass_to_dict,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching


def is_real_corpus_catalog(catalog_path: Optional[Path]) -> bool:
    return (
        catalog_path is not None
        and "real_corpus" in catalog_path.parts
        and catalog_path.name == "curated_catalog.json"
    )


def _catalog_state_id(catalog_path: Path, catalog: SourceCatalog) -> str:
    digest = hashlib.sha256()
    digest.update(catalog_path.resolve().as_posix().encode("utf-8"))
    digest.update(catalog_path.read_bytes())
    for entry in sorted(catalog.entries, key=lambda item: item.source_id):
        digest.update(entry.source_id.encode("utf-8"))
        digest.update(entry.title.encode("utf-8"))
        digest.update(entry.source_kind.value.encode("utf-8"))
        if entry.local_path:
            digest.update(entry.local_path.resolve().as_posix().encode("utf-8"))
            stat = entry.local_path.stat()
            digest.update(str(stat.st_size).encode("utf-8"))
            digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return digest.hexdigest()[:16]


def _cache_paths(catalog_path: Path) -> tuple[Path, Path]:
    cache_dir = catalog_path.parent / "cache"
    return cache_dir / "normalized_bundle.pkl", cache_dir / "normalized_bundle_meta.json"


def _entry_is_admitted(entry) -> bool:
    return (
        entry.normalization_status == NormalizationStatus.SUCCESS
        and entry.chunk_count > 0
    )


def _matches_arf(entry: SourceCatalogEntry) -> bool:
    lowered = normalize_text_for_matching(f"{entry.source_id} {entry.title}")
    return "arf" in lowered or "architecture and reference framework" in lowered


def _matches_rp_project(entry: SourceCatalogEntry) -> bool:
    if entry.source_kind != SourceKind.PROJECT_ARTIFACT:
        return False
    lowered = normalize_text_for_matching(f"{entry.source_id} {entry.title}")
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


def _matches_germany_legal_or_legislative(entry: SourceCatalogEntry) -> bool:
    if entry.jurisdiction != "DE":
        return False
    lowered = normalize_text_for_matching(f"{entry.source_id} {entry.title}")
    return any(
        token in lowered
        for token in [
            "de_law_",
            "de_parliament_",
            "bundestag",
            "drucksache",
            "gesetz",
            "durchfuehrungsgesetz",
        ]
    )


def _matches_germany_wallet_delivery(entry: SourceCatalogEntry) -> bool:
    if entry.jurisdiction != "DE":
        return False
    lowered = normalize_text_for_matching(f"{entry.source_id} {entry.title}")
    return entry.source_kind == SourceKind.PROJECT_ARTIFACT or any(
        token in lowered
        for token in [
            "de_sprind_",
            "sprind",
            "wallet",
            "eudi",
            "digitale identitaet",
            "digitale brieftasche",
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
    if any(entry.jurisdiction == "DE" for entry in bundle.catalog.entries):
        families.extend(
            [
                family(
                    "germany_legislative_or_legal_sources",
                    2,
                    _matches_germany_legal_or_legislative,
                ),
                family(
                    "germany_wallet_delivery_sources",
                    2,
                    _matches_germany_wallet_delivery,
                ),
            ]
        )

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


def write_corpus_state_snapshot(snapshot: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def load_or_build_ingestion_bundle(
    catalog_path: Path,
) -> Tuple[SourceCatalog, IngestionBundle, Optional[CorpusCoverageReport], str]:
    catalog = load_source_catalog(catalog_path)
    corpus_state_id = _catalog_state_id(catalog_path, catalog)

    if not is_real_corpus_catalog(catalog_path):
        bundle = ingest_catalog(catalog)
        return catalog, bundle, None, corpus_state_id

    bundle_cache_path, metadata_path = _cache_paths(catalog_path)
    bundle_cache_path.parent.mkdir(parents=True, exist_ok=True)

    bundle: Optional[IngestionBundle] = None
    if bundle_cache_path.exists() and metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("corpus_state_id") == corpus_state_id:
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
                    "corpus_state_id": corpus_state_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    coverage_report = build_corpus_coverage_report(
        catalog_path=catalog_path,
        bundle=bundle,
        corpus_state_id=corpus_state_id,
    )
    return catalog, bundle, coverage_report, corpus_state_id
