from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from eubw_researcher.answering import TOPOLOGY_FACET_IDS
from eubw_researcher.config import (
    load_evaluation_scenarios,
    load_runtime_config,
    load_source_hierarchy,
    load_web_allowlist,
)
from eubw_researcher.corpus import (
    is_real_corpus_catalog,
    load_or_build_ingestion_bundle,
    render_corpus_coverage_summary_md,
    write_corpus_coverage_report,
)
from eubw_researcher.models import ManualReviewReport, ScenarioVerdict, dataclass_to_dict
from eubw_researcher.models import EvalRunManifest, EvalScenarioRunSummary
from eubw_researcher.pipeline import ResearchPipeline
from eubw_researcher.evaluation.review import (
    build_manual_review_artifact,
    build_manual_review_report,
    build_manual_review_report_markdown,
)


def default_output_dir(repo_root: Path, catalog_path: Optional[Path]) -> Path:
    if is_real_corpus_catalog(catalog_path):
        return repo_root / "artifacts" / "eval_runs_real_corpus"
    return repo_root / "artifacts" / "eval_runs"


def _scenario_config_path(
    repo_root: Path,
    catalog_path: Optional[Path],
    scenarios_path: Optional[Path],
) -> Path:
    if scenarios_path is not None:
        return scenarios_path
    default_path = repo_root / "configs" / "evaluation_scenarios.yaml"
    real_corpus_path = repo_root / "configs" / "evaluation_scenarios_real_corpus.yaml"
    if is_real_corpus_catalog(catalog_path) and real_corpus_path.exists():
        return real_corpus_path
    return default_path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _run_git_command(repo_root: Path, *args: str) -> Optional[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _git_metadata(repo_root: Path) -> dict[str, Optional[object]]:
    branch = _run_git_command(repo_root, "branch", "--show-current")
    commit = _run_git_command(repo_root, "rev-parse", "HEAD")
    status = _run_git_command(repo_root, "status", "--short")
    return {
        "branch": branch,
        "commit": commit,
        "dirty": True if status is None else bool(status),
    }


def _evaluate_scenario_with_review_report(
    scenario,
    result,
) -> Tuple[ScenarioVerdict, ManualReviewReport]:
    checks = []
    passed = True

    if scenario.required_intent_type:
        if result.query_intent.intent_type == scenario.required_intent_type:
            checks.append(f"intent_type:{scenario.required_intent_type}:ok")
        else:
            checks.append(
                "intent_type:"
                f"{scenario.required_intent_type}:fail:{result.query_intent.intent_type}"
            )
            passed = False

    if len(result.ledger_entries) >= scenario.min_ledger_entries:
        checks.append(f"ledger_entries>={scenario.min_ledger_entries}:ok")
    else:
        checks.append(f"ledger_entries>={scenario.min_ledger_entries}:fail")
        passed = False

    actual_states = [entry.final_claim_state for entry in result.ledger_entries]
    for state in scenario.required_states:
        if state in actual_states:
            checks.append(f"state:{state.value}:ok")
        else:
            checks.append(f"state:{state.value}:fail")
            passed = False

    if scenario.allowed_states:
        disallowed_states = [state.value for state in actual_states if state not in scenario.allowed_states]
        if disallowed_states:
            checks.append(f"allowed_states_only:fail:{','.join(disallowed_states)}")
            passed = False
        else:
            checks.append("allowed_states_only:ok")

    actual_sources = {
        citation.source_id
        for entry in result.ledger_entries
        for citation in entry.citations
    }
    for source_id in scenario.required_sources:
        if source_id in actual_sources:
            checks.append(f"required_source:{source_id}:ok")
        else:
            checks.append(f"required_source:{source_id}:fail")
            passed = False

    for source_id in scenario.forbidden_sources:
        if source_id in actual_sources:
            checks.append(f"forbidden_source:{source_id}:fail")
            passed = False
        else:
            checks.append(f"forbidden_source:{source_id}:ok")

    for snippet in scenario.required_answer_substrings:
        if snippet in result.rendered_answer:
            checks.append(f"answer_contains:{snippet}:ok")
        else:
            checks.append(f"answer_contains:{snippet}:fail")
            passed = False

    for snippet in scenario.forbidden_answer_substrings:
        if snippet in result.rendered_answer:
            checks.append(f"answer_forbids:{snippet}:fail")
            passed = False
        else:
            checks.append(f"answer_forbids:{snippet}:ok")

    if scenario.required_clarification_substring:
        if scenario.required_clarification_substring in result.rendered_answer:
            checks.append("clarification_note:ok")
        else:
            checks.append("clarification_note:fail")
            passed = False

    if len(result.gap_records) >= scenario.min_gap_records:
        checks.append(f"gap_records>={scenario.min_gap_records}:ok")
    else:
        checks.append(f"gap_records>={scenario.min_gap_records}:fail")
        passed = False

    gap_reasons = [gap.reason_local_evidence_insufficient for gap in result.gap_records]
    for snippet in scenario.required_gap_reason_substrings:
        if any(snippet in reason for reason in gap_reasons):
            checks.append(f"gap_reason:{snippet}:ok")
        else:
            checks.append(f"gap_reason:{snippet}:fail")
            passed = False

    gap_actions = [gap.next_allowed_action for gap in result.gap_records]
    for action in scenario.required_gap_actions:
        if action in gap_actions:
            checks.append(f"gap_action:{action}:ok")
        else:
            checks.append(f"gap_action:{action}:fail")
            passed = False

    discovery_count = sum(
        1 for record in result.web_fetch_records if record.record_type == "discovery"
    )
    fetch_count = sum(
        1 for record in result.web_fetch_records if record.record_type == "fetch"
    )

    if discovery_count >= scenario.required_web_discovery_count:
        checks.append(f"web_discovery_records>={scenario.required_web_discovery_count}:ok")
    else:
        checks.append(f"web_discovery_records>={scenario.required_web_discovery_count}:fail")
        passed = False

    if fetch_count >= scenario.required_web_fetch_count:
        checks.append(f"web_fetch_records>={scenario.required_web_fetch_count}:ok")
    else:
        checks.append(f"web_fetch_records>={scenario.required_web_fetch_count}:fail")
        passed = False

    if scenario.required_retrieval_prefix_kinds:
        actual_prefix = [step.required_kind for step in result.retrieval_plan.steps[: len(scenario.required_retrieval_prefix_kinds)]]
        if actual_prefix == scenario.required_retrieval_prefix_kinds:
            checks.append("retrieval_prefix:ok")
        else:
            checks.append(
                "retrieval_prefix:fail:"
                + ",".join(kind.value for kind in actual_prefix)
            )
            passed = False

    if scenario.require_provisional_grouping:
        if (
            result.provisional_grouping
            and len(result.provisional_grouping) >= 2
            and all(group.claim_ids and group.source_ids for group in result.provisional_grouping)
            and all(
                group_claim_id in {entry.claim_id for entry in result.ledger_entries}
                for group in result.provisional_grouping
                for group_claim_id in group.claim_ids
            )
        ):
            checks.append("provisional_grouping:ok")
        else:
            checks.append("provisional_grouping:fail")
            passed = False

    web_trigger_gaps = [
        gap for gap in result.gap_records if gap.next_allowed_action == "official_web_search"
    ]
    if web_trigger_gaps:
        if all(
            gap.local_source_layers_searched
            and {"lexical", "semantic"}.issubset(set(gap.retrieval_methods_used))
            and gap.reason_local_evidence_insufficient
            for gap in web_trigger_gaps
        ):
            checks.append("web_gap_audit:ok")
        else:
            checks.append("web_gap_audit:fail")
            passed = False

    if result.web_fetch_records:
        allowed_records = [
            record
            for record in result.web_fetch_records
            if record.allowed and record.record_type == "fetch"
        ]
        if all(
            (
                record.metadata_complete
                and record.canonical_url
                and record.domain
                and record.source_kind is not None
                and record.source_role_level is not None
                and record.retrieval_timestamp
                and record.citation_quality is not None
            )
            for record in allowed_records
        ):
            checks.append("web_metadata_complete:ok")
        else:
            checks.append("web_metadata_complete:fail")
            passed = False

        approved_urls = {
            citation.canonical_url
            for entry in result.approved_entries
            for citation in entry.citations
            if citation.canonical_url
        }
        rejected_urls = {
            record.canonical_url
            for record in result.web_fetch_records
            if record.record_type == "fetch" and ((not record.allowed) or (not record.metadata_complete))
        }
        if approved_urls & rejected_urls:
            checks.append("rejected_web_not_approved:fail")
            passed = False
        else:
            checks.append("rejected_web_not_approved:ok")

    approved_entries_have_citations = all(entry.citations for entry in result.approved_entries)
    if approved_entries_have_citations:
        checks.append("approved_entries_have_citations:ok")
    else:
        checks.append("approved_entries_have_citations:fail")
        passed = False

    blocked_visible = "Blocked:" in result.rendered_answer
    if not blocked_visible:
        checks.append("blocked_hidden_in_answer:ok")
    else:
        checks.append("blocked_hidden_in_answer:fail")
        passed = False

    state_markers = {
        "Confirmed:": any(entry.final_claim_state.value == "confirmed" for entry in result.approved_entries),
        "Interpretive:": any(entry.final_claim_state.value == "interpretive" for entry in result.approved_entries),
        "Open:": any(entry.final_claim_state.value == "open" for entry in result.approved_entries),
    }
    if all((not expected) or marker in result.rendered_answer for marker, expected in state_markers.items()):
        checks.append("state_visibility:ok")
    else:
        checks.append("state_visibility:fail")
        passed = False

    if result.query_intent.intent_type == "certificate_topology_analysis":
        if result.facet_coverage_report is None:
            checks.append("facet_coverage_artifact:fail")
            passed = False
        else:
            checks.append("facet_coverage_artifact:ok")
            facets_by_id = result.facet_coverage_report.by_id()
            for facet_id in TOPOLOGY_FACET_IDS:
                facet = facets_by_id.get(facet_id)
                if facet is not None and facet.addressed:
                    checks.append(f"facet:{facet_id}:ok")
                else:
                    checks.append(f"facet:{facet_id}:fail")
                    passed = False

        pinpoint_report = getattr(result, "pinpoint_evidence_report", None)
        if (
            pinpoint_report is not None
            and pinpoint_report.all_cited_evidence_mapped
            and pinpoint_report.records
        ):
            checks.append("pinpoint_evidence_artifact:ok")
        else:
            checks.append("pinpoint_evidence_artifact:fail")
            passed = False

        alignment_report = getattr(result, "answer_alignment_report", None)
        if (
            alignment_report is not None
            and not alignment_report.has_blocking_violations()
        ):
            checks.append("answer_alignment:ok")
        else:
            checks.append("answer_alignment:fail")
            passed = False

        blind_validation_report = getattr(result, "blind_validation_report", None)
        if blind_validation_report is not None and blind_validation_report.passed:
            checks.append("blind_validation:ok")
        else:
            checks.append("blind_validation:fail")
            passed = False

    gap_by_question = {gap.sub_question: gap for gap in result.gap_records}
    def _entry_needs_gap(entry) -> bool:
        return entry.final_claim_state.value in {"open", "blocked"} or (
            entry.final_claim_state.value == "interpretive"
            and (
                entry.source_role_level != entry.required_source_role_level
                or entry.support_directness.value == "indirect"
                or entry.citation_quality.value == "document_only"
            )
        )

    if all(
        (not _entry_needs_gap(entry))
        or entry.claim_text in gap_by_question
        for entry in result.ledger_entries
    ):
        checks.append("governing_support_or_gap:ok")
    else:
        checks.append("governing_support_or_gap:fail")
        passed = False

    confirmed_document_only_entries = [
        entry
        for entry in result.ledger_entries
        if entry.final_claim_state.value == "confirmed"
        and entry.citation_quality.value == "document_only"
    ]
    if confirmed_document_only_entries:
        if all(
            any(
                evidence.anchor_audit_note
                and "technical extraction failure" in evidence.anchor_audit_note.lower()
                for evidence in entry.governing_evidence
            )
            for entry in confirmed_document_only_entries
        ):
            checks.append("document_only_confirmed_audit:ok")
        else:
            checks.append("document_only_confirmed_audit:fail")
            passed = False

    approved_web_urls = {
        citation.canonical_url
        for entry in result.approved_entries
        for citation in entry.citations
        if citation.source_origin.value == "web" and citation.canonical_url
    }
    fetch_records_by_url = {
        record.canonical_url: record
        for record in result.web_fetch_records
        if record.record_type == "fetch"
    }
    if all(
        (
            approved_url in fetch_records_by_url
            and fetch_records_by_url[approved_url].metadata_complete
            and fetch_records_by_url[approved_url].content_type
            and fetch_records_by_url[approved_url].normalization_status is not None
            and fetch_records_by_url[approved_url].content_digest
            and fetch_records_by_url[approved_url].provenance_record
        )
        for approved_url in approved_web_urls
    ):
        checks.append("approved_web_admission_contract:ok")
    else:
        checks.append("approved_web_admission_contract:fail")
        passed = False

    provisional_verdict = ScenarioVerdict(
        scenario_id=scenario.scenario_id,
        passed=passed,
        checks=list(checks),
    )
    review_report = build_manual_review_report(
        result,
        provisional_verdict,
        scenario_id=scenario.scenario_id,
        catalog_path=None,
        corpus_state_id=None,
    )

    if approved_web_urls:
        evidence_urls = {
            item.canonical_url for item in review_report.approved_fetched_source_evidence
        }
        evidence_complete = all(
            item.content_digest and item.provenance_record
            for item in review_report.approved_fetched_source_evidence
        )
        if approved_web_urls.issubset(evidence_urls) and evidence_complete:
            checks.append("review_fetch_evidence_visible:ok")
        else:
            checks.append("review_fetch_evidence_visible:fail")
            passed = False

    if scenario.require_manual_review_accept:
        if review_report.final_judgment == "accept":
            checks.append("manual_review_accept:ok")
        else:
            checks.append("manual_review_accept:fail")
            passed = False

    return (
        ScenarioVerdict(
            scenario_id=scenario.scenario_id,
            passed=passed,
            checks=checks,
        ),
        review_report,
    )


def _evaluate_scenario(scenario, result) -> ScenarioVerdict:
    verdict, _review_report = _evaluate_scenario_with_review_report(scenario, result)
    return verdict


def _run_pipeline(repo_root: Path, catalog_path: Optional[Path] = None):
    runtime = load_runtime_config(repo_root / "configs" / "runtime.yaml")
    hierarchy = load_source_hierarchy(repo_root / "configs" / "source_hierarchy.yaml")
    allowlist = load_web_allowlist(repo_root / "configs" / "web_allowlist.yaml")
    resolved_catalog_path = (
        catalog_path or repo_root / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
    )
    _, bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(resolved_catalog_path)
    pipeline = ResearchPipeline(
        runtime_config=runtime,
        hierarchy=hierarchy,
        allowlist=allowlist,
        ingestion_bundle=bundle,
    )
    return pipeline, coverage_report, corpus_state_id, resolved_catalog_path


def _build_manual_review_outputs(
    result,
    *,
    verdict: Optional[ScenarioVerdict],
    scenario_id: Optional[str],
    catalog_path: Optional[Path],
    corpus_state_id: Optional[str],
    reviewer_name: str,
    manual_review_report: Optional[ManualReviewReport] = None,
) -> tuple[object, ManualReviewReport, str]:
    manual_review = build_manual_review_artifact(result, scenario_id=scenario_id)
    resolved_report = manual_review_report or build_manual_review_report(
        result,
        verdict or ScenarioVerdict(scenario_id=scenario_id or "direct_run", passed=True, checks=[]),
        scenario_id=scenario_id,
        catalog_path=str(catalog_path.resolve()) if catalog_path else None,
        corpus_state_id=corpus_state_id,
        reviewer_name=reviewer_name,
    )
    return (
        manual_review,
        resolved_report,
        build_manual_review_report_markdown(resolved_report),
    )


def write_artifact_bundle(
    output_dir: Path,
    result,
    verdict: Optional[ScenarioVerdict] = None,
    scenario_id: Optional[str] = None,
    catalog_path: Optional[Path] = None,
    corpus_state_id: Optional[str] = None,
    reviewer_name: str = "Codex",
    manual_review_report: Optional[ManualReviewReport] = None,
) -> ManualReviewReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    manual_review, resolved_report, manual_review_report_markdown = _build_manual_review_outputs(
        result,
        verdict=verdict,
        scenario_id=scenario_id,
        catalog_path=catalog_path,
        corpus_state_id=corpus_state_id,
        reviewer_name=reviewer_name,
        manual_review_report=manual_review_report,
    )

    (output_dir / "retrieval_plan.json").write_text(
        json.dumps(dataclass_to_dict(result.retrieval_plan), indent=2),
        encoding="utf-8",
    )
    (output_dir / "gap_records.json").write_text(
        json.dumps(dataclass_to_dict(result.gap_records), indent=2),
        encoding="utf-8",
    )
    (output_dir / "web_fetch_records.json").write_text(
        json.dumps(dataclass_to_dict(result.web_fetch_records), indent=2),
        encoding="utf-8",
    )
    (output_dir / "ingestion_report.json").write_text(
        json.dumps(dataclass_to_dict(result.ingestion_report), indent=2),
        encoding="utf-8",
    )
    (output_dir / "ledger_entries.json").write_text(
        json.dumps(dataclass_to_dict(result.ledger_entries), indent=2),
        encoding="utf-8",
    )
    (output_dir / "approved_ledger.json").write_text(
        json.dumps(dataclass_to_dict(result.approved_entries), indent=2),
        encoding="utf-8",
    )
    (output_dir / "final_answer.txt").write_text(
        result.rendered_answer + "\n",
        encoding="utf-8",
    )
    if result.provisional_grouping:
        (output_dir / "provisional_grouping.json").write_text(
            json.dumps(dataclass_to_dict(result.provisional_grouping), indent=2),
            encoding="utf-8",
        )
    if result.facet_coverage_report is not None:
        (output_dir / "facet_coverage.json").write_text(
            json.dumps(dataclass_to_dict(result.facet_coverage_report), indent=2),
            encoding="utf-8",
        )
    if result.pinpoint_evidence_report is not None:
        (output_dir / "pinpoint_evidence.json").write_text(
            json.dumps(dataclass_to_dict(result.pinpoint_evidence_report), indent=2),
            encoding="utf-8",
        )
    if result.answer_alignment_report is not None:
        (output_dir / "answer_alignment.json").write_text(
            json.dumps(dataclass_to_dict(result.answer_alignment_report), indent=2),
            encoding="utf-8",
        )
    if result.blind_validation_report is not None:
        (output_dir / "blind_validation_report.json").write_text(
            json.dumps(dataclass_to_dict(result.blind_validation_report), indent=2),
            encoding="utf-8",
        )
    (output_dir / "manual_review.json").write_text(
        json.dumps(dataclass_to_dict(manual_review), indent=2),
        encoding="utf-8",
    )
    (output_dir / "manual_review_report.md").write_text(
        manual_review_report_markdown,
        encoding="utf-8",
    )
    if result.corpus_coverage_report is not None:
        write_corpus_coverage_report(
            result.corpus_coverage_report,
            output_dir / "corpus_coverage_report.json",
        )
        (output_dir / "corpus_coverage_summary.md").write_text(
            render_corpus_coverage_summary_md(result.corpus_coverage_report),
            encoding="utf-8",
        )
    if verdict is not None:
        (output_dir / "verdict.json").write_text(
            json.dumps(dataclass_to_dict(verdict), indent=2),
            encoding="utf-8",
        )
    return resolved_report


def build_eval_run_manifest(
    repo_root: Path,
    *,
    output_dir: Path,
    scenario_config_path: Path,
    catalog_path: Path,
    corpus_state_id: str,
    runtime_contract_version: str,
    scenario_runs: List[EvalScenarioRunSummary],
    coverage_gate_passed: Optional[bool],
    coverage_report_path: Optional[Path],
    coverage_summary_path: Optional[Path],
) -> EvalRunManifest:
    git_metadata = _git_metadata(repo_root)
    return EvalRunManifest(
        run_timestamp=_utcnow().isoformat(),
        scenario_config_path=str(scenario_config_path.resolve()),
        catalog_path=str(catalog_path.resolve()),
        corpus_state_id=corpus_state_id,
        runtime_contract_version=runtime_contract_version,
        binding_gate_surface=(
            "real_corpus_eval" if is_real_corpus_catalog(catalog_path) else "fixture_eval"
        ),
        coverage_gate_passed=coverage_gate_passed,
        overall_passed=all(item.passed for item in scenario_runs),
        coverage_report_path=(
            str(coverage_report_path.resolve())
            if coverage_report_path is not None
            else None
        ),
        coverage_summary_path=(
            str(coverage_summary_path.resolve())
            if coverage_summary_path is not None
            else None
        ),
        git_commit=git_metadata.get("commit"),
        git_branch=git_metadata.get("branch"),
        git_dirty=bool(git_metadata.get("dirty")),
        scenario_runs=scenario_runs,
    )


def write_eval_run_manifest(manifest: EvalRunManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclass_to_dict(manifest), indent=2), encoding="utf-8")


def load_eval_run_manifest(path: Path) -> EvalRunManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return EvalRunManifest(
        run_timestamp=payload["run_timestamp"],
        scenario_config_path=payload["scenario_config_path"],
        catalog_path=payload["catalog_path"],
        corpus_state_id=payload["corpus_state_id"],
        runtime_contract_version=payload["runtime_contract_version"],
        binding_gate_surface=payload["binding_gate_surface"],
        coverage_gate_passed=payload.get("coverage_gate_passed"),
        overall_passed=payload["overall_passed"],
        coverage_report_path=payload.get("coverage_report_path"),
        coverage_summary_path=payload.get("coverage_summary_path"),
        git_commit=payload.get("git_commit"),
        git_branch=payload.get("git_branch"),
        git_dirty=payload.get("git_dirty", False),
        scenario_runs=[
            EvalScenarioRunSummary(
                scenario_id=item["scenario_id"],
                passed=item["passed"],
                require_manual_review_accept=item["require_manual_review_accept"],
                manual_review_accept_satisfied=item["manual_review_accept_satisfied"],
                final_judgment=item["final_judgment"],
                output_dir=item["output_dir"],
                verdict_path=item["verdict_path"],
                manual_review_report_path=item["manual_review_report_path"],
            )
            for item in payload.get("scenario_runs", [])
        ],
    )


def run_named_scenario(
    repo_root: Path,
    scenario_id: str,
    output_dir: Path,
    catalog_path: Optional[Path] = None,
    scenarios_path: Optional[Path] = None,
) -> Tuple[Path, ScenarioVerdict]:
    resolved_scenarios_path = _scenario_config_path(repo_root, catalog_path, scenarios_path)
    scenarios = load_evaluation_scenarios(resolved_scenarios_path)
    pipeline, coverage_report, corpus_state_id, resolved_catalog_path = _run_pipeline(
        repo_root,
        catalog_path=catalog_path,
    )

    scenario = next(item for item in scenarios if item.scenario_id == scenario_id)
    result = pipeline.answer_question(scenario.question)
    result.corpus_coverage_report = coverage_report
    verdict, review_report = _evaluate_scenario_with_review_report(scenario, result)
    if coverage_report is not None:
        if coverage_report.passed:
            verdict.checks.append("corpus_coverage_gate:ok")
        else:
            verdict.checks.append("corpus_coverage_gate:fail")
            verdict.passed = False

    scenario_dir = output_dir / scenario_id
    write_artifact_bundle(
        scenario_dir,
        result,
        verdict=verdict,
        scenario_id=scenario_id,
        catalog_path=resolved_catalog_path,
        corpus_state_id=corpus_state_id,
        manual_review_report=review_report,
    )
    return scenario_dir, verdict


def run_all_scenarios(
    repo_root: Path,
    output_dir: Path,
    catalog_path: Optional[Path] = None,
    scenarios_path: Optional[Path] = None,
) -> List[Tuple[str, ScenarioVerdict]]:
    resolved_scenarios_path = _scenario_config_path(repo_root, catalog_path, scenarios_path)
    scenarios = load_evaluation_scenarios(resolved_scenarios_path)
    pipeline, coverage_report, corpus_state_id, resolved_catalog_path = _run_pipeline(
        repo_root,
        catalog_path=catalog_path,
    )
    from eubw_researcher.runtime_facade import ResearchRuntimeFacade

    results: List[Tuple[str, ScenarioVerdict]] = []
    scenario_runs: List[EvalScenarioRunSummary] = []
    for scenario in scenarios:
        result = pipeline.answer_question(scenario.question)
        result.corpus_coverage_report = coverage_report
        verdict, review_report = _evaluate_scenario_with_review_report(scenario, result)
        if coverage_report is not None:
            if coverage_report.passed:
                verdict.checks.append("corpus_coverage_gate:ok")
            else:
                verdict.checks.append("corpus_coverage_gate:fail")
                verdict.passed = False
        scenario_dir = output_dir / scenario.scenario_id
        write_artifact_bundle(
            scenario_dir,
            result,
            verdict=verdict,
            scenario_id=scenario.scenario_id,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
            manual_review_report=review_report,
        )
        scenario_runs.append(
            EvalScenarioRunSummary(
                scenario_id=scenario.scenario_id,
                passed=verdict.passed,
                require_manual_review_accept=scenario.require_manual_review_accept,
                manual_review_accept_satisfied=(
                    review_report.final_judgment == "accept"
                    if scenario.require_manual_review_accept
                    else False
                ),
                final_judgment=review_report.final_judgment,
                output_dir=str(scenario_dir.resolve()),
                verdict_path=str((scenario_dir / "verdict.json").resolve()),
                manual_review_report_path=str(
                    (scenario_dir / "manual_review_report.md").resolve()
                ),
            )
        )
        results.append((scenario.scenario_id, verdict))
    coverage_report_path = None
    coverage_summary_path = None
    if coverage_report is not None:
        coverage_report_path = output_dir / "corpus_coverage_report.json"
        coverage_summary_path = output_dir / "corpus_coverage_summary.md"
        write_corpus_coverage_report(coverage_report, coverage_report_path)
        coverage_summary_path.write_text(
            render_corpus_coverage_summary_md(coverage_report),
            encoding="utf-8",
        )
    manifest = build_eval_run_manifest(
        repo_root,
        output_dir=output_dir,
        scenario_config_path=resolved_scenarios_path,
        catalog_path=resolved_catalog_path,
        corpus_state_id=corpus_state_id,
        runtime_contract_version=ResearchRuntimeFacade.CONTRACT_VERSION,
        scenario_runs=scenario_runs,
        coverage_gate_passed=coverage_report.passed if coverage_report is not None else None,
        coverage_report_path=coverage_report_path,
        coverage_summary_path=coverage_summary_path,
    )
    write_eval_run_manifest(manifest, output_dir / "eval_run_manifest.json")
    return results
