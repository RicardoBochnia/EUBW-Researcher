from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from eubw_researcher.config import (
    load_runtime_config,
    load_source_hierarchy,
    load_web_allowlist,
)
from eubw_researcher.corpus import load_or_build_ingestion_bundle
from eubw_researcher.evaluation.runner import (
    default_output_dir,
    run_all_scenarios,
    run_named_scenario,
    write_artifact_bundle,
)
from eubw_researcher.pipeline import ResearchPipeline

AGENT_RUNTIME_CONTRACT_VERSION = "option_a_agent_runtime_v1"
DEFAULT_AGENT_ANSWER_CATALOG = Path("artifacts/real_corpus/curated_catalog.json")
DEFAULT_AGENT_EVAL_CATALOG = Path("tests/fixtures/catalog/source_catalog.yaml")
PathLike = Union[str, Path]


@dataclass(frozen=True)
class AgentAnswerRun:
    runtime_contract_version: str
    mode: str
    question: str
    catalog_path: str
    corpus_state_id: str
    output_dir: Optional[str]
    final_answer_path: Optional[str]
    rendered_answer: str


@dataclass(frozen=True)
class AgentBundleRun:
    runtime_contract_version: str
    mode: str
    question: str
    catalog_path: str
    corpus_state_id: str
    output_dir: str
    final_answer_path: str
    artifacts: List[str]


@dataclass(frozen=True)
class AgentScenarioEvaluation:
    scenario_id: str
    passed: bool
    output_dir: str


@dataclass(frozen=True)
class AgentEvaluationRun:
    runtime_contract_version: str
    mode: str
    catalog_path: str
    output_dir: str
    results: List[AgentScenarioEvaluation]


class AgentRuntimeFacade:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def _resolve_path(self, path: Optional[PathLike], *, default: Path) -> Path:
        candidate = default if path is None else Path(path)
        if not candidate.is_absolute():
            candidate = self.repo_root / candidate
        return candidate.resolve()

    def _resolve_required_path(self, path: PathLike) -> Path:
        return self._resolve_path(path, default=Path("."))

    def _load_pipeline(self, catalog_path: Optional[PathLike], *, default_catalog: Path):
        resolved_catalog_path = self._resolve_path(catalog_path, default=default_catalog)
        _catalog, bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(
            resolved_catalog_path
        )
        pipeline = ResearchPipeline(
            runtime_config=load_runtime_config(self.repo_root / "configs" / "runtime.yaml"),
            hierarchy=load_source_hierarchy(self.repo_root / "configs" / "source_hierarchy.yaml"),
            allowlist=load_web_allowlist(self.repo_root / "configs" / "web_allowlist.yaml"),
            ingestion_bundle=bundle,
        )
        return pipeline, coverage_report, corpus_state_id, resolved_catalog_path

    def answer_question(
        self,
        question: str,
        *,
        catalog_path: Optional[PathLike] = None,
        output_dir: Optional[PathLike] = None,
    ) -> AgentAnswerRun:
        pipeline, coverage_report, corpus_state_id, resolved_catalog_path = self._load_pipeline(
            catalog_path,
            default_catalog=DEFAULT_AGENT_ANSWER_CATALOG,
        )
        result = pipeline.answer_question(question)
        result.corpus_coverage_report = coverage_report

        resolved_output_dir: Optional[Path] = None
        if output_dir is not None:
            resolved_output_dir = self._resolve_required_path(output_dir)
            write_artifact_bundle(
                resolved_output_dir,
                result,
                catalog_path=resolved_catalog_path,
                corpus_state_id=corpus_state_id,
            )

        return AgentAnswerRun(
            runtime_contract_version=AGENT_RUNTIME_CONTRACT_VERSION,
            mode="answer_question",
            question=question,
            catalog_path=str(resolved_catalog_path),
            corpus_state_id=corpus_state_id,
            output_dir=str(resolved_output_dir) if resolved_output_dir else None,
            final_answer_path=(
                str(resolved_output_dir / "final_answer.txt")
                if resolved_output_dir is not None
                else None
            ),
            rendered_answer=result.rendered_answer,
        )

    def write_reviewable_artifact_bundle(
        self,
        question: str,
        *,
        output_dir: PathLike,
        catalog_path: Optional[PathLike] = None,
    ) -> AgentBundleRun:
        pipeline, coverage_report, corpus_state_id, resolved_catalog_path = self._load_pipeline(
            catalog_path,
            default_catalog=DEFAULT_AGENT_ANSWER_CATALOG,
        )
        result = pipeline.answer_question(question)
        result.corpus_coverage_report = coverage_report

        resolved_output_dir = self._resolve_required_path(output_dir)
        write_artifact_bundle(
            resolved_output_dir,
            result,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
        )

        return AgentBundleRun(
            runtime_contract_version=AGENT_RUNTIME_CONTRACT_VERSION,
            mode="write_reviewable_artifact_bundle",
            question=question,
            catalog_path=str(resolved_catalog_path),
            corpus_state_id=corpus_state_id,
            output_dir=str(resolved_output_dir),
            final_answer_path=str(resolved_output_dir / "final_answer.txt"),
            artifacts=sorted(path.name for path in resolved_output_dir.iterdir() if path.is_file()),
        )

    def run_named_evaluation(
        self,
        scenario_id: str,
        *,
        output_dir: Optional[PathLike] = None,
        catalog_path: Optional[PathLike] = None,
        scenarios_path: Optional[PathLike] = None,
    ) -> AgentEvaluationRun:
        resolved_catalog_path = self._resolve_path(
            catalog_path,
            default=DEFAULT_AGENT_EVAL_CATALOG,
        )
        resolved_output_dir = (
            self._resolve_required_path(output_dir)
            if output_dir is not None
            else default_output_dir(self.repo_root, resolved_catalog_path).resolve()
        )
        resolved_scenarios_path = (
            self._resolve_required_path(scenarios_path)
            if scenarios_path is not None
            else None
        )
        scenario_dir, verdict = run_named_scenario(
            repo_root=self.repo_root,
            scenario_id=scenario_id,
            output_dir=resolved_output_dir,
            catalog_path=resolved_catalog_path,
            scenarios_path=resolved_scenarios_path,
        )
        return AgentEvaluationRun(
            runtime_contract_version=AGENT_RUNTIME_CONTRACT_VERSION,
            mode="run_named_evaluation",
            catalog_path=str(resolved_catalog_path),
            output_dir=str(resolved_output_dir),
            results=[
                AgentScenarioEvaluation(
                    scenario_id=scenario_id,
                    passed=verdict.passed,
                    output_dir=str(scenario_dir),
                )
            ],
        )

    def run_all_evaluations(
        self,
        *,
        output_dir: Optional[PathLike] = None,
        catalog_path: Optional[PathLike] = None,
        scenarios_path: Optional[PathLike] = None,
    ) -> AgentEvaluationRun:
        resolved_catalog_path = self._resolve_path(
            catalog_path,
            default=DEFAULT_AGENT_EVAL_CATALOG,
        )
        resolved_output_dir = (
            self._resolve_required_path(output_dir)
            if output_dir is not None
            else default_output_dir(self.repo_root, resolved_catalog_path).resolve()
        )
        resolved_scenarios_path = (
            self._resolve_required_path(scenarios_path)
            if scenarios_path is not None
            else None
        )
        results = run_all_scenarios(
            repo_root=self.repo_root,
            output_dir=resolved_output_dir,
            catalog_path=resolved_catalog_path,
            scenarios_path=resolved_scenarios_path,
        )
        return AgentEvaluationRun(
            runtime_contract_version=AGENT_RUNTIME_CONTRACT_VERSION,
            mode="run_all_evaluations",
            catalog_path=str(resolved_catalog_path),
            output_dir=str(resolved_output_dir),
            results=[
                AgentScenarioEvaluation(
                    scenario_id=scenario_id,
                    passed=verdict.passed,
                    output_dir=str(resolved_output_dir / scenario_id),
                )
                for scenario_id, verdict in results
            ],
        )
