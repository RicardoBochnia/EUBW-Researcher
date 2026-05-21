#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from eubw_researcher.evaluation.real_question_pack import run_real_question_pack


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _question_gate(question_dir: Path, *, locator_threshold: float) -> dict:
    verdict = _load_json(question_dir / "verdict.json")
    alignment = _load_json(question_dir / "answer_alignment.json")
    pinpoint = _load_json(question_dir / "pinpoint_evidence.json")

    checks = list(verdict.get("checks", []))
    required_concept_failures = [
        check for check in checks if check.startswith("expected_concept:") and check.endswith(":required:fail")
    ]
    legacy_gap_misses = [
        check for check in checks if check.startswith("expected_concept:") and check.endswith(":legacy_gap:not_surfaced")
    ]
    alignment_records = alignment.get("records", [])
    pinpoint_records = pinpoint.get("records", [])
    locator_coverage = (
        1.0
        if not alignment_records
        else min(1.0, len(pinpoint_records) / max(1, len(alignment_records)))
    )
    unsupported_normative_claims = len(alignment.get("blocking_violations", []))
    source_role_violations = len(
        [
            violation
            for violation in alignment.get("blocking_violations", [])
            if "source" in violation.casefold()
            or "governing" in violation.casefold()
            or "rank" in violation.casefold()
        ]
    )
    artifact_traceability_pass = (
        not verdict.get("missing_artifacts")
        and bool(pinpoint.get("all_cited_evidence_mapped", True))
        and not alignment.get("blocking_violations")
        and locator_coverage >= locator_threshold
    )
    hard_gate_pass = (
        bool(verdict.get("passed", False))
        and not required_concept_failures
        and unsupported_normative_claims == 0
        and source_role_violations == 0
        and locator_coverage >= locator_threshold
        and not legacy_gap_misses
        and artifact_traceability_pass
    )
    return {
        "question_id": verdict.get("scenario_id", question_dir.name),
        "hard_gate_pass": hard_gate_pass,
        "required_concepts_met": not required_concept_failures,
        "required_concept_failures": required_concept_failures,
        "unsupported_normative_claims": unsupported_normative_claims,
        "source_role_violations": source_role_violations,
        "locator_coverage": locator_coverage,
        "locator_threshold": locator_threshold,
        "caveat_preservation_pass": not legacy_gap_misses,
        "legacy_only_concepts_marked_as_gap_or_rejected": not legacy_gap_misses,
        "legacy_gap_misses": legacy_gap_misses,
        "artifact_traceability_pass": artifact_traceability_pass,
        "final_verdict_passed": bool(verdict.get("passed", False)),
        "checks": checks,
    }


def _render_markdown(report: dict) -> str:
    lines = [
        "# Legacy Parity Report",
        "",
        f"- Overall hard gate: `{str(report['hard_gate_pass']).lower()}`",
        f"- Pack: `{report['pack_path']}`",
        f"- Runtime config: `{report['runtime_config_path']}`",
        f"- Catalog: `{report['catalog_path']}`",
        f"- Freeze manifest: `{report.get('freeze_manifest_path')}`",
        "",
        "| Question | Hard gate | Required concepts | Locator coverage | Traceability |",
        "| --- | --- | --- | --- | --- |",
    ]
    for question in report["questions"]:
        lines.append(
            "| {question_id} | `{hard_gate}` | `{concepts}` | {coverage:.2f} | `{trace}` |".format(
                question_id=question["question_id"],
                hard_gate=str(question["hard_gate_pass"]).lower(),
                concepts=str(question["required_concepts_met"]).lower(),
                coverage=question["locator_coverage"],
                trace=str(question["artifact_traceability_pass"]).lower(),
            )
        )
    lines.append("")
    failing = [
        question for question in report["questions"] if not question["hard_gate_pass"]
    ]
    if failing:
        lines.append("## Failing Questions")
        lines.append("")
        for question in failing:
            lines.append(f"### {question['question_id']}")
            for key in [
                "required_concept_failures",
                "legacy_gap_misses",
                "unsupported_normative_claims",
                "source_role_violations",
            ]:
                lines.append(f"- {key}: `{question[key]}`")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", default="configs/legacy_parity_question_pack.yaml")
    parser.add_argument("--catalog", default="artifacts/real_corpus/curated_catalog.json")
    parser.add_argument("--runtime-config", default="configs/runtime.knowledge_composer_vnext.yaml")
    parser.add_argument("--freeze-manifest", default="configs/legacy_parity_freeze_manifest.json")
    parser.add_argument("--output-dir", default="artifacts/tmp/legacy_parity")
    parser.add_argument("--locator-threshold", type=float, default=0.8)
    args = parser.parse_args()

    run_root, manifest = run_real_question_pack(
        ROOT,
        pack_path=args.pack,
        catalog_path=args.catalog,
        output_dir=args.output_dir,
        runtime_config_path=args.runtime_config,
    )
    freeze_path = (ROOT / args.freeze_manifest).resolve()
    freeze_manifest = _load_json(freeze_path)
    question_gates = [
        _question_gate(Path(run.output_dir), locator_threshold=args.locator_threshold)
        for run in manifest.question_runs
    ]
    report = {
        "schema_version": "legacy_parity_report.v1",
        "hard_gate_pass": all(question["hard_gate_pass"] for question in question_gates),
        "pack_path": manifest.pack_path,
        "pack_digest": manifest.pack_digest,
        "catalog_path": manifest.catalog_path,
        "catalog_digest": freeze_manifest.get("catalog_digest"),
        "runtime_config_path": manifest.runtime_config_path,
        "runtime_config_digest": manifest.runtime_config_digest,
        "question_pack_digest": manifest.pack_digest,
        "legacy_reference_digest": freeze_manifest.get("legacy_reference_digest"),
        "freeze_manifest_path": str(freeze_path),
        "freeze_manifest_digest": (
            freeze_manifest.get("question_pack_digest")
            if freeze_manifest
            else None
        ),
        "commit_sha": manifest.git_commit,
        "git_dirty": manifest.git_dirty,
        "run_manifest_path": str((run_root / "pack_run_manifest.json").resolve()),
        "questions": question_gates,
    }
    json_path = run_root / "legacy_parity_report.json"
    md_path = run_root / "legacy_parity_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(json_path)
    print(md_path)
    return 0 if report["hard_gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
