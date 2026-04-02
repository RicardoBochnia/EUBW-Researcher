# Option A Agent Runtime Guide

Use this guide when the task is to run, validate, or inspect the current Option A V2 implementation.

## Goal

Treat the repository as an inspectable backend research system, not as a speculative architecture draft.

The primary usage pattern is:
1. build or reuse the real-corpus catalog
2. run the CLI entrypoint
3. inspect the reviewable artifact bundle
4. judge the result from artifacts plus final answer, not from answer text alone

## Default entrypoints

- Stable agent-facing facade:
  `from eubw_researcher import AgentRuntimeFacade`
- Stable agent wrapper for direct questions:
  `python3 scripts/agent_answer_question.py "<question>" --output-dir artifacts/manual_runs/<run-name>`
- Stable agent wrapper for eval routing:
  `python3 scripts/agent_run_eval.py --scenario scenario_c_protocol_authorization_server`
- Build or refresh the real-corpus catalog:
  `python3 scripts/build_real_corpus_catalog.py`
- Run the full testsuite, including Scenario D closeout coverage:
  `python3 scripts/run_tests.py`
- Run only the separate Scenario D closeout harness tests:
  `python3 scripts/run_closeout_tests.py`
- Run fixture eval:
  `python3 scripts/run_eval.py --all`
- Run real-corpus eval:
  `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Run one direct research question:
  `python3 scripts/answer_question.py "<question>" --catalog artifacts/real_corpus/curated_catalog.json --output-dir artifacts/manual_runs/<run-name>`
- Run the separate Scenario D closeout harness:
  `python3 scripts/run_scenario_d_closeout.py --catalog artifacts/real_corpus/curated_catalog.json --validator-command "<validator command>"`

The closeout harness invokes the validator as:
- `<validator command> --input <request.json> --output <result.json>`

Unless there is a strong reason otherwise, use the default real-corpus catalog at:
- `artifacts/real_corpus/curated_catalog.json`

For the stable agent facade, use the built-in defaults unless the task explicitly needs another catalog:
- direct question and artifact-bundle runs default to `artifacts/real_corpus/curated_catalog.json`
- eval runs default to `tests/fixtures/catalog/source_catalog.yaml`

## Stable agent-facing contract

Use `AgentRuntimeFacade` when an agent needs one narrow, reviewable runtime surface without importing internal pipeline or evaluation modules directly.

The current contract version is:
- `option_a_agent_runtime_v1`

The supported stable operations are:
- `answer_question(...)`
- `write_reviewable_artifact_bundle(...)`
- `run_named_evaluation(...)`
- `run_all_evaluations(...)`

The wrapper scripts return JSON summaries keyed by the same contract version and route labels, so agents can make deterministic decisions without reconstructing repo internals.

The `agent_answer_question.py` wrapper supports two modes:
- default answer mode returns the rendered answer plus optional artifact paths
- `--artifacts-only` writes the reviewable bundle and returns only the bundle summary

Keep using the existing `scripts/answer_question.py` and `scripts/run_eval.py` for legacy CLI compatibility. The new facade is the stable agent entry; the older scripts remain direct project CLIs, not the versioned agent contract.

## Preferred operating pattern

For verification or review tasks:
- read `README.md`
- read `docs/architecture/options/option-a/REVIEW_GUIDE.md`
- read `docs/architecture/options/option-a/MANUAL_REVIEW_CHECKLIST.md`
- run the relevant CLI command
- inspect the generated artifact bundle

For exploratory usage tasks:
- run `scripts/answer_question.py`
- always provide `--output-dir`
- inspect artifacts in that run directory before making strong claims about correctness

## Artifact-first review surface

Do not treat the rendered answer alone as sufficient evidence.

The highest-value artifacts are:
- `final_answer.txt`
- `manual_review_report.md`
- `approved_ledger.json`
- `pinpoint_evidence.json`
- `answer_alignment.json`
- `blind_validation_report.json`
- `gap_records.json`
- `web_fetch_records.json`
- `retrieval_plan.json`
- `provisional_grouping.json` when present
- `corpus_coverage_report.json` for corpus-backed runs

For Scenario D closeout runs, also inspect:
- `spawned_validator_request.json`
- `spawned_validator_result.json`

## V2 boundaries to respect

Do not mis-state these accepted boundaries as bugs unless the user explicitly wants to go beyond V2:
- no UI
- no persistent provenance graph
- no multi-agent orchestration inside the product
- the Scenario D spawned-validator proof is a separate review harness, not in-product orchestration
- no arbitrary open-web search
- Germany remains best-effort, not a broad member-state engine
- real-corpus acceptance means reviewable, uncertainty-aware, source-bound output, not exact wording parity with fixtures

## When to rebuild inputs

Rebuild the real-corpus catalog when:
- `artifacts/real_corpus/curated_catalog.json` is missing
- `configs/real_corpus_selection.yaml` changed
- the local archive under `artifacts/real_corpus/archive` changed

Otherwise prefer reusing the existing catalog and cached ingestion bundle.
