from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, List, Mapping, Optional

from eubw_researcher.models import (
    CorpusCoverageReport,
    EvalRunManifest,
    SpawnedValidatorGateManifest,
    SourceCatalog,
    SourceKind,
    SourceRoleLevel,
    ValidatedBindingReviewSample,
    ValidatedCurrentStateReport,
)

_ROLE_LEVEL_ORDER: List[SourceRoleLevel] = [
    SourceRoleLevel.HIGH,
    SourceRoleLevel.MEDIUM,
    SourceRoleLevel.LOW,
]

_KIND_ORDER: List[SourceKind] = list(SourceKind)
_RELEASE_GATE_TARGET = "release_gate"


def _validated_spawned_validator_gate_passed(
    manifest: SpawnedValidatorGateManifest,
) -> bool:
    return (
        bool(manifest.scenario_runs)
        and manifest.overall_passed
        and all(
            item.final_passed
            and item.spawned_validator_invoked
            and item.spawned_validator_contract_passed is True
            and item.spawned_validator_passed is True
            for item in manifest.scenario_runs
        )
    )


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
) -> dict[str, Any]:
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


def build_validated_current_state_report(
    snapshot: Mapping[str, Any],
    *,
    eval_manifest: EvalRunManifest,
    eval_manifest_path: Path,
    runtime_contract_version: str,
    coverage_report_path: Optional[Path],
    coverage_summary_path: Optional[Path],
    corpus_selection_summary_path: Optional[Path],
    corpus_state_snapshot_path: Path,
    real_question_pack_manifest: Optional[Mapping[str, Any]] = None,
    real_question_pack_manifest_path: Optional[Path] = None,
    spawned_validator_gate_manifest: Optional[SpawnedValidatorGateManifest] = None,
    spawned_validator_gate_manifest_path: Optional[Path] = None,
    promote_spawned_validator_gate: bool = False,
    git_metadata: Optional[Mapping[str, Any]] = None,
) -> ValidatedCurrentStateReport:
    snapshot_catalog_path = str(Path(snapshot["catalog_path"]).resolve())
    eval_catalog_path = str(Path(eval_manifest.catalog_path).resolve())
    binding_review_samples = [
        ValidatedBindingReviewSample(
            scenario_id=item.scenario_id,
            manual_review_accept_required=item.require_manual_review_accept,
            manual_review_accept_satisfied=item.manual_review_accept_satisfied,
            verdict_path=item.verdict_path,
            manual_review_report_path=item.manual_review_report_path,
        )
        for item in eval_manifest.scenario_runs
        if item.require_manual_review_accept
    ]
    current_catalog_matches_eval_gate = (
        snapshot_catalog_path == eval_catalog_path
        and snapshot["corpus_state_id"] == eval_manifest.corpus_state_id
    )
    current_runtime_matches_eval_gate = (
        runtime_contract_version == eval_manifest.runtime_contract_version
    )
    coverage_gate_passed = eval_manifest.coverage_gate_passed
    eval_gate_passed = eval_manifest.overall_passed
    spawned_validator_gate_matches_state = None
    spawned_validator_gate_passed = None
    release_validation_mode = "deterministic_eval_only"
    binding_spawned_validator_gate_ok = True
    if spawned_validator_gate_manifest is not None:
        spawned_validator_catalog_path = str(
            Path(spawned_validator_gate_manifest.catalog_path).resolve()
        )
        spawned_validator_gate_matches_state = (
            spawned_validator_catalog_path == snapshot_catalog_path
            and spawned_validator_gate_manifest.corpus_state_id == snapshot["corpus_state_id"]
            and spawned_validator_gate_manifest.runtime_contract_version
            == runtime_contract_version
        )
        spawned_validator_gate_passed = _validated_spawned_validator_gate_passed(
            spawned_validator_gate_manifest
        )
        spawned_validator_gate_is_release_gate = (
            spawned_validator_gate_manifest.gate_target == _RELEASE_GATE_TARGET
        )
        if promote_spawned_validator_gate:
            release_validation_mode = "deterministic_eval_plus_binding_spawned_validator"
            binding_spawned_validator_gate_ok = bool(
                spawned_validator_gate_matches_state
                and spawned_validator_gate_passed
                and spawned_validator_gate_is_release_gate
            )
        else:
            release_validation_mode = "deterministic_eval_plus_supplemental_spawned_validator"
    validated = (
        coverage_gate_passed is True
        and eval_gate_passed
        and current_catalog_matches_eval_gate
        and current_runtime_matches_eval_gate
        and binding_spawned_validator_gate_ok
    )
    supplemental_matches_state = None
    supplemental_run_id = None
    if real_question_pack_manifest is not None:
        pack_catalog_path = real_question_pack_manifest.get("catalog_path")
        supplemental_matches_state = (
            (
                pack_catalog_path is not None
                and str(Path(pack_catalog_path).resolve()) == snapshot_catalog_path
            )
            and real_question_pack_manifest.get("corpus_state_id") == snapshot["corpus_state_id"]
            and real_question_pack_manifest.get("runtime_contract_version")
            == runtime_contract_version
        )
        supplemental_run_id = real_question_pack_manifest.get("run_id")
    return ValidatedCurrentStateReport(
        report_version="validated_current_state.v1",
        binding_gate_surface=eval_manifest.binding_gate_surface,
        release_validation_mode=release_validation_mode,
        validated=validated,
        catalog_path=snapshot_catalog_path,
        corpus_state_id=snapshot["corpus_state_id"],
        runtime_contract_version=runtime_contract_version,
        git_commit=(git_metadata or {}).get("commit"),
        git_branch=(git_metadata or {}).get("branch"),
        git_dirty=(git_metadata or {}).get("dirty"),
        total_sources=int(snapshot["total_sources"]),
        counts_by_kind=dict(snapshot["counts_by_kind"]),
        counts_by_role_level=dict(snapshot["counts_by_role_level"]),
        coverage_gate_passed=coverage_gate_passed,
        eval_gate_passed=eval_gate_passed,
        current_catalog_matches_eval_gate=current_catalog_matches_eval_gate,
        current_runtime_matches_eval_gate=current_runtime_matches_eval_gate,
        eval_manifest_path=str(eval_manifest_path.resolve()),
        corpus_state_snapshot_path=str(corpus_state_snapshot_path.resolve()),
        corpus_coverage_report_path=(
            str(coverage_report_path.resolve()) if coverage_report_path is not None else None
        ),
        corpus_coverage_summary_path=(
            str(coverage_summary_path.resolve()) if coverage_summary_path is not None else None
        ),
        corpus_selection_summary_path=(
            str(corpus_selection_summary_path.resolve())
            if corpus_selection_summary_path is not None
            else None
        ),
        spawned_validator_gate_passed=spawned_validator_gate_passed,
        binding_review_samples=binding_review_samples,
        spawned_validator_gate_manifest_path=(
            str(spawned_validator_gate_manifest_path.resolve())
            if spawned_validator_gate_manifest_path is not None
            else None
        ),
        spawned_validator_gate_matches_state=spawned_validator_gate_matches_state,
        supplemental_real_question_pack_manifest_path=(
            str(real_question_pack_manifest_path.resolve())
            if real_question_pack_manifest_path is not None
            else None
        ),
        supplemental_real_question_pack_matches_state=supplemental_matches_state,
        supplemental_real_question_pack_run_id=supplemental_run_id,
    )


def render_validated_current_state_report_md(
    report: ValidatedCurrentStateReport,
) -> str:
    coverage_gate_text = (
        "yes"
        if report.coverage_gate_passed is True
        else "no"
        if report.coverage_gate_passed is False
        else "unknown"
    )
    overall = "VALIDATED" if report.validated else "NOT VALIDATED"
    lines: List[str] = []
    lines.append("# Validated Current State")
    lines.append("")
    lines.append(f"**Overall:** {overall}")
    lines.append(f"**Binding gate surface:** `{report.binding_gate_surface}`")
    lines.append(f"**Release validation mode:** `{report.release_validation_mode}`")
    lines.append(f"**Corpus state:** `{report.corpus_state_id}`")
    lines.append(f"**Runtime contract:** `{report.runtime_contract_version}`")
    lines.append("")
    lines.append("## Current state")
    lines.append("")
    lines.append(f"- Catalog path: `{report.catalog_path}`")
    lines.append(f"- Total sources: {report.total_sources}")
    lines.append(
        "- Counts by role level: "
        + ", ".join(
            f"{role}={count}" for role, count in report.counts_by_role_level.items()
        )
    )
    lines.append(
        "- Counts by kind: "
        + ", ".join(
            f"{kind}={count}" for kind, count in report.counts_by_kind.items()
        )
    )
    lines.append("")
    lines.append("## Gate checks")
    lines.append("")
    lines.append(f"- Coverage gate passed: {coverage_gate_text}")
    lines.append(
        f"- Eval gate passed: {'yes' if report.eval_gate_passed else 'no'}"
    )
    lines.append(
        "- Current catalog matches eval gate: "
        + ("yes" if report.current_catalog_matches_eval_gate else "no")
    )
    lines.append(
        "- Current runtime matches eval gate: "
        + ("yes" if report.current_runtime_matches_eval_gate else "no")
    )
    if report.spawned_validator_gate_passed is not None:
        lines.append(
            "- Spawned-validator gate passed: "
            + ("yes" if report.spawned_validator_gate_passed else "no")
        )
        lines.append(
            "- Spawned-validator gate matches current state: "
            + (
                "yes"
                if report.spawned_validator_gate_matches_state
                else "no"
            )
        )
    if report.binding_review_samples:
        lines.append("")
        lines.append("## Binding review samples")
        lines.append("")
        lines.append("| Scenario | Manual review accept | Verdict | Review report |")
        lines.append("|----------|----------------------|---------|---------------|")
        for sample in report.binding_review_samples:
            manual_review_accept_text = (
                "unknown"
                if sample.manual_review_accept_satisfied is None
                else "yes"
                if sample.manual_review_accept_satisfied
                else "no"
            )
            lines.append(
                f"| {sample.scenario_id} | "
                f"{manual_review_accept_text} | "
                f"`{sample.verdict_path}` | "
                f"`{sample.manual_review_report_path}` |"
            )
    lines.append("")
    lines.append("## Artifact references")
    lines.append("")
    lines.append(f"- Eval manifest: `{report.eval_manifest_path}`")
    lines.append(f"- Corpus snapshot: `{report.corpus_state_snapshot_path}`")
    if report.corpus_coverage_report_path:
        lines.append(f"- Corpus coverage report: `{report.corpus_coverage_report_path}`")
    if report.corpus_coverage_summary_path:
        lines.append(f"- Corpus coverage summary: `{report.corpus_coverage_summary_path}`")
    if report.corpus_selection_summary_path:
        lines.append(f"- Corpus selection summary: `{report.corpus_selection_summary_path}`")
    if report.spawned_validator_gate_manifest_path and not report.release_validation_mode.endswith(
        "supplemental_spawned_validator"
    ):
        lines.append(
            "- Spawned-validator gate manifest: "
            f"`{report.spawned_validator_gate_manifest_path}`"
        )
    if report.supplemental_real_question_pack_manifest_path:
        lines.append("")
        lines.append("## Supplemental evidence")
        lines.append("")
        if report.spawned_validator_gate_manifest_path:
            lines.append(
                "- Spawned-validator gate manifest: "
                f"`{report.spawned_validator_gate_manifest_path}`"
            )
            lines.append(
                "- Spawned-validator gate matches current state: "
                + (
                    "yes"
                    if report.spawned_validator_gate_matches_state
                    else "no"
                )
            )
        lines.append(
            f"- Real-question pack manifest: `{report.supplemental_real_question_pack_manifest_path}`"
        )
        lines.append(
            "- Matches current state: "
            + (
                "yes"
                if report.supplemental_real_question_pack_matches_state
                else "no"
            )
        )
    elif report.spawned_validator_gate_manifest_path and report.release_validation_mode.endswith(
        "supplemental_spawned_validator"
    ):
        lines.append("")
        lines.append("## Supplemental evidence")
        lines.append("")
        lines.append(
            "- Spawned-validator gate manifest: "
            f"`{report.spawned_validator_gate_manifest_path}`"
        )
        lines.append(
            "- Matches current state: "
            + (
                "yes"
                if report.spawned_validator_gate_matches_state
                else "no"
            )
        )
    lines.append("")
    return "\n".join(lines)
