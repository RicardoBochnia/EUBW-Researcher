# Option A runtime facade contract

The stable agent-facing package-root surface for the current Option A runtime is the facade contract exported from `eubw_researcher`:

- `ResearchRuntimeFacade`
- `AgentRuntimeRequest`
- `AgentRuntimeResponse`
- `AgentRuntimeMode`

## Contract version

- contract id: `option_a_runtime.v1`

## Public surface

- `ResearchRuntimeFacade.answer_question(question, catalog_path=None)`
- `ResearchRuntimeFacade.run_evidence_only(question, catalog_path=None)`
- `ResearchRuntimeFacade.write_reviewable_artifact_bundle(question, output_dir, catalog_path=None)`
- `ResearchRuntimeFacade.run(AgentRuntimeRequest(...))`

The facade accepts one question per request and resolves config, corpus loading, pipeline creation, and artifact writing internally.

## Supported modes

- `answer_question`
  - returns the full `AnswerResult`
  - does not write artifacts
- `evidence_only`
  - returns the same `AnswerResult` contract
  - intended for agents that want the ledger, gap records, and reviewable evidence structures without using the artifact-writer route
- `write_reviewable_artifact_bundle`
  - runs the same deterministic question path
  - writes the standard review bundle to `output_dir`

## Deterministic routing rules

- relative paths are resolved from the repository root passed to the facade
- omitted `catalog_path` resolves to `artifacts/real_corpus/curated_catalog.json`
- `output_dir` is only accepted for `write_reviewable_artifact_bundle`
- `write_reviewable_artifact_bundle` requires `output_dir`
- blank questions are rejected

## Response contract

Each facade call returns `AgentRuntimeResponse` with:

- `contract_version`
- `mode`
- `catalog_path`
- `corpus_state_id`
- `output_dir`
- `result`

`result` is the existing `AnswerResult`, including the review artifacts that are already part of the runtime contract such as:

- `retrieval_plan`
- `gap_records`
- `web_fetch_records`
- `ledger_entries`
- `approved_entries`
- `rendered_answer`
- `provisional_grouping`
- `pinpoint_evidence_report`
- `answer_alignment_report`
- `blind_validation_report`
- `corpus_coverage_report`

## Stability boundary

Agents should treat this package-root facade contract as the stable programmatic surface.

Internal modules and types such as direct pipeline wiring, `ResearchPipeline`, config loading helpers, retrieval internals, and artifact-writing internals are implementation details and may change without notice.
