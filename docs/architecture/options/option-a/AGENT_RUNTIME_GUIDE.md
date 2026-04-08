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

- Build or refresh the real-corpus catalog:
  `python3 scripts/build_real_corpus_catalog.py`
- Run the user-triggered real-corpus refresh check against the stored canonical source URLs:
  `python3 scripts/refresh_real_corpus.py`
  - this stages changed or missing candidates under `artifacts/real_corpus/refresh_staging`
  - add `--apply` only when you intentionally want to update the accepted local archive and archive-catalog metadata
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

## Stable agent-facing runtime facade

For programmatic agent use, prefer `ResearchRuntimeFacade` from `eubw_researcher`.

The facade is the stable runtime contract for:
- answer-question runs
- evidence-only runs
- writing the standard reviewable artifact bundle

The contract is documented in `docs/architecture/options/option-a/RUNTIME_FACADE_CONTRACT.md`.
The current facade envelope is `option_a_runtime.v2`, and `AgentRuntimeResponse.result` is the narrowed `AgentRuntimeResult` payload rather than the internal pipeline `AnswerResult`.

Anything below that facade boundary should be treated as internal implementation detail.

The closeout harness invokes the validator as:
- `<validator command> --input <request.json> --output <result.json>`

Unless there is a strong reason otherwise, use the default real-corpus catalog at:
- `artifacts/real_corpus/curated_catalog.json`

## Preferred operating pattern

- prefer `ResearchRuntimeFacade` for programmatic agent-driven runs
- use the documented CLI entrypoints when validating end-to-end behavior
- default to the curated real-corpus catalog unless the task explicitly requires another input
- inspect the generated artifact bundle as the primary review surface, not answer text alone

## Refresh Governance Decision

Treat refresh differently from discovery:
- discovery remains allowlist-governed and path-gated for finding new sources
- refresh may only re-check the exact stored `canonical_url` for an already accepted archive entry
- refresh must not perform discovery, link-following, alternate-source search, or silent source replacement
- refresh should therefore not be blocked just because the canonical URL lacks a discovery allowlist rule
- archive writes still remain bounded to paths inside `artifacts/real_corpus/archive`

## Wave 3 discovery contract

Treat official discovery as an exact-host policy system, not a suffix-matching host-family crawler:
- `configs/web_allowlist.yaml` is exact-host-only; `docs.eudi.dev` is distinct from `eudi.dev`, and `commission.europa.eu` is distinct from `ec.europa.eu`
- domain policies may share the same host when they differ by `source_kind`; use the kind-aware policy lookup rather than assuming one policy per domain
- `seed_urls` remain direct fetch candidates
- discovery entrypoints are now structured as `discovery_entrypoints` with `entrypoint_id`, `url_template`, and `strategy`
- `official_search` is currently restricted to the EUR-Lex quick-search HTML endpoint; do not generalize it into arbitrary site-search or third-party search
- `publications.europa.eu` is an official document host and permitted cross-domain follow-up target for legal EUR-Lex policies, but it is not currently configured as its own search endpoint
- document admission is stricter than crawl permission: `crawl_path_prefixes` govern what discovery may follow, while `admission_path_prefixes` govern what may enter the fetched-evidence path

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

For Wave 3 web-review runs, also inspect the per-record governance fields in `web_fetch_records.json` and the approved fetched-source section in `manual_review_report.md`:
- `policy_id`
- `entrypoint_id`
- `discovery_strategy`
- `admission_rule`
- `discovery_query`

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
