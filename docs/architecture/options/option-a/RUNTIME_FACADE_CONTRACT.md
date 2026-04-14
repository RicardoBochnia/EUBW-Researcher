# Option A runtime facade contract

The stable agent-facing package-root surface for the current Option A runtime is the facade contract exported from `eubw_researcher`:

- `ResearchRuntimeFacade`
- `AgentRuntimeRequest`
- `AgentRuntimeResponse`
- `AgentRuntimeResult`
- `AgentRuntimeMode`

## Contract version

- runtime contract id: `option_a_runtime.v2`
- result schema id: `agent_runtime_result.v3`

The runtime contract version covers the facade entrypoints and response envelope.
The result schema version covers the narrowed `AgentRuntimeResult` payload carried in `AgentRuntimeResponse.result`.

## Breaking change from v1

`option_a_runtime.v2` is a breaking contract change relative to `option_a_runtime.v1`.

Migration notes:

- callers that gated on `response.contract_version == "option_a_runtime.v1"` must now accept `option_a_runtime.v2`
- callers that relied on the public response being the internal `AnswerResult` should type against `AgentRuntimeResult` instead
- `response.result` remains the stable access point, but only the fields documented below are part of the public agent contract

## Public surface

- `ResearchRuntimeFacade.answer_question(question, catalog_path=None, runtime_config_path=None)`
- `ResearchRuntimeFacade.run_evidence_only(question, catalog_path=None, runtime_config_path=None)`
- `ResearchRuntimeFacade.write_reviewable_artifact_bundle(question, output_dir, catalog_path=None, runtime_config_path=None)`
- `ResearchRuntimeFacade.run(AgentRuntimeRequest(...))`

The facade accepts one question per request and resolves config, corpus loading, pipeline creation, and artifact writing internally.

## Supported modes

- `answer_question`
  - returns `AgentRuntimeResponse` with a narrowed `AgentRuntimeResult`
  - does not write artifacts
- `evidence_only`
  - returns the same narrowed `AgentRuntimeResult`
  - intended for agents that need the stable review/evidence payload without using the artifact-writer route
- `write_reviewable_artifact_bundle`
  - runs the same deterministic question path
  - writes the standard review bundle to `output_dir`
  - still returns the narrowed `AgentRuntimeResult`

## Deterministic routing rules

- relative paths are resolved from the repository root passed to the facade
- omitted `catalog_path` resolves to `artifacts/real_corpus/curated_catalog.json`
- omitted `runtime_config_path` resolves to `configs/runtime.yaml`
- `output_dir` is only accepted for `write_reviewable_artifact_bundle`
- `write_reviewable_artifact_bundle` requires `output_dir`
- blank questions are rejected

## Response envelope

Each facade call returns `AgentRuntimeResponse` with:

- `contract_version`
- `result_schema_version`
- `mode`
- `catalog_path`
- `corpus_state_id`
- `output_dir`
- `result`

## Stable result payload

`result` is `AgentRuntimeResult`, a facade-owned payload that exposes only the supported stable fields for agent use:

- `question`
- `query_intent`
- `retrieval_plan`
  - includes `normalized_question`, `question_term_normalizations`, and `target_queries` for reviewable query normalization traceability
  - includes `local_retrieval_backend`, `local_index_candidate_pool`, `local_index_cache_status`, and `local_backend_fallback_used` for stable local-retrieval backend traceability
- `gap_records`
- `web_fetch_records`
- `ingestion_report`
- `ledger_entries`
- `approved_entries`
- `rendered_answer`
- `provisional_grouping`
- `facet_coverage_report`
- `pinpoint_evidence_report`
- `answer_alignment_report`
- `blind_validation_report`
- `corpus_coverage_report`

These fields are returned as stable plain-data structures suitable for agent consumption.

## Stability boundary

Agents should treat this package-root facade contract as the stable programmatic surface.

Internal modules and types such as direct pipeline wiring, `ResearchPipeline`, config loading helpers, retrieval internals, artifact-writing internals, and the internal `eubw_researcher.models.AnswerResult` are implementation details and may change without notice.

The facade still uses the internal `AnswerResult` for pipeline execution and artifact writing, but that internal model is no longer part of the package-root public response contract.
