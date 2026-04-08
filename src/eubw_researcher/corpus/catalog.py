from __future__ import annotations

import json
from pathlib import Path

from eubw_researcher.models import (
    DocumentStatus,
    SourceCatalog,
    SourceCatalogEntry,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
)


def load_source_catalog(path: Path) -> SourceCatalog:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    entries = []
    for item in payload["sources"]:
        local_path = item.get("local_path")
        resolved_path = None
        if local_path:
            path_obj = Path(local_path)
            resolved_path = path_obj if path_obj.is_absolute() else (path.parent / path_obj).resolve()
        entries.append(
            SourceCatalogEntry(
                source_id=item["source_id"],
                title=item["title"],
                source_kind=SourceKind(item["source_kind"]),
                source_role_level=SourceRoleLevel(item["source_role_level"]),
                jurisdiction=item["jurisdiction"],
                publication_status=item.get("publication_status"),
                publication_date=item.get("publication_date"),
                local_path=resolved_path,
                canonical_url=item.get("canonical_url"),
                document_status=DocumentStatus(item.get("document_status", "final")),
                source_origin=SourceOrigin(item.get("source_origin", "local")),
                anchorability_hints=list(item.get("anchorability_hints", [])),
                admission_reason=item.get("admission_reason"),
                source_family_id=item.get("source_family_id"),
            )
        )
    return SourceCatalog(entries=entries)


def write_source_catalog(catalog: SourceCatalog, path: Path) -> None:
    payload = {
        "sources": [
            {
                "source_id": entry.source_id,
                "title": entry.title,
                "source_kind": entry.source_kind.value,
                "source_role_level": entry.source_role_level.value,
                "jurisdiction": entry.jurisdiction,
                "publication_status": entry.publication_status,
                "publication_date": entry.publication_date,
                "local_path": str(entry.local_path) if entry.local_path else None,
                "canonical_url": entry.canonical_url,
                "document_status": entry.document_status.value,
                "source_origin": entry.source_origin.value,
                "anchorability_hints": list(entry.anchorability_hints),
                "admission_reason": entry.admission_reason,
                "source_family_id": entry.source_family_id,
            }
            for entry in catalog.entries
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
