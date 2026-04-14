from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _catalog_path import resolve_catalog_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
        help="Internal source catalog path.",
    )
    parser.add_argument(
        "--cases",
        default="configs/retrieval_usefulness_cases.yaml",
        help="Retrieval usefulness case config path.",
    )
    parser.add_argument(
        "--baseline-config",
        default="configs/runtime.scan.yaml",
        help="Baseline runtime config path.",
    )
    parser.add_argument(
        "--candidate-config",
        default="configs/runtime.yaml",
        help="Candidate runtime config path.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Output directory for comparison artifacts. Defaults to "
            "artifacts/retrieval_backend_runs/<timestamp>."
        ),
    )
    return parser.parse_args()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_output_dir(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "retrieval_backend_runs" / _utcnow().strftime(
        "%Y%m%dT%H%M%SZ"
    )


def _resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("cases", []))


def _case_is_usable(result: dict) -> bool:
    return result["intent_matches_expected"] and result["target_present_in_plan"]


def _summarize_case_reports(case_reports: list[dict]) -> dict[str, int | str]:
    baseline_hits = sum(1 for case in case_reports if case["baseline"]["hit"])
    candidate_hits = sum(1 for case in case_reports if case["candidate"]["hit"])
    improvements = sum(1 for case in case_reports if case["delta"] == "improved")
    regressions = sum(1 for case in case_reports if case["delta"] == "regressed")
    baseline_route_failures = sum(
        1 for case in case_reports if not _case_is_usable(case["baseline"])
    )
    candidate_route_failures = sum(
        1 for case in case_reports if not _case_is_usable(case["candidate"])
    )
    recommendation = (
        "promote_candidate_default"
        if regressions == 0
        and improvements >= 1
        and candidate_route_failures == 0
        else "keep_baseline_default"
    )
    return {
        "baseline_hits": baseline_hits,
        "candidate_hits": candidate_hits,
        "improvements": improvements,
        "regressions": regressions,
        "baseline_route_failures": baseline_route_failures,
        "candidate_route_failures": candidate_route_failures,
        "recommendation": recommendation,
    }


def _evaluate_runtime(
    *,
    question: str,
    target_id: str,
    expected_source_ids: list[str],
    expected_intent_type: str | None,
    runtime_config,
    hierarchy,
    terminology,
    bundle,
    catalog_path: Path,
    corpus_state_id: str,
):
    from eubw_researcher.retrieval import (
        analyze_query,
        build_retrieval_plan,
        retrieve_candidates_with_trace,
    )

    intent = analyze_query(question, terminology)
    plan = build_retrieval_plan(intent, hierarchy, runtime_config, terminology)
    target_queries = {target.target_id: target for target in plan.target_queries}
    target_query = target_queries.get(target_id)
    intent_matches_expected = (
        expected_intent_type is None or intent.intent_type == expected_intent_type
    )
    query_text = (
        target_query.normalized_query
        if target_query is not None
        else plan.normalized_question
    )
    hit = None
    if intent_matches_expected and target_query is not None:
        for step in plan.steps:
            candidates, trace = retrieve_candidates_with_trace(
                question=query_text,
                step=step,
                bundle=bundle,
                hierarchy=hierarchy,
                runtime_config=runtime_config,
                catalog_path=catalog_path,
                corpus_state_id=corpus_state_id,
            )
            for index, candidate in enumerate(candidates, start=1):
                if candidate.chunk.source_id in expected_source_ids:
                    hit = {
                        "step_id": step.step_id,
                        "required_kind": step.required_kind.value,
                        "position": index,
                        "source_id": candidate.chunk.source_id,
                        "cache_status": trace.cache_status,
                        "fallback_used": trace.fallback_used,
                    }
                    break
            if hit is not None:
                break
    return {
        "intent_type": intent.intent_type,
        "intent_matches_expected": intent_matches_expected,
        "target_present_in_plan": target_query is not None,
        "evaluated_query": query_text,
        "hit": hit is not None,
        "hit_detail": hit,
        "backend": runtime_config.local_retrieval_backend,
    }


def _render_markdown(report: dict) -> str:
    lines = [
        "# Retrieval Backend Comparison",
        "",
        f"- Baseline backend: `{report['baseline_backend']}`",
        f"- Candidate backend: `{report['candidate_backend']}`",
        f"- Baseline hits: {report['summary']['baseline_hits']}",
        f"- Candidate hits: {report['summary']['candidate_hits']}",
        f"- Improvements: {report['summary']['improvements']}",
        f"- Regressions: {report['summary']['regressions']}",
        (
            "- Candidate route failures: "
            f"{report['summary']['candidate_route_failures']}"
        ),
        f"- Recommendation: `{report['summary']['recommendation']}`",
        "",
        "## Cases",
        "",
        "| Case | Baseline | Candidate | Delta |",
        "| --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        baseline = "hit" if case["baseline"]["hit"] else "miss"
        candidate = "hit" if case["candidate"]["hit"] else "miss"
        delta = case["delta"]
        lines.append(
            f"| {case['case_id']} | {baseline} | {candidate} | {delta} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from eubw_researcher.config import (
        load_runtime_config,
        load_source_hierarchy,
        load_terminology_config,
        runtime_config_digest,
    )
    from eubw_researcher.corpus.runtime import load_or_build_ingestion_bundle

    catalog_path = resolve_catalog_path(repo_root, args.catalog)
    cases_path = _resolve_path(repo_root, args.cases)
    baseline_config_path = _resolve_path(repo_root, args.baseline_config)
    candidate_config_path = _resolve_path(repo_root, args.candidate_config)
    output_dir = (
        _resolve_path(repo_root, args.output_dir)
        if args.output_dir
        else _default_output_dir(repo_root)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    hierarchy = load_source_hierarchy(repo_root / "configs" / "source_hierarchy.yaml")
    terminology = load_terminology_config(repo_root / "configs" / "terminology.yaml")
    baseline_runtime = load_runtime_config(baseline_config_path)
    candidate_runtime = load_runtime_config(candidate_config_path)
    _catalog, bundle, _coverage_report, corpus_state_id = load_or_build_ingestion_bundle(
        catalog_path
    )
    cases = _load_cases(cases_path)

    case_reports = []
    for case in cases:
        baseline = _evaluate_runtime(
            question=case["question"],
            target_id=case["target_id"],
            expected_source_ids=list(case["expected_source_ids"]),
            expected_intent_type=case.get("expected_intent_type"),
            runtime_config=baseline_runtime,
            hierarchy=hierarchy,
            terminology=terminology,
            bundle=bundle,
            catalog_path=catalog_path,
            corpus_state_id=corpus_state_id,
        )
        candidate = _evaluate_runtime(
            question=case["question"],
            target_id=case["target_id"],
            expected_source_ids=list(case["expected_source_ids"]),
            expected_intent_type=case.get("expected_intent_type"),
            runtime_config=candidate_runtime,
            hierarchy=hierarchy,
            terminology=terminology,
            bundle=bundle,
            catalog_path=catalog_path,
            corpus_state_id=corpus_state_id,
        )
        delta = (
            "improved"
            if candidate["hit"] and not baseline["hit"]
            else "regressed"
            if baseline["hit"] and not candidate["hit"]
            else "unchanged"
        )
        case_reports.append(
            {
                "case_id": case["case_id"],
                "question": case["question"],
                "target_id": case["target_id"],
                "expected_source_ids": list(case["expected_source_ids"]),
                "baseline": baseline,
                "candidate": candidate,
                "delta": delta,
            }
        )

    summary = _summarize_case_reports(case_reports)
    report = {
        "generated_at": _utcnow().isoformat(),
        "catalog_path": str(catalog_path),
        "corpus_state_id": corpus_state_id,
        "cases_path": str(cases_path),
        "baseline_config_path": str(baseline_config_path),
        "baseline_config_digest": runtime_config_digest(baseline_config_path),
        "baseline_backend": baseline_runtime.local_retrieval_backend,
        "candidate_config_path": str(candidate_config_path),
        "candidate_config_digest": runtime_config_digest(candidate_config_path),
        "candidate_backend": candidate_runtime.local_retrieval_backend,
        "cases": case_reports,
        "summary": summary,
    }

    (output_dir / "comparison_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (output_dir / "comparison_report.md").write_text(
        _render_markdown(report),
        encoding="utf-8",
    )
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
