from __future__ import annotations

import logging
from typing import Dict, List

from eubw_researcher.answering import (
    build_provisional_grouping,
    compose_answer_bundle,
)
from eubw_researcher.evidence import build_ledger, has_direct_admissible_support
from eubw_researcher.models import (
    AnswerResult,
    ClaimState,
    GapRecord,
    IngestionBundle,
    RetrievalCandidate,
    RetrievalPlanStep,
    RuntimeConfig,
    SourceCatalog,
    SourceKind,
    SourceRoleLevel,
    WebAllowlistConfig,
    WebFetchRecord,
)
from eubw_researcher.retrieval import analyze_query, build_retrieval_plan, retrieve_candidates
from eubw_researcher.trust import build_blind_validation_report
from eubw_researcher.web import fetch_and_normalize_official_sources

LOGGER = logging.getLogger(__name__)


class ResearchPipeline:
    def __init__(
        self,
        runtime_config: RuntimeConfig,
        hierarchy,
        allowlist: WebAllowlistConfig,
        ingestion_bundle: IngestionBundle,
    ) -> None:
        self.runtime_config = runtime_config
        self.hierarchy = hierarchy
        self.allowlist = allowlist
        self.ingestion_bundle = ingestion_bundle

    def _role_weight(self, role_level: SourceRoleLevel) -> int:
        return {
            SourceRoleLevel.HIGH: 3,
            SourceRoleLevel.MEDIUM: 2,
            SourceRoleLevel.LOW: 1,
        }[role_level]

    def _allowed_web_kinds(
        self,
        target,
        ledger_entry,
        *,
        intent_type: str | None = None,
    ) -> List[SourceKind]:
        available_kinds = [
            kind
            for kind in target.preferred_kinds
            if (
                self.allowlist.seed_urls_for_kind(kind, intent_type=intent_type)
                or self.allowlist.discovery_urls_for_kind(kind, intent_type=intent_type)
            )
            and self._role_weight(self.hierarchy.role_for(kind))
            <= self._role_weight(target.required_source_role_level)
        ]
        available_kinds.sort(
            key=lambda kind: (
                self._role_weight(self.hierarchy.role_for(kind)) == self._role_weight(target.required_source_role_level),
                -self.hierarchy.rank_for(kind),
            ),
            reverse=True,
        )
        same_rank_kinds = [
            kind
            for kind in available_kinds
            if self.hierarchy.role_for(kind) == target.required_source_role_level
        ]
        lower_rank_kinds = [kind for kind in available_kinds if kind not in same_rank_kinds]

        if ledger_entry.final_claim_state == ClaimState.OPEN:
            locally_present_kinds = {
                evidence.source_kind
                for evidence in (
                    ledger_entry.supporting_evidence
                    + ledger_entry.contradicting_evidence
                    + ledger_entry.governing_evidence
                )
                if evidence.source_origin.value == "local"
            }
            return [kind for kind in same_rank_kinds if kind not in locally_present_kinds]

        if same_rank_kinds:
            return same_rank_kinds
        return lower_rank_kinds

    def _next_allowed_action(self, target, ledger_entry, *, intent_type: str | None = None) -> str:
        if self._allowed_web_kinds(target, ledger_entry, intent_type=intent_type):
            return "official_web_search"
        return "stop_local_only"

    def _target_query_text(self, question: str, target) -> str:
        support_terms = [" ".join(group) for group in target.support_groups]
        return " ".join(
            [
                question,
                target.claim_text,
                " ".join(target.scope_terms),
                " ".join(target.primary_terms),
                " ".join(support_terms),
            ]
        )

    def _merge_candidates(self, candidate_groups: List[List[RetrievalCandidate]]) -> List[RetrievalCandidate]:
        by_chunk_id: Dict[str, RetrievalCandidate] = {}
        for candidates in candidate_groups:
            for candidate in candidates:
                existing = by_chunk_id.get(candidate.chunk.chunk_id)
                if existing is None or candidate.combined_score > existing.combined_score:
                    by_chunk_id[candidate.chunk.chunk_id] = candidate
        merged = list(by_chunk_id.values())
        merged.sort(
            key=lambda item: (
                item.combined_score,
                item.lexical_score,
                item.semantic_score,
            ),
            reverse=True,
        )
        return merged

    def _target_requires_layered_evidence(self, target) -> bool:
        return (
            len(target.preferred_kinds) > 1
            or bool(target.grouping_label)
            or target.claim_type.value == "synthesis"
        )

    def _local_retrieval(self, question: str, query_intent):
        retrieval_plan = build_retrieval_plan(
            query_intent=query_intent,
            hierarchy=self.hierarchy,
            runtime_config=self.runtime_config,
        )

        candidates_by_step: Dict[str, List[RetrievalCandidate]] = {}
        target_traces = {
            target.target_id: {
                "resolved": False,
                "local_source_layers_searched": [],
                "candidate_sources_inspected": [],
            }
            for target in query_intent.claim_targets
        }

        for step in retrieval_plan.steps:
            step_candidate_groups: List[List[RetrievalCandidate]] = []
            for target in query_intent.claim_targets:
                trace = target_traces[target.target_id]
                if trace["resolved"]:
                    continue
                target_candidates = retrieve_candidates(
                    question=self._target_query_text(question, target),
                    step=step,
                    bundle=self.ingestion_bundle,
                    hierarchy=self.hierarchy,
                    runtime_config=self.runtime_config,
                )
                step_candidate_groups.append(target_candidates)
                trace["local_source_layers_searched"].append(step.required_kind.value)
                trace["candidate_sources_inspected"].extend(
                    candidate.chunk.source_id for candidate in target_candidates
                )
                if (
                    has_direct_admissible_support(target, target_candidates, self.hierarchy)
                    and not self._target_requires_layered_evidence(target)
                ):
                    trace["resolved"] = True

            step_candidates = self._merge_candidates(step_candidate_groups)
            candidates_by_step[step.step_id] = step_candidates

            if all(trace["resolved"] for trace in target_traces.values()):
                break

        return retrieval_plan, candidates_by_step, target_traces

    def _build_gap_records(self, query_intent, target_traces, ledger_entries) -> List[GapRecord]:
        ledger_by_claim = {entry.claim_text: entry for entry in ledger_entries}
        gap_records: List[GapRecord] = []

        for target in query_intent.claim_targets:
            trace = target_traces[target.target_id]
            ledger_entry = ledger_by_claim[target.claim_text]
            needs_gap = ledger_entry.final_claim_state in (ClaimState.OPEN, ClaimState.BLOCKED) or (
                ledger_entry.final_claim_state == ClaimState.INTERPRETIVE
                and (
                    ledger_entry.source_role_level != target.required_source_role_level
                    or ledger_entry.support_directness.value == "indirect"
                    or ledger_entry.citation_quality.value == "document_only"
                )
            )
            if not needs_gap:
                continue

            if ledger_entry.final_claim_state == ClaimState.OPEN:
                reason = (
                    "Contradictory admissible evidence remains unresolved after ranked local search."
                )
            elif ledger_entry.final_claim_state == ClaimState.INTERPRETIVE:
                reason = (
                    "Only under-powered local support was found; the required governing support remains unresolved."
                )
            else:
                reason = (
                    "All ranked local layers for this target were inspected without direct admissible support."
                )
            gap_records.append(
                GapRecord(
                    sub_question=target.claim_text,
                    required_source_role_level=target.required_source_role_level,
                    local_source_layers_searched=list(trace["local_source_layers_searched"]),
                    retrieval_methods_used=["lexical", "semantic"],
                    candidate_sources_inspected=list(trace["candidate_sources_inspected"]),
                    reason_local_evidence_insufficient=reason,
                    next_allowed_action=self._next_allowed_action(
                        target,
                        ledger_entry,
                        intent_type=query_intent.intent_type,
                    ),
                    web_source_kinds_considered=[],
                    web_discovery_urls_attempted=[],
                    web_fetch_urls_attempted=[],
                )
            )

        return gap_records

    def _fetch_web_candidates(
        self,
        question: str,
        query_intent,
        gap_records: List[GapRecord],
        target_traces,
        ledger_entries,
    ) -> tuple[Dict[str, List[RetrievalCandidate]], List[WebFetchRecord], List]:
        web_candidates_by_step: Dict[str, List[RetrievalCandidate]] = {}
        web_fetch_records: List[WebFetchRecord] = []
        web_ingestion_reports: List = []

        target_by_claim = {target.claim_text: target for target in query_intent.claim_targets}
        ledger_by_claim = {entry.claim_text: entry for entry in ledger_entries}
        for gap_record in gap_records:
            if gap_record.next_allowed_action != "official_web_search":
                continue
            target = target_by_claim.get(gap_record.sub_question)
            if target is None:
                continue
            ledger_entry = ledger_by_claim.get(gap_record.sub_question)
            if ledger_entry is None:
                continue
            allowed_web_kinds = self._allowed_web_kinds(
                target,
                ledger_entry,
                intent_type=query_intent.intent_type,
            )
            if not allowed_web_kinds:
                continue
            LOGGER.info(
                "Triggering web expansion for %s because %s",
                target.target_id,
                gap_record.reason_local_evidence_insufficient,
            )
            documents, reports, fetch_records = fetch_and_normalize_official_sources(
                sub_question=gap_record.sub_question,
                source_kinds=allowed_web_kinds,
                allowlist=self.allowlist,
                runtime_config=self.runtime_config,
                intent_type=query_intent.intent_type,
            )
            web_fetch_records.extend(fetch_records)
            web_ingestion_reports.extend(reports)
            gap_record.web_source_kinds_considered = list(allowed_web_kinds)
            gap_record.web_discovery_urls_attempted = [
                record.canonical_url for record in fetch_records if record.record_type == "discovery"
            ]
            gap_record.web_fetch_urls_attempted = [
                record.canonical_url
                for record in fetch_records
                if record.record_type in {"fetch", "discovered_link"}
            ]
            if not documents:
                continue

            web_bundle = IngestionBundle(
                catalog=SourceCatalog(entries=[document.entry for document in documents]),
                documents=documents,
                report=reports,
            )
            for source_kind in allowed_web_kinds:
                step = RetrievalPlanStep(
                    step_id=f"web_{target.target_id}_{source_kind.value}",
                    required_kind=source_kind,
                    required_source_role_level=self.hierarchy.role_for(source_kind),
                    inspection_depth=self.runtime_config.retrieval_top_k,
                    reason="Gap-driven official web expansion.",
                )
                web_candidates = retrieve_candidates(
                    question=self._target_query_text(question, target),
                    step=step,
                    bundle=web_bundle,
                    hierarchy=self.hierarchy,
                    runtime_config=self.runtime_config,
                )
                if web_candidates:
                    target_traces[target.target_id]["local_source_layers_searched"].append(
                        f"web:{source_kind.value}"
                    )
                    target_traces[target.target_id]["candidate_sources_inspected"].extend(
                        candidate.chunk.source_id for candidate in web_candidates
                    )
                    web_candidates_by_step[step.step_id] = web_candidates

        return web_candidates_by_step, web_fetch_records, web_ingestion_reports

    def answer_question(self, question: str) -> AnswerResult:
        query_intent = analyze_query(question)
        retrieval_plan, local_candidates_by_step, target_traces = self._local_retrieval(
            question=question,
            query_intent=query_intent,
        )

        local_ledger_entries = build_ledger(
            query_intent=query_intent,
            candidates_by_step=local_candidates_by_step,
            hierarchy=self.hierarchy,
        )
        initial_gap_records = self._build_gap_records(
            query_intent=query_intent,
            target_traces=target_traces,
            ledger_entries=local_ledger_entries,
        )

        web_candidates_by_step: Dict[str, List[RetrievalCandidate]] = {}
        web_fetch_records: List[WebFetchRecord] = []
        web_ingestion_reports: List = []
        if any(gap.next_allowed_action == "official_web_search" for gap in initial_gap_records):
            web_candidates_by_step, web_fetch_records, web_ingestion_reports = self._fetch_web_candidates(
                question=question,
                query_intent=query_intent,
                gap_records=initial_gap_records,
                target_traces=target_traces,
                ledger_entries=local_ledger_entries,
            )

        combined_candidates_by_step = dict(local_candidates_by_step)
        combined_candidates_by_step.update(web_candidates_by_step)

        ledger_entries = build_ledger(
            query_intent=query_intent,
            candidates_by_step=combined_candidates_by_step,
            hierarchy=self.hierarchy,
        )
        approved_entries = [
            entry for entry in ledger_entries if entry.final_claim_state != ClaimState.BLOCKED
        ]

        gap_records = self._build_gap_records(
            query_intent=query_intent,
            target_traces=target_traces,
            ledger_entries=ledger_entries,
        )
        if web_fetch_records or any(
            gap.next_allowed_action == "official_web_search" for gap in initial_gap_records
        ):
            persisted_gaps = {gap.sub_question: gap for gap in gap_records}
            for gap in initial_gap_records:
                if gap.next_allowed_action != "official_web_search":
                    continue
                if gap.sub_question in persisted_gaps:
                    persisted = persisted_gaps[gap.sub_question]
                    persisted.web_source_kinds_considered = list(gap.web_source_kinds_considered)
                    persisted.web_discovery_urls_attempted = list(gap.web_discovery_urls_attempted)
                    persisted.web_fetch_urls_attempted = list(gap.web_fetch_urls_attempted)
                else:
                    gap_records.append(gap)

        composed_answer = compose_answer_bundle(
            question,
            approved_entries,
            query_intent=query_intent,
            clarification_note=query_intent.clarification_note,
            documents=self.ingestion_bundle.documents,
        )
        provisional_grouping = build_provisional_grouping(query_intent, approved_entries)
        result = AnswerResult(
            question=question,
            query_intent=query_intent,
            retrieval_plan=retrieval_plan,
            gap_records=gap_records,
            web_fetch_records=web_fetch_records,
            ingestion_report=[*self.ingestion_bundle.report, *web_ingestion_reports],
            ledger_entries=ledger_entries,
            approved_entries=approved_entries,
            rendered_answer=composed_answer.rendered_answer,
            provisional_grouping=provisional_grouping,
            facet_coverage_report=composed_answer.facet_coverage_report,
            pinpoint_evidence_report=composed_answer.pinpoint_evidence_report,
            answer_alignment_report=composed_answer.answer_alignment_report,
        )
        result.blind_validation_report = build_blind_validation_report(result)
        return result
