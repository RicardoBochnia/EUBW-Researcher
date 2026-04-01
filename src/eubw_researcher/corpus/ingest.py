from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from eubw_researcher.corpus.normalize import normalize_local_source
from eubw_researcher.models import (
    AnchorAudit,
    AnchorQuality,
    Citation,
    CitationQuality,
    IngestionBundle,
    IngestionReportEntry,
    NormalizationStatus,
    SourceCatalog,
    SourceCatalogEntry,
    SourceChunk,
    SourceDocument,
)

LOGGER = logging.getLogger(__name__)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STRONG_ANCHOR_RE = re.compile(r"^(article|section|clause|annex|chapter)\b", re.IGNORECASE)
NUMBERED_ANCHOR_RE = re.compile(r"^((\d+(\.\d+)+)|appendix\s+[a-z0-9]+)\b", re.IGNORECASE)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "chunk"


def _parse_markdown_sections(text: str) -> Tuple[List[Tuple[List[str], str]], List[str]]:
    stack: List[Tuple[int, str]] = []
    buffer: List[str] = []
    sections: List[Tuple[List[str], str]] = []
    headings: List[str] = []

    def flush() -> None:
        if not stack:
            return
        content = "\n".join(buffer).strip()
        if content:
            sections.append(([item[1] for item in stack], content))

    for raw_line in text.splitlines():
        match = HEADING_RE.match(raw_line)
        if match:
            flush()
            buffer = []
            level = len(match.group(1))
            heading = match.group(2).strip()
            headings.append(heading)
            stack = [item for item in stack if item[0] < level]
            stack.append((level, heading))
        else:
            buffer.append(raw_line)

    flush()
    return sections, headings


def ingest_text_entry(
    entry: SourceCatalogEntry,
    text: str,
    normalization_format: Optional[str] = None,
    normalization_note: Optional[str] = None,
) -> Tuple[SourceDocument, IngestionReportEntry]:
    sections, headings = _parse_markdown_sections(text)
    word_count = len(text.split())

    expects_section_anchors = any(
        hint in entry.anchorability_hints
        for hint in ["section_level", "article_level", "expect_anchors"]
    )
    if any(STRONG_ANCHOR_RE.match(item) for item in headings) or (
        expects_section_anchors and any(NUMBERED_ANCHOR_RE.match(item) for item in headings)
    ):
        anchor_quality = AnchorQuality.STRONG
    elif headings:
        anchor_quality = AnchorQuality.WEAK
    else:
        anchor_quality = AnchorQuality.MISSING

    expected_anchorable = "expect_anchors" in entry.anchorability_hints
    parser_or_structure_limitation = (
        expected_anchorable and anchor_quality == AnchorQuality.MISSING and word_count >= 80
    )
    structure_poor = anchor_quality == AnchorQuality.MISSING and not parser_or_structure_limitation
    anchor_audit = AnchorAudit(
        expected_anchorable=expected_anchorable,
        content_retrievable=bool(text),
        parser_or_structure_limitation=parser_or_structure_limitation,
        structure_poor=structure_poor,
        audit_note=(
            "Provision-like anchors available."
            if anchor_quality == AnchorQuality.STRONG
            else "Generic headings only; degrade to document-only citations and do not treat the source as a technical anchor-extraction failure."
            if anchor_quality == AnchorQuality.WEAK
            else "Expected anchors were not recoverable, but the governing document content is retrievable; treat this as a technical extraction failure only if the claim remains directly supported at document level."
            if parser_or_structure_limitation
            else "No usable internal anchors; render as full-document citation only."
        ),
    )
    technical_anchor_failure = (
        anchor_audit.parser_or_structure_limitation
        and anchor_audit.is_document_only_confirmable()
    )

    chunks: List[SourceChunk] = []
    if sections:
        for path_labels, content in sections:
            anchor_label = " > ".join(path_labels)
            citation_quality = (
                CitationQuality.ANCHOR_GROUNDED
                if anchor_quality == AnchorQuality.STRONG
                else CitationQuality.DOCUMENT_ONLY
            )
            citation = Citation(
                source_id=entry.source_id,
                document_title=entry.title,
                source_role_level=entry.source_role_level,
                source_kind=entry.source_kind,
                jurisdiction=entry.jurisdiction,
                citation_quality=citation_quality,
                document_path=entry.local_path,
                canonical_url=entry.canonical_url,
                source_origin=entry.source_origin,
                anchor_label=anchor_label
                if citation_quality == CitationQuality.ANCHOR_GROUNDED
                else None,
                structure_poor=False,
                anchor_audit_note=anchor_audit.audit_note,
            )
            chunks.append(
                SourceChunk(
                    source_id=entry.source_id,
                    chunk_id=f"{entry.source_id}::{_slugify(anchor_label)}",
                    title=entry.title,
                    source_kind=entry.source_kind,
                    source_role_level=entry.source_role_level,
                    source_origin=entry.source_origin,
                    jurisdiction=entry.jurisdiction,
                    text=f"{entry.title}\n{anchor_label}\n{content}",
                    citation=citation,
                    technical_anchor_failure=technical_anchor_failure,
                    anchor_quality=anchor_quality,
                    extracted_anchor_label=anchor_label,
                    anchor_audit=anchor_audit,
                )
            )
    else:
        citation = Citation(
            source_id=entry.source_id,
            document_title=entry.title,
            source_role_level=entry.source_role_level,
            source_kind=entry.source_kind,
            jurisdiction=entry.jurisdiction,
            citation_quality=CitationQuality.DOCUMENT_ONLY,
            document_path=entry.local_path,
            canonical_url=entry.canonical_url,
            source_origin=entry.source_origin,
            structure_poor=structure_poor,
            anchor_audit_note=anchor_audit.audit_note,
        )
        chunks.append(
            SourceChunk(
                source_id=entry.source_id,
                chunk_id=f"{entry.source_id}::document",
                title=entry.title,
                source_kind=entry.source_kind,
                source_role_level=entry.source_role_level,
                source_origin=entry.source_origin,
                jurisdiction=entry.jurisdiction,
                text=f"{entry.title}\n{text}",
                citation=citation,
                technical_anchor_failure=technical_anchor_failure,
                anchor_quality=anchor_quality,
                extracted_anchor_label=None,
                anchor_audit=anchor_audit,
            )
        )

    document = SourceDocument(
        entry=entry,
        text=text,
        chunks=chunks,
        anchor_quality=anchor_quality,
        structure_poor=structure_poor,
        technical_anchor_failure=technical_anchor_failure,
        anchor_audit=anchor_audit,
    )
    report = IngestionReportEntry(
        source_id=entry.source_id,
        title=entry.title,
        source_kind=entry.source_kind,
        source_role_level=entry.source_role_level,
        jurisdiction=entry.jurisdiction,
        anchor_quality=anchor_quality,
        structure_poor=structure_poor,
        citation_quality=chunks[0].citation_quality,
        technical_anchor_failure=technical_anchor_failure,
        anchor_audit_note=anchor_audit.audit_note,
        chunk_count=len(chunks),
        local_path=entry.local_path,
        normalization_status=NormalizationStatus.SUCCESS,
        normalization_format=normalization_format,
        normalization_note=normalization_note,
    )
    return document, report


def ingest_catalog(catalog: SourceCatalog) -> IngestionBundle:
    documents: List[SourceDocument] = []
    report: List[IngestionReportEntry] = []

    for entry in catalog.entries:
        try:
            if not entry.local_path:
                raise ValueError(f"Source {entry.source_id} is missing a local_path.")
            text, _, normalization_format, normalization_note = normalize_local_source(entry.local_path)
            document, report_entry = ingest_text_entry(
                entry,
                text,
                normalization_format=normalization_format,
                normalization_note=normalization_note,
            )
            LOGGER.info(
                "Ingested %s with %s anchors and %s chunk(s).",
                entry.source_id,
                document.anchor_quality,
                len(document.chunks),
            )
            documents.append(document)
            report.append(report_entry)
        except Exception as exc:
            LOGGER.warning("Failed to normalize %s: %s", entry.source_id, exc)
            report.append(
                IngestionReportEntry(
                    source_id=entry.source_id,
                    title=entry.title,
                    source_kind=entry.source_kind,
                    source_role_level=entry.source_role_level,
                    jurisdiction=entry.jurisdiction,
                    anchor_quality=AnchorQuality.MISSING,
                    structure_poor=True,
                    citation_quality=CitationQuality.DOCUMENT_ONLY,
                    technical_anchor_failure=False,
                    anchor_audit_note=f"Normalization failure: {exc}",
                    chunk_count=0,
                    local_path=entry.local_path,
                    normalization_status=NormalizationStatus.FAILED,
                    normalization_format=(entry.local_path.suffix.lstrip(".") if entry.local_path else None),
                    normalization_note=str(exc),
                )
            )

    return IngestionBundle(catalog=catalog, documents=documents, report=report)
