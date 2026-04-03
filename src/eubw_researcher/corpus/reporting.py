from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List

from eubw_researcher.models import (
    CorpusCoverageReport,
    SourceCatalog,
    SourceKind,
    SourceRoleLevel,
)

_ROLE_LEVEL_ORDER: List[SourceRoleLevel] = [
    SourceRoleLevel.HIGH,
    SourceRoleLevel.MEDIUM,
    SourceRoleLevel.LOW,
]

_KIND_ORDER: List[SourceKind] = list(SourceKind)


def render_corpus_selection_summary_md(catalog: SourceCatalog) -> str:
    """Compact markdown listing of all selected sources.

    Grouped by role_level (high → medium → low), then by source_kind.
    Each source shows title, source_kind, jurisdiction, and admission_reason.
    """
    lines: List[str] = []
    lines.append("# Corpus Selection Summary")
    lines.append("")
    lines.append(f"**Total sources:** {len(catalog.entries)}")

    for role_level in _ROLE_LEVEL_ORDER:
        level_entries = [e for e in catalog.entries if e.source_role_level == role_level]
        if not level_entries:
            continue
        lines.append("")
        lines.append(f"## {role_level.value.capitalize()}-rank sources")

        for kind in _KIND_ORDER:
            kind_entries = sorted(
                [e for e in level_entries if e.source_kind == kind],
                key=lambda e: e.source_id,
            )
            if not kind_entries:
                continue
            lines.append("")
            lines.append(f"### {kind.value} ({len(kind_entries)})")
            lines.append("")
            lines.append("| Source | Kind | Jurisdiction | Admission reason |")
            lines.append("|--------|------|-------------|-----------------|")
            for entry in kind_entries:
                reason = (entry.admission_reason or "").replace("|", "\\|")
                title = entry.title.replace("|", "\\|")
                lines.append(f"| {title} | {entry.source_kind.value} | {entry.jurisdiction} | {reason} |")

    lines.append("")
    return "\n".join(lines)


def render_corpus_coverage_summary_md(report: CorpusCoverageReport) -> str:
    """Human-readable markdown coverage summary.

    Shows overall PASS/FAIL, corpus_state_id, counts by kind, and
    per-family admission status.
    """
    overall = "PASS" if report.passed else "FAIL"
    lines: List[str] = []
    lines.append("# Corpus Coverage Summary")
    lines.append("")
    lines.append(f"**Corpus state:** `{report.corpus_state_id}`")
    lines.append(f"**Overall:** {overall}")
    lines.append("")

    lines.append("## Admitted sources by kind")
    lines.append("")
    lines.append("| Kind | Count |")
    lines.append("|------|-------|")
    for kind in _KIND_ORDER:
        count = report.admitted_source_counts_by_kind.get(kind.value, 0)
        if count:
            lines.append(f"| {kind.value} | {count} |")
    lines.append("")

    lines.append("## Coverage families")
    lines.append("")
    lines.append("| Family | Required | Admitted | Status |")
    lines.append("|--------|----------|---------|--------|")
    for fam in report.families:
        status = "FAIL" if fam.missing else "PASS"
        lines.append(
            f"| {fam.family_id} | {fam.minimum_count} | {fam.admitted_count} | {status} |"
        )

    lines.append("")
    return "\n".join(lines)


def build_corpus_state_snapshot(
    catalog: SourceCatalog,
    corpus_state_id: str,
    catalog_path: Path,
) -> dict:
    """Deterministic machine-readable snapshot of the current corpus state.

    Deliberately omits generation_timestamp so that identical catalog state
    produces identical output on every run.

    counts_by_kind keys follow SourceKind enum declaration order.
    counts_by_role_level keys follow high → medium → low order.
    source_ids is sorted.
    """
    kind_counter = Counter(e.source_kind for e in catalog.entries)
    role_counter = Counter(e.source_role_level for e in catalog.entries)

    counts_by_kind = {
        kind.value: kind_counter[kind]
        for kind in _KIND_ORDER
        if kind_counter[kind]
    }
    counts_by_role_level = {
        level.value: role_counter[level]
        for level in _ROLE_LEVEL_ORDER
        if role_counter[level]
    }
    return {
        "corpus_state_id": corpus_state_id,
        "catalog_path": catalog_path.as_posix(),
        "total_sources": len(catalog.entries),
        "counts_by_kind": counts_by_kind,
        "counts_by_role_level": counts_by_role_level,
        "source_ids": sorted(e.source_id for e in catalog.entries),
    }
