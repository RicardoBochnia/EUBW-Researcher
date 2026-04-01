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
- Run the full testsuite:
  `python3 scripts/run_tests.py`
- Run fixture eval:
  `python3 scripts/run_eval.py --all`
- Run real-corpus eval:
  `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Run one direct research question:
  `python3 scripts/answer_question.py "<question>" --catalog artifacts/real_corpus/curated_catalog.json --output-dir artifacts/manual_runs/<run-name>`

Unless there is a strong reason otherwise, use the default real-corpus catalog at:
- `artifacts/real_corpus/curated_catalog.json`

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
- `gap_records.json`
- `web_fetch_records.json`
- `retrieval_plan.json`
- `provisional_grouping.json` when present
- `corpus_coverage_report.json` for corpus-backed runs

## V2 boundaries to respect

Do not mis-state these accepted boundaries as bugs unless the user explicitly wants to go beyond V2:
- no UI
- no persistent provenance graph
- no multi-agent orchestration inside the product
- no arbitrary open-web search
- Germany remains best-effort, not a broad member-state engine
- real-corpus acceptance means reviewable, uncertainty-aware, source-bound output, not exact wording parity with fixtures

## When to rebuild inputs

Rebuild the real-corpus catalog when:
- `artifacts/real_corpus/curated_catalog.json` is missing
- `configs/real_corpus_selection.yaml` changed
- the local archive under `artifacts/real_corpus/archive` changed

Otherwise prefer reusing the existing catalog and cached ingestion bundle.
