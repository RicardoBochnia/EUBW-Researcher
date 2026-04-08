# EUBW-Researcher

Inspectable Python research prototype for the Option A evidence-first pipeline.

## Local commands

- Programmatic agent use should use the facade contract exported from `eubw_researcher` (`ResearchRuntimeFacade`, `AgentRuntimeRequest`, `AgentRuntimeResponse`, `AgentRuntimeResult`, `AgentRuntimeMode`); see `docs/architecture/options/option-a/RUNTIME_FACADE_CONTRACT.md`.
- Run the unit test suite used by the default pull-request CI path: `python3 scripts/run_unit_tests.py`
- Run the integration-heavy pipeline/eval suite used by conditional pull-request CI jobs: `python3 scripts/run_integration_tests.py`
- Run the full local test suite, including Scenario D closeout coverage: `python3 scripts/run_tests.py`
- Run only the separate Scenario D closeout harness tests: `python3 scripts/run_closeout_tests.py`
- Ingest the sample curated corpus: `python3 scripts/ingest_sample_corpus.py`
- Build the internal catalog for the local real corpus archive: `python3 scripts/build_real_corpus_catalog.py`
- Check the configured real-corpus archive against the stored canonical source URLs and stage changed candidates: `python3 scripts/refresh_real_corpus.py`
- Apply staged refresh candidates into the accepted local archive and update archive-catalog metadata: `python3 scripts/refresh_real_corpus.py --apply`
- Ingest the generated real corpus catalog: `python3 scripts/ingest_sample_corpus.py --catalog artifacts/real_corpus/curated_catalog.json`
- Ask a question against the generated real corpus catalog: `python3 scripts/answer_question.py "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"`
- Ask the primary V2 Business Wallet research question and write review artifacts: `python3 scripts/answer_question.py "What requirements apply to the Business Wallet, and how can they be provisionally structured?" --catalog artifacts/real_corpus/curated_catalog.json --output-dir artifacts/review_demo_primary`
- Ask an EBW registration-information question against the real corpus catalog: `python3 scripts/answer_question.py "What information must a wallet-relying party provide during relying party registration?" --catalog artifacts/real_corpus/curated_catalog.json`
- Ask an EBW certificate-requirements question against the real corpus catalog: `python3 scripts/answer_question.py "What is the difference between a wallet-relying party registration certificate and a wallet-relying party access certificate?" --catalog artifacts/real_corpus/curated_catalog.json`
- Run the curated real-question manual-review pack: `python3 scripts/run_real_question_pack.py --all`
- Run one curated real-question pack item: `python3 scripts/run_real_question_pack.py --question-id scenario_d_certificate_topology_anchor`
- Run the Scenario C thin-slice evaluation: `python3 scripts/run_eval.py --scenario scenario_c_protocol_authorization_server`
- Run the full configured evaluation set: `python3 scripts/run_eval.py --all`
- Run eval against a non-fixture catalog: `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Run the real-corpus review gate: `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Generate the validated current-state report from the real-corpus eval gate: `python3 scripts/report_validated_current_state.py`
- Generate the validated current-state report with optional spawned-validator evidence: `python3 scripts/report_validated_current_state.py --spawned-validator-manifest artifacts/spawned_validator_gate_runs/spawned_validator_gate_manifest.json`
- Run the optional spawned-validator gate for one configured high-risk scenario: `python3 scripts/run_spawned_validator_gate.py --scenario high_risk_failure_pattern --catalog artifacts/real_corpus/curated_catalog.json --validator-command "<validator command>"`
- Run the optional spawned-validator release gate subset: `python3 scripts/run_spawned_validator_gate.py --release-gate --catalog artifacts/real_corpus/curated_catalog.json --validator-command "<validator command>"`
- Add a real-question-pack manifest as supplemental evidence for that report: `python3 scripts/report_validated_current_state.py --real-question-pack-manifest artifacts/real_question_pack_runs/<run-id>/pack_run_manifest.json`
- Run the separate Scenario D closeout harness with a spawned validator: `python3 scripts/run_scenario_d_closeout.py --catalog artifacts/real_corpus/curated_catalog.json --validator-command "<validator command>"`

Validator contract for the closeout harness:
- the harness invokes the validator as `<validator command> --input <request.json> --output <result.json>`
- the validator must write JSON including `passed`, `context_inherited`, `artifacts_used`, `raw_document_dependency`, `product_output_self_sufficient`, `summary`, and `validator_answer`

## Notes

- The repository is V2-backend-only by design: no UI, no persistent provenance graph, and no multi-agent orchestration.
- Pull-request CI now uses a cheap routing step on every PR, pins Python 3.12 for that routing step, runs the unit suite only when runtime-relevant files changed, lets the heavier integration and closeout suites proceed only after unit tests pass, and reserves `python3 scripts/run_tests.py` for every push to `main`, scheduled validation, or manual dispatch.
- Real-corpus refresh is user-triggered: `scripts/refresh_real_corpus.py` checks configured archive entries against their stored canonical source URLs, stages changed candidates under `artifacts/real_corpus/refresh_staging`, and only updates the accepted archive when run with `--apply`.
- Refresh governance decision: refresh is intentionally not governed by the open-web discovery allowlist. Discovery stays allowlist-only and path-gated for finding new sources; refresh is limited to already accepted corpus entries and may only re-check the exact stored `canonical_url` for those entries. No discovery, link-following, alternate-source search, or silent source replacement is allowed in the refresh workflow.
- Config files under `configs/` use YAML-compatible JSON so no separate YAML parser dependency is required; PDF extraction uses `pypdf`.
- Manual artifact review guidance lives in `docs/architecture/options/option-a/MANUAL_REVIEW_CHECKLIST.md`.
- A compact reviewer entrypoint lives in `docs/architecture/options/option-a/REVIEW_GUIDE.md`.
- Known V2 residual limits and their mitigation/acceptance are recorded in `docs/architecture/options/option-a/HARDENING_NOTES.md`.
- Default eval outputs are split by corpus: `artifacts/eval_runs` for fixtures and `artifacts/eval_runs_real_corpus` for the real archive catalog.
- Top-level eval output directories now include `eval_run_manifest.json`; for real-corpus eval they also include top-level `corpus_coverage_report.json` and `corpus_coverage_summary.md` as the compact validated-gate surface.
- `eval_run_manifest.json` is only authoritative when produced by `python3 scripts/run_eval.py --all`; single-scenario eval runs do not write or preserve the top-level authoritative manifest/coverage artifacts in the target output directory.
- `scripts/report_validated_current_state.py` writes a compact validated-state bundle under `artifacts/current_state`, including `validated_current_state_report.json` and `validated_current_state_report.md`; it consumes the real-corpus `eval_run_manifest.json` from `run_eval.py --all`, and real-question-pack evidence is supplemental only when passed explicitly with `--real-question-pack-manifest`.
- `scripts/run_spawned_validator_gate.py` writes optional validator-gated scenario bundles plus `spawned_validator_gate_manifest.json`; this is separate from the deterministic eval gate and is intended for configured high-risk scenarios or the configured release-gate subset.
- `scripts/report_validated_current_state.py` can record a spawned-validator manifest as supplemental evidence, or treat it as binding only when explicitly asked with `--promote-spawned-validator-gate`.
- Reviewable bundles include `retrieval_plan.json`, `gap_records.json`, `ingestion_report.json`, `ledger_entries.json`, `approved_ledger.json`, `web_fetch_records.json`, `final_answer.txt`, `manual_review.json`, `manual_review_report.md`, `pinpoint_evidence.json`, `answer_alignment.json`, and `blind_validation_report.json`; grouping-capable runs additionally emit `provisional_grouping.json`.
- Corpus-backed bundles additionally emit `corpus_coverage_report.json`, and the real-corpus ingestion bundle is cached under `artifacts/real_corpus/cache/` so repeated review runs do not re-normalize the full archive.
- `manual_review.json` is an automated prefill artifact; `manual_review_report.md` is the primary human-readable review surface.
- The real-question pack `pack_run_manifest.json` captures baseline git attribution before in-repo output creation, whether the run wrote repo-local artifacts, and compact reviewer-oriented per-question triage fields.
- The real-question pack writes one standard reviewable bundle per configured question under `artifacts/real_question_pack_runs/<run-id>/...` plus a top-level `pack_run_manifest.json` with run attribution and compact review signals; it is a regression-review surface, not a benchmark scorecard.
- `pinpoint_evidence.json` maps answer claims to reviewer-usable local source locators and records any precision limits explicitly.
- `answer_alignment.json` records the structural answer-to-evidence alignment check used by the V2.2 topology gate.
- `blind_validation_report.json` records the product-output-first self-sufficiency gate for whether the generated artifacts should be reusable without raw-document reconstruction.
- Scenario D closeout runs additionally persist `spawned_validator_request.json` and `spawned_validator_result.json`; these are review-harness artifacts, not part of the normal deterministic eval gate.
- Optional spawned-validator gate runs also persist `spawned_validator_request.json` and `spawned_validator_result.json` per gated scenario, plus a top-level `spawned_validator_gate_manifest.json` describing which scenarios were gated and whether the validator changed the final outcome.
- The binding real-corpus review samples are `primary_success_scenario` and `scenario_b_registration_certificate_mandatory`; their `manual_review_report.md` must end in `accept`.
- `scenario_d_certificate_topology_anchor` is the maintained Option A closeout proof case; use the separate closeout harness rather than the normal eval gate when a fresh no-context validator proof is required.
- Approved fetched web sources are surfaced in `manual_review_report.md` with digest and provenance evidence for reviewability.
- The local real corpus archive now lives under `artifacts/real_corpus/archive` and is intentionally excluded from git.
- `configs/real_corpus_selection.yaml` is the inspectable bridge from the local source archive into the internal Option A source catalog.
- If another agent is working in parallel, prefer a dedicated Git worktree before making repo changes, for example: `git worktree add -b codex/<topic> ../<repo>-<topic> HEAD`
- Official discovery remains allowlist-only, path-gated, and bounded to configured entrypoints plus one-hop crawl defaults from `configs/web_allowlist.yaml` and `configs/runtime.yaml`.
