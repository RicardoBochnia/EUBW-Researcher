from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from eubw_researcher.models import (
    CorpusCoverageDelta,
    CorpusCoverageFamily,
    CorpusCoverageReport,
    CorpusManifest,
    CorpusManifestSource,
    CorpusRefreshSummary,
    CorpusSourceDelta,
    IngestionBundle,
    NormalizationStatus,
    SourceCatalog,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    dataclass_to_dict,
)


def default_corpus_manifest_path(catalog_path: Path) -> Path:
    return catalog_path.parent / "corpus_manifest.json"


def default_corpus_refresh_summary_path(catalog_path: Path) -> Path:
    return catalog_path.parent / "corpus_refresh_summary.json"


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolved_path_string(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    return path.resolve().as_posix()


def _report_lookup(bundle: Optional[IngestionBundle]) -> Dict[str, object]:
    if bundle is None:
        return {}
    return {entry.source_id: entry for entry in bundle.report}


def build_manifest_sources(
    catalog: SourceCatalog,
    *,
    bundle: Optional[IngestionBundle] = None,
) -> list[CorpusManifestSource]:
    report_by_id = _report_lookup(bundle)
    sources: list[CorpusManifestSource] = []
    for entry in sorted(catalog.entries, key=lambda item: item.source_id):
        report = report_by_id.get(entry.source_id)
        byte_size = None
        content_digest = None
        if entry.local_path is not None:
            byte_size = entry.local_path.stat().st_size
            content_digest = _file_digest(entry.local_path)
        sources.append(
            CorpusManifestSource(
                source_id=entry.source_id,
                title=entry.title,
                source_kind=entry.source_kind,
                source_role_level=entry.source_role_level,
                jurisdiction=entry.jurisdiction,
                publication_status=entry.publication_status,
                publication_date=entry.publication_date,
                source_origin=entry.source_origin,
                canonical_url=entry.canonical_url,
                local_path=_resolved_path_string(entry.local_path),
                anchorability_hints=list(entry.anchorability_hints),
                admission_reason=entry.admission_reason,
                content_digest=content_digest,
                byte_size=byte_size,
                normalization_status=getattr(report, "normalization_status", None),
                chunk_count=getattr(report, "chunk_count", None),
            )
        )
    return sources


def enrich_manifest_sources(
    sources: list[CorpusManifestSource],
    *,
    bundle: Optional[IngestionBundle] = None,
) -> list[CorpusManifestSource]:
    report_by_id = _report_lookup(bundle)
    enriched_sources: list[CorpusManifestSource] = []
    for source in sources:
        report = report_by_id.get(source.source_id)
        enriched_sources.append(
            CorpusManifestSource(
                source_id=source.source_id,
                title=source.title,
                source_kind=source.source_kind,
                source_role_level=source.source_role_level,
                jurisdiction=source.jurisdiction,
                publication_status=source.publication_status,
                publication_date=source.publication_date,
                source_origin=source.source_origin,
                canonical_url=source.canonical_url,
                local_path=source.local_path,
                anchorability_hints=list(source.anchorability_hints),
                admission_reason=source.admission_reason,
                content_digest=source.content_digest,
                byte_size=source.byte_size,
                normalization_status=getattr(report, "normalization_status", None),
                chunk_count=getattr(report, "chunk_count", None),
            )
        )
    return enriched_sources


def compute_corpus_state_id(sources: list[CorpusManifestSource]) -> str:
    digest = hashlib.sha256()
    for source in sources:
        payload = dataclass_to_dict(source)
        payload.pop("normalization_status", None)
        payload.pop("chunk_count", None)
        payload.pop("local_path", None)
        digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:16]


def build_corpus_manifest(
    catalog_path: Path,
    catalog: SourceCatalog,
    *,
    sources: Optional[list[CorpusManifestSource]] = None,
    corpus_state_id: Optional[str] = None,
    bundle: Optional[IngestionBundle] = None,
    coverage_report: Optional[CorpusCoverageReport] = None,
    selection_config_path: Optional[Path] = None,
) -> CorpusManifest:
    manifest_sources = sources if sources is not None else build_manifest_sources(catalog)
    manifest_sources = enrich_manifest_sources(manifest_sources, bundle=bundle)
    return CorpusManifest(
        catalog_path=str(catalog_path.resolve()),
        corpus_state_id=(
            corpus_state_id
            if corpus_state_id is not None
            else compute_corpus_state_id(manifest_sources)
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
        selection_config_path=(
            str(selection_config_path.resolve())
            if selection_config_path is not None
            else None
        ),
        sources=manifest_sources,
        coverage_passed=coverage_report.passed if coverage_report is not None else None,
        coverage_families=list(coverage_report.families) if coverage_report is not None else [],
    )


def _family_lookup(families: list[CorpusCoverageFamily]) -> Dict[str, CorpusCoverageFamily]:
    return {family.family_id: family for family in families}


def _delta_from_source(
    source: CorpusManifestSource,
    *,
    change_type: str,
    changed_fields: Optional[list[str]] = None,
    previous: Optional[CorpusManifestSource] = None,
) -> CorpusSourceDelta:
    return CorpusSourceDelta(
        source_id=source.source_id,
        title=source.title,
        change_type=change_type,
        changed_fields=sorted(changed_fields or []),
        source_origin=source.source_origin,
        canonical_url=source.canonical_url,
        previous_content_digest=previous.content_digest if previous is not None else None,
        current_content_digest=source.content_digest,
    )


def _source_field_map(source: CorpusManifestSource) -> dict[str, object]:
    payload = dataclass_to_dict(source)
    payload.pop("normalization_status", None)
    payload.pop("chunk_count", None)
    payload.pop("local_path", None)
    return payload


def build_corpus_refresh_summary(
    current_manifest: CorpusManifest,
    previous_manifest: Optional[CorpusManifest],
) -> CorpusRefreshSummary:
    previous_by_id = {
        source.source_id: source for source in (previous_manifest.sources if previous_manifest else [])
    }
    current_by_id = {source.source_id: source for source in current_manifest.sources}

    added_sources = [
        _delta_from_source(source, change_type="added")
        for source_id, source in current_by_id.items()
        if source_id not in previous_by_id
    ]
    removed_sources = [
        CorpusSourceDelta(
            source_id=source.source_id,
            title=source.title,
            change_type="removed",
            source_origin=source.source_origin,
            canonical_url=source.canonical_url,
            previous_content_digest=source.content_digest,
            current_content_digest=None,
        )
        for source_id, source in previous_by_id.items()
        if source_id not in current_by_id
    ]

    updated_sources: list[CorpusSourceDelta] = []
    for source_id in sorted(set(previous_by_id) & set(current_by_id)):
        previous_source = previous_by_id[source_id]
        current_source = current_by_id[source_id]
        previous_payload = _source_field_map(previous_source)
        current_payload = _source_field_map(current_source)
        changed_fields = [
            field_name
            for field_name in sorted(set(previous_payload) | set(current_payload))
            if previous_payload.get(field_name) != current_payload.get(field_name)
        ]
        if changed_fields:
            updated_sources.append(
                _delta_from_source(
                    current_source,
                    change_type="updated",
                    changed_fields=changed_fields,
                    previous=previous_source,
                )
            )

    changed_web_sources = [
        item
        for item in [*added_sources, *removed_sources, *updated_sources]
        if item.source_origin == SourceOrigin.WEB
    ]

    coverage_deltas: list[CorpusCoverageDelta] = []
    previous_families = _family_lookup(previous_manifest.coverage_families) if previous_manifest else {}
    current_families = _family_lookup(current_manifest.coverage_families)
    for family_id in sorted(set(previous_families) | set(current_families)):
        previous_family = previous_families.get(family_id)
        current_family = current_families.get(family_id)
        previous_admitted_count = previous_family.admitted_count if previous_family is not None else 0
        current_admitted_count = current_family.admitted_count if current_family is not None else 0
        previous_missing = previous_family.missing if previous_family is not None else True
        current_missing = current_family.missing if current_family is not None else True
        if (
            previous_admitted_count != current_admitted_count
            or previous_missing != current_missing
        ):
            coverage_deltas.append(
                CorpusCoverageDelta(
                    family_id=family_id,
                    previous_admitted_count=previous_admitted_count,
                    current_admitted_count=current_admitted_count,
                    previous_missing=previous_missing,
                    current_missing=current_missing,
                )
            )

    refresh_status = "initial_build"
    previous_corpus_state_id = previous_manifest.corpus_state_id if previous_manifest else None
    if previous_manifest is not None:
        refresh_status = (
            "unchanged"
            if previous_manifest.corpus_state_id == current_manifest.corpus_state_id
            else "refreshed"
        )

    return CorpusRefreshSummary(
        catalog_path=current_manifest.catalog_path,
        corpus_state_id=current_manifest.corpus_state_id,
        previous_corpus_state_id=previous_corpus_state_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        refresh_status=refresh_status,
        selection_config_path=current_manifest.selection_config_path,
        added_sources=added_sources,
        removed_sources=removed_sources,
        updated_sources=updated_sources,
        changed_web_sources=changed_web_sources,
        coverage_deltas=coverage_deltas,
    )


def write_corpus_manifest(manifest: CorpusManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclass_to_dict(manifest), indent=2), encoding="utf-8")


def write_corpus_refresh_summary(summary: CorpusRefreshSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclass_to_dict(summary), indent=2), encoding="utf-8")


def _load_family(payload: dict) -> CorpusCoverageFamily:
    return CorpusCoverageFamily(
        family_id=payload["family_id"],
        minimum_count=int(payload["minimum_count"]),
        admitted_count=int(payload["admitted_count"]),
        admitted_source_ids=list(payload.get("admitted_source_ids", [])),
        missing=bool(payload["missing"]),
    )


def _load_manifest_source(payload: dict) -> CorpusManifestSource:
    normalization_status = payload.get("normalization_status")
    return CorpusManifestSource(
        source_id=payload["source_id"],
        title=payload["title"],
        source_kind=SourceKind(payload["source_kind"]),
        source_role_level=SourceRoleLevel(payload["source_role_level"]),
        jurisdiction=payload["jurisdiction"],
        publication_status=payload.get("publication_status"),
        publication_date=payload.get("publication_date"),
        source_origin=SourceOrigin(payload.get("source_origin", "local")),
        canonical_url=payload.get("canonical_url"),
        local_path=payload.get("local_path"),
        anchorability_hints=list(payload.get("anchorability_hints", [])),
        admission_reason=payload.get("admission_reason"),
        content_digest=payload.get("content_digest"),
        byte_size=payload.get("byte_size"),
        normalization_status=(
            NormalizationStatus(normalization_status)
            if normalization_status is not None
            else None
        ),
        chunk_count=payload.get("chunk_count"),
    )


def load_corpus_manifest(path: Path) -> Optional[CorpusManifest]:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CorpusManifest(
        catalog_path=payload["catalog_path"],
        corpus_state_id=payload["corpus_state_id"],
        generated_at=payload["generated_at"],
        selection_config_path=payload.get("selection_config_path"),
        sources=[_load_manifest_source(item) for item in payload.get("sources", [])],
        coverage_passed=payload.get("coverage_passed"),
        coverage_families=[_load_family(item) for item in payload.get("coverage_families", [])],
    )


def _load_source_delta(payload: dict) -> CorpusSourceDelta:
    source_origin = payload.get("source_origin")
    return CorpusSourceDelta(
        source_id=payload["source_id"],
        title=payload["title"],
        change_type=payload["change_type"],
        changed_fields=list(payload.get("changed_fields", [])),
        source_origin=SourceOrigin(source_origin) if source_origin is not None else None,
        canonical_url=payload.get("canonical_url"),
        previous_content_digest=payload.get("previous_content_digest"),
        current_content_digest=payload.get("current_content_digest"),
    )


def load_corpus_refresh_summary(path: Path) -> Optional[CorpusRefreshSummary]:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CorpusRefreshSummary(
        catalog_path=payload["catalog_path"],
        corpus_state_id=payload["corpus_state_id"],
        previous_corpus_state_id=payload.get("previous_corpus_state_id"),
        generated_at=payload["generated_at"],
        refresh_status=payload["refresh_status"],
        selection_config_path=payload.get("selection_config_path"),
        added_sources=[_load_source_delta(item) for item in payload.get("added_sources", [])],
        removed_sources=[_load_source_delta(item) for item in payload.get("removed_sources", [])],
        updated_sources=[_load_source_delta(item) for item in payload.get("updated_sources", [])],
        changed_web_sources=[_load_source_delta(item) for item in payload.get("changed_web_sources", [])],
        coverage_deltas=[
            CorpusCoverageDelta(
                family_id=item["family_id"],
                previous_admitted_count=int(item["previous_admitted_count"]),
                current_admitted_count=int(item["current_admitted_count"]),
                previous_missing=bool(item["previous_missing"]),
                current_missing=bool(item["current_missing"]),
            )
            for item in payload.get("coverage_deltas", [])
        ],
    )
