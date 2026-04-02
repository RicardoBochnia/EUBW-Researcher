# EUBW-Researcher

Inspectable Python research prototype for the Option A evidence-first pipeline.

## Local commands

- Programmatic agent use should use the facade contract exported from `eubw_researcher` (`ResearchRuntimeFacade`, `AgentRuntimeRequest`, `AgentRuntimeResponse`, `AgentRuntimeMode`); see `docs/architecture/options/option-a/RUNTIME_FACADE_CONTRACT.md`.
- Run the full local test suite, including Scenario D closeout coverage: `python3 scripts/run_tests.py`
- Run only the separate Scenario D closeout harness tests: `python3 scripts/run_closeout_tests.py`
- Ingest the sample curated corpus: `python3 scripts/ingest_sample_corpus.py`
- Build the internal catalog for the local real corpus archive: `python3 scripts/build_real_corpus_catalog.py`
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
- Run the separate Scenario D closeout harness with a spawned validator: `python3 scripts/run_scenario_d_closeout.py --catalog artifacts/real_corpus/curated_catalog.json --validator-command "<validator command>"`

Validator contract for the closeout harness:
- the harness invokes the validator as `<validator command> --input <request.json> --output <result.json>`
- the validator must write JSON including `passed`, `context_inherited`, `artifacts_used`, `raw_document_dependency`, `product_output_self_sufficient`, `summary`, and `validator_answer`

## Notes

- The repository is V2-backend-only by design: no UI, no persistent provenance graph, and no multi-agent orchestration.
- Config files under `configs/` use YAML-compatible JSON so no separate YAML parser dependency is required; PDF extraction uses `pypdf`.
- Manual artifact review guidance lives in `docs/architecture/options/option-a/MANUAL_REVIEW_CHECKLIST.md`.
- A compact reviewer entrypoint lives in `docs/architecture/options/option-a/REVIEW_GUIDE.md`.
- Known V2 residual limits and their mitigation/acceptance are recorded in `docs/architecture/options/option-a/HARDENING_NOTES.md`.
- Default eval outputs are split by corpus: `artifacts/eval_runs` for fixtures and `artifacts/eval_runs_real_corpus` for the real archive catalog.
- Reviewable bundles include `retrieval_plan.json`, `gap_records.json`, `ingestion_report.json`, `ledger_entries.json`, `approved_ledger.json`, `web_fetch_records.json`, `final_answer.txt`, `manual_review.json`, `manual_review_report.md`, `pinpoint_evidence.json`, `answer_alignment.json`, and `blind_validation_report.json`; grouping-capable runs additionally emit `provisional_grouping.json`.
- Corpus-backed bundles additionally emit `corpus_coverage_report.json`, and the real-corpus ingestion bundle is cached under `artifacts/real_corpus/cache/` so repeated review runs do not re-normalize the full archive.
- `manual_review.json` is an automated prefill artifact; `manual_review_report.md` is the primary human-readable review surface.
- The real-question pack writes one standard reviewable bundle per configured question under `artifacts/real_question_pack_runs/<run-id>/...` plus a top-level `pack_run_manifest.json` with run attribution and compact review signals; it is a regression-review surface, not a benchmark scorecard.
- `pinpoint_evidence.json` maps answer claims to reviewer-usable local source locators and records any precision limits explicitly.
- `answer_alignment.json` records the structural answer-to-evidence alignment check used by the V2.2 topology gate.
- `blind_validation_report.json` records the product-output-first self-sufficiency gate for whether the generated artifacts should be reusable without raw-document reconstruction.
- Scenario D closeout runs additionally persist `spawned_validator_request.json` and `spawned_validator_result.json`; these are review-harness artifacts, not part of the normal deterministic eval gate.
- The binding real-corpus review samples are `primary_success_scenario` and `scenario_b_registration_certificate_mandatory`; their `manual_review_report.md` must end in `accept`.
- `scenario_d_certificate_topology_anchor` is the maintained Option A closeout proof case; use the separate closeout harness rather than the normal eval gate when a fresh no-context validator proof is required.
- Approved fetched web sources are surfaced in `manual_review_report.md` with digest and provenance evidence for reviewability.
- The local real corpus archive now lives under `artifacts/real_corpus/archive` and is intentionally excluded from git.
- `configs/real_corpus_selection.yaml` is the inspectable bridge from the local source archive into the internal Option A source catalog.
- If another agent is working in parallel, prefer a dedicated Git worktree before making repo changes, for example: `git worktree add -b codex/<topic> ../<repo>-<topic> HEAD`
- Official discovery remains allowlist-only, path-gated, and bounded to configured entrypoints plus one-hop crawl defaults from `configs/web_allowlist.yaml` and `configs/runtime.yaml`.
