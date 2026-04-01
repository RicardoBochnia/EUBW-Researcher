from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from eubw_researcher.models import ArchiveCorpusConfig, SourceCatalog, SourceCatalogEntry


def _load_archive_rows(catalog_path: Path) -> List[dict]:
    with catalog_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _resolve_archive_path(archive_root: Path, raw_path: str) -> Path:
    normalized = raw_path.replace("\\", "/")
    path = Path(normalized)
    parts = list(path.parts)
    if parts and parts[0] == "sources":
        parts = parts[1:]
    return (archive_root / Path(*parts)).resolve()


def build_catalog_from_archive(config: ArchiveCorpusConfig) -> SourceCatalog:
    rows = _load_archive_rows(config.archive_catalog)
    rows_by_id: Dict[str, dict] = {row["source_id"]: row for row in rows}

    entries: List[SourceCatalogEntry] = []
    for selection in config.sources:
        archive_row = rows_by_id.get(selection.archive_source_id)
        if archive_row is None:
            raise KeyError(
                f"Archive source {selection.archive_source_id} is missing from {config.archive_catalog}."
            )

        local_path = _resolve_archive_path(config.archive_root, archive_row["local_path"])
        if not local_path.exists():
            raise FileNotFoundError(
                f"Archive source {selection.archive_source_id} points to missing file {local_path}."
            )

        entries.append(
            SourceCatalogEntry(
                source_id=selection.source_id,
                title=selection.title,
                source_kind=selection.source_kind,
                source_role_level=selection.source_role_level,
                jurisdiction=selection.jurisdiction,
                publication_status=selection.publication_status,
                publication_date=selection.publication_date,
                local_path=local_path,
                canonical_url=archive_row.get("source_url"),
                source_origin=selection.source_origin,
                anchorability_hints=list(selection.anchorability_hints),
            )
        )

    return SourceCatalog(entries=entries)
