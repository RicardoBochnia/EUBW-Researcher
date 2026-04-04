from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from eubw_researcher.config import (
    load_runtime_config,
    load_source_hierarchy,
    load_web_allowlist,
)
from eubw_researcher.corpus import load_or_build_ingestion_bundle
from eubw_researcher.models import (
    AnswerAlignmentReport,
    AnswerResult,
    BlindValidationReport,
    CorpusCoverageReport,
    FacetCoverageReport,
    GapRecord,
    IngestionReportEntry,
    LedgerEntry,
    PinpointEvidenceReport,
    ProvisionalGroup,
    QueryIntent,
    RetrievalPlan,
    WebFetchRecord,
)
from eubw_researcher.pipeline import ResearchPipeline

RuntimePath = Union[str, Path]


class AgentRuntimeMode(str, Enum):
    ANSWER_QUESTION = "answer_question"
    EVIDENCE_ONLY = "evidence_only"
    WRITE_REVIEWABLE_ARTIFACT_BUNDLE = "write_reviewable_artifact_bundle"


@dataclass(frozen=True)
class AgentRuntimeRequest:
    """Stable runtime request payload.

    `mode` accepts either an `AgentRuntimeMode` member or one of its string values:
    `answer_question`, `evidence_only`, or `write_reviewable_artifact_bundle`.
    """

    question: str
    mode: Union[AgentRuntimeMode, str] = AgentRuntimeMode.ANSWER_QUESTION
    catalog_path: Optional[RuntimePath] = None
    output_dir: Optional[RuntimePath] = None


@dataclass(frozen=True)
class AgentRuntimeResponse:
    contract_version: str
    result_schema_version: str
    mode: AgentRuntimeMode
    catalog_path: Path
    corpus_state_id: str
    output_dir: Optional[Path]
    result: AgentRuntimeResult


@dataclass(frozen=True)
class AgentRuntimeResult:
    question: str
    query_intent: QueryIntent
    retrieval_plan: RetrievalPlan
    gap_records: list[GapRecord]
    web_fetch_records: list[WebFetchRecord]
    ingestion_report: list[IngestionReportEntry]
    ledger_entries: list[LedgerEntry]
    approved_entries: list[LedgerEntry]
    rendered_answer: str
    provisional_grouping: list[ProvisionalGroup]
    facet_coverage_report: Optional[FacetCoverageReport] = None
    pinpoint_evidence_report: Optional[PinpointEvidenceReport] = None
    answer_alignment_report: Optional[AnswerAlignmentReport] = None
    blind_validation_report: Optional[BlindValidationReport] = None
    corpus_coverage_report: Optional[CorpusCoverageReport] = None


class ResearchRuntimeFacade:
    """Stable agent-facing runtime facade for Option A."""

    CONTRACT_VERSION = "option_a_runtime.v2"
    RESULT_SCHEMA_VERSION = "agent_runtime_result.v1"
    DEFAULT_CATALOG_PATH = Path("artifacts/real_corpus/curated_catalog.json")

    def __init__(self, repo_root: RuntimePath) -> None:
        self.repo_root = Path(repo_root).resolve()

    def answer_question(
        self,
        question: str,
        *,
        catalog_path: Optional[RuntimePath] = None,
    ) -> AgentRuntimeResponse:
        return self.run(
            AgentRuntimeRequest(
                question=question,
                mode=AgentRuntimeMode.ANSWER_QUESTION,
                catalog_path=catalog_path,
            )
        )

    def run_evidence_only(
        self,
        question: str,
        *,
        catalog_path: Optional[RuntimePath] = None,
    ) -> AgentRuntimeResponse:
        return self.run(
            AgentRuntimeRequest(
                question=question,
                mode=AgentRuntimeMode.EVIDENCE_ONLY,
                catalog_path=catalog_path,
            )
        )

    def write_reviewable_artifact_bundle(
        self,
        question: str,
        output_dir: RuntimePath,
        *,
        catalog_path: Optional[RuntimePath] = None,
    ) -> AgentRuntimeResponse:
        return self.run(
            AgentRuntimeRequest(
                question=question,
                mode=AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE,
                catalog_path=catalog_path,
                output_dir=output_dir,
            )
        )

    def run(self, request: AgentRuntimeRequest) -> AgentRuntimeResponse:
        mode = self._coerce_mode(request.mode)
        normalized_question = self._normalize_question(request.question)
        output_dir = self._resolve_output_dir(mode, request.output_dir)
        internal_result, resolved_catalog_path, corpus_state_id = self._execute_question(
            normalized_question,
            request.catalog_path,
        )
        if mode == AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE:
            assert output_dir is not None
            self._write_artifact_bundle(
                output_dir,
                internal_result,
                catalog_path=resolved_catalog_path,
                corpus_state_id=corpus_state_id,
            )
        return AgentRuntimeResponse(
            contract_version=self.CONTRACT_VERSION,
            result_schema_version=self.RESULT_SCHEMA_VERSION,
            mode=mode,
            catalog_path=resolved_catalog_path,
            corpus_state_id=corpus_state_id,
            output_dir=output_dir,
            result=self._to_public_result(internal_result),
        )

    def _execute_question(
        self,
        question: str,
        catalog_path: Optional[RuntimePath],
    ) -> tuple[AnswerResult, Path, str]:
        resolved_catalog_path = self._resolve_catalog_path(catalog_path)
        _, bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(
            resolved_catalog_path
        )
        pipeline = ResearchPipeline(
            runtime_config=load_runtime_config(
                self.repo_root / "configs" / "runtime.yaml"
            ),
            hierarchy=load_source_hierarchy(
                self.repo_root / "configs" / "source_hierarchy.yaml"
            ),
            allowlist=load_web_allowlist(
                self.repo_root / "configs" / "web_allowlist.yaml"
            ),
            ingestion_bundle=bundle,
        )
        result = pipeline.answer_question(question)
        result.corpus_coverage_report = coverage_report
        return result, resolved_catalog_path, corpus_state_id

    def _resolve_catalog_path(self, catalog_path: Optional[RuntimePath]) -> Path:
        resolved_path = self._resolve_path(catalog_path or self.DEFAULT_CATALOG_PATH)
        if not resolved_path.exists():
            raise FileNotFoundError(f"Catalog file not found: {resolved_path}")
        if not resolved_path.is_file():
            raise ValueError(f"Catalog path is not a file: {resolved_path}")
        return resolved_path

    def _resolve_output_dir(
        self,
        mode: AgentRuntimeMode,
        output_dir: Optional[RuntimePath],
    ) -> Optional[Path]:
        if mode == AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE:
            if output_dir is None:
                raise ValueError("output_dir is required for write_reviewable_artifact_bundle")
            if isinstance(output_dir, str) and not output_dir.strip():
                raise ValueError("output_dir must not be empty")
            resolved_output_dir = self._resolve_path(output_dir)
            if resolved_output_dir == self.repo_root:
                raise ValueError("output_dir must not resolve to the repository root")
            if resolved_output_dir.exists() and not resolved_output_dir.is_dir():
                raise ValueError(
                    f"output_dir must be a directory path: {resolved_output_dir}"
                )
            return resolved_output_dir
        if output_dir is not None:
            raise ValueError(
                "output_dir is only supported for "
                f"{AgentRuntimeMode.WRITE_REVIEWABLE_ARTIFACT_BUNDLE.value}"
            )
        return None

    def _resolve_path(self, value: RuntimePath) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.repo_root / path
        return path.resolve()

    @staticmethod
    def _write_artifact_bundle(
        output_dir: Path,
        result: AnswerResult,
        *,
        catalog_path: Path,
        corpus_state_id: str,
    ) -> None:
        from eubw_researcher.evaluation.runner import write_artifact_bundle

        write_artifact_bundle(
            output_dir,
            result,
            catalog_path=catalog_path,
            corpus_state_id=corpus_state_id,
        )

    @staticmethod
    def _coerce_mode(mode: Union[AgentRuntimeMode, str]) -> AgentRuntimeMode:
        if isinstance(mode, AgentRuntimeMode):
            return mode
        return AgentRuntimeMode(mode)

    @staticmethod
    def _to_public_result(result: AnswerResult) -> AgentRuntimeResult:
        return AgentRuntimeResult(
            question=result.question,
            query_intent=result.query_intent,
            retrieval_plan=result.retrieval_plan,
            gap_records=result.gap_records,
            web_fetch_records=result.web_fetch_records,
            ingestion_report=result.ingestion_report,
            ledger_entries=result.ledger_entries,
            approved_entries=result.approved_entries,
            rendered_answer=result.rendered_answer,
            provisional_grouping=result.provisional_grouping,
            facet_coverage_report=result.facet_coverage_report,
            pinpoint_evidence_report=result.pinpoint_evidence_report,
            answer_alignment_report=result.answer_alignment_report,
            blind_validation_report=result.blind_validation_report,
            corpus_coverage_report=result.corpus_coverage_report,
        )

    @staticmethod
    def _normalize_question(question: str) -> str:
        normalized = question.strip()
        if not normalized:
            raise ValueError("question must not be empty")
        return normalized
