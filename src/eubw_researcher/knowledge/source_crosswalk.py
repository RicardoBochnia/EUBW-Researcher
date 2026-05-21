from __future__ import annotations

from eubw_researcher.models import SourceCatalog, SourceCrosswalkEntry


def build_source_crosswalk(catalog: SourceCatalog) -> list[SourceCrosswalkEntry]:
    entries: list[SourceCrosswalkEntry] = []
    for source in catalog.entries:
        legacy_source_ids = list(source.legacy_source_ids)
        if source.archive_source_id and source.archive_source_id not in legacy_source_ids:
            legacy_source_ids.append(source.archive_source_id)
        entries.append(
            SourceCrosswalkEntry(
                source_id=source.source_id,
                archive_source_id=source.archive_source_id,
                legacy_source_ids=legacy_source_ids,
                source_family_id=source.source_family_id,
                content_digest=source.content_digest,
            )
        )
    return entries

