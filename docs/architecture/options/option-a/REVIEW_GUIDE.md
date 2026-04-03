# Option A Review Guide

Use this guide for a compact V2 review of the current Option A implementation.

## Review goal

Confirm that the repository currently delivers:

- an inspectable evidence-first pipeline
- visible claim-state control (`confirmed`, `interpretive`, `open`, `blocked`)
- hierarchy-aware source handling
- traceable retrieval gaps and constrained web expansion
- reviewable artifacts for both fixture and real-corpus runs

This is a V2 research-version review target, not a production-readiness claim.

## Recommended review order

1. Read the V2 contract in `V2_PLAN.md`.
2. Read `MANUAL_REVIEW_CHECKLIST.md`.
3. Read `HARDENING_NOTES.md`.
4. Run the automated gates.
5. Inspect one fixture eval run and one real-corpus eval run.

## Commands

- Run the full test suite, including Scenario D closeout coverage:
  `python3 scripts/run_tests.py`
- Run the fixture-backed evaluation gate:
  `python3 scripts/run_eval.py --all`
- Run the real-corpus evaluation gate:
  `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Run the Scenario D closeout harness with a spawned validator:
  `python3 scripts/run_scenario_d_closeout.py --catalog artifacts/real_corpus/curated_catalog.json --validator-command "<validator command>"`
- Run a direct question with reviewable artifacts:
  `python3 scripts/answer_question.py "What is the difference between a wallet-relying party registration certificate and a wallet-relying party access certificate?" --catalog artifacts/real_corpus/curated_catalog.json --output-dir artifacts/review_demo`
- Run the curated real-question manual-review pack:
  `python3 scripts/run_real_question_pack.py --all`

By default, fixture eval writes to `artifacts/eval_runs` and real-corpus eval writes to `artifacts/eval_runs_real_corpus`.
The real-corpus gate also reuses the cached normalized bundle under `artifacts/real_corpus/cache/` and writes `corpus_coverage_report.json` into each scenario bundle.
The real-question pack writes to `artifacts/real_question_pack_runs/<run-id>/...` and adds a top-level `pack_run_manifest.json` that records repo state, runtime contract, corpus state, and compact per-question review signals.

## What should be green

- `scripts/run_tests.py` should pass.
- Fixture eval should pass all configured scenarios.
- Real-corpus eval should pass all configured scenarios.
- Direct CLI output should write the same reviewable artifact bundle as eval.

## Artifact bundle to inspect

Every reviewable run should include:

- `retrieval_plan.json`
- `gap_records.json`
- `ingestion_report.json`
- `ledger_entries.json`
- `approved_ledger.json`
- `web_fetch_records.json`
- `final_answer.txt`
- `pinpoint_evidence.json`
- `answer_alignment.json`
- `blind_validation_report.json`
- `manual_review.json`
- `manual_review_report.md`
- `verdict.json` for eval runs
- `provisional_grouping.json` for grouping-capable runs
- `corpus_coverage_report.json` for corpus-backed runs

For the real-question pack, the top-level run directory additionally includes:

- `pack_run_manifest.json`

Scenario D closeout runs additionally include:

- `spawned_validator_request.json`
- `spawned_validator_result.json`

## Highest-value things to verify manually

- No blocked claim appears in `final_answer.txt`.
- Mixed-support answers keep `confirmed`, `interpretive`, and `open` visible.
- `retrieval_plan.json` shows the expected EU-first or standards-first traversal.
- `gap_records.json` explains unresolved claims and any `official_web_search` trigger.
- `gap_records.json` preserves any discovery/fetch URLs used during official web expansion.
- `web_fetch_records.json` only contains allowlisted URLs, and rejected web sources stay out of the approved ledger.
- `manual_review.json` is clearly marked as an automated prefill, not mistaken for human review.
- `manual_review_report.md` is present and gives a usable human-readable review summary.
- `pinpoint_evidence.json` maps each cited answer claim to a concrete local locator and is explicit when only approximate traceability is available.
- `answer_alignment.json` shows no blocking wording-to-evidence alignment violations.
- `blind_validation_report.json` passes and records that the run should be reusable without raw-document reconstruction.
- For Scenario D closeout, `blind_validation_report.json` should show `validation_mode="structural_plus_spawned_validator_closeout"` and a nested `spawned_validator` result with `context_inherited=false`.
- Any approved fetched web source is surfaced in `manual_review_report.md` with digest and provenance evidence.
- `ledger_entries.json` shows weak anchors as `document_only`.
- Any `document_only` `confirmed` claim carries a credible technical anchor audit note.
- Lower-precedence material does not displace higher-precedence governing support.
- `provisional_grouping.json` stays provisional and source-bound.
- `corpus_coverage_report.json` passes and shows admitted coverage for the required source families on real-corpus runs.

## Good review samples

Suggested fixture sample:

- `artifacts/eval_runs/scenario_c_protocol_authorization_server`

Suggested real-corpus sample:

- `artifacts/eval_runs_real_corpus/scenario_b_registration_certificate_mandatory`

Suggested closeout sample:

- `artifacts/scenario_d_closeout/scenario_d_certificate_topology_anchor`

The V2 release gate treats the real-corpus `primary_success_scenario` and `scenario_b_registration_certificate_mandatory` bundles as binding review samples; their `manual_review_report.md` should end in `accept`.
Scenario D is the maintained closeout proof case; run its separate harness when a fresh no-context validator proof is needed without destabilizing the deterministic eval gate.

If the real-corpus eval directory is regenerated under a different output path, inspect the latest scenario directory with the same scenario id.
For the real-question pack, use `pack_run_manifest.json` to see which question bundles were produced and which review-signal verdicts changed, without treating the pack as a benchmark percentage gate.

## Current V2 boundary

The review should explicitly note these accepted limits:

- web expansion is allowlist-only and bounded to configured official domains
- official discovery is a bounded crawl from configured official entrypoints, with path/document admission controls rather than hostname-only admission
- fetched html/xhtml/xml/pdf content is normalized when possible; malformed fetched documents remain explicit failures rather than silent fallbacks
- real-corpus acceptance means reviewable, uncertainty-aware outputs, not identical answers to the fixture corpus

## Suggested PR summary structure

- Scope: Option A V2 research version with real-corpus-default operation and unified review artifacts
- Core implementation: ingestion, retrieval planning, official discovery, gap handling, source-role controller, answer composition, grouping artifact, eval runner
- Verification: test suite, fixture eval gate, real-corpus eval gate, manual review artifacts
- Known limits: the explicit V2 boundaries from `HARDENING_NOTES.md`
