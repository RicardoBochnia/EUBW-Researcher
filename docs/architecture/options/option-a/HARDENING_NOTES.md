# Option A Hardening Notes

This note records the remaining deliberate V2 boundaries after the completed hardening pass.

## Phase 3: Web expansion

- V2 web expansion is allowlist-only and bounded to official domains configured in `configs/web_allowlist.yaml`.
- Implemented behavior: web expansion requires a stored gap record, prefers same-rank official web kinds before lower-rank kinds, and preserves discovery/fetch traces in both `gap_records.json` and `web_fetch_records.json`.
- Implemented behavior: official discovery uses exact-host-only domain policies. There is no wildcard, suffix, or parent-domain inheritance between hosts such as `eudi.dev` and `docs.eudi.dev`, or between `ec.europa.eu` and `commission.europa.eu`.
- Implemented behavior: discovery configuration is structured through `discovery_entrypoints` with an explicit `entrypoint_id`, `url_template`, and `strategy`. Legacy `discovery_urls` remain loader-migrated for backward compatibility.
- Implemented behavior: discovery and admission are separated. `crawl_path_prefixes` bound what discovery may follow, while `admission_path_prefixes` bound what fetched content may enter the approved-evidence path.
- Implemented behavior: official discovery now performs a depth-limited crawl from configured official entrypoints and only follows links that satisfy the exact-host policy, path-prefix controls, blocked-keyword filters, and same-rank/layer discipline.
- Implemented behavior: `official_search` is intentionally narrow. The current search-backed path is the EUR-Lex quick-search HTML endpoint only, and discovered follow-ups may cross into explicitly approved legal hosts such as `publications.europa.eu`.
- Implemented behavior: fetched document admission is stricter than hostname allowlisting alone. Successful normalization is necessary but not sufficient; admitted fetched evidence must also satisfy the configured path/document-class policy and carry the full stored metadata contract.
- Implemented behavior: fetched `html`, `xhtml`, `xml`, and `pdf` sources are normalized into the normal ingestion path; malformed fetched documents stay explicit as normalization failures and do not enter the approved ledger.
- Implemented behavior: discovery defaults are config-driven and conservative: one-hop depth, per-domain admitted-fetch cap, and per-run admitted-fetch cap.
- Implemented behavior: GitHub Pages may be admitted as an explicit exact host such as `eu-digital-identity-wallet.github.io`, but this does not relax the exclusion of `raw.githubusercontent.com`, `api.github.com`, or generic raw GitHub content.
- Deliberate V2 boundary: no arbitrary-site search, no third-party search engines, and no crawling outside the configured exact-host allowlist.

## Local and fetched normalization

- Local archive ingestion and official web ingestion both support markdown/text, html/xhtml, xml, and pdf inputs.
- Implemented behavior: normalization failures stay explicit in `ingestion_report.json` for admitted sources and in `web_fetch_records.json` for rejected fetched sources.
- Implemented behavior: the real-corpus review path reuses a cached normalized ingestion bundle under `artifacts/real_corpus/cache/` and records a stable `corpus_state_id` for review reproducibility.
- Deliberate V2 boundary: PDF extraction is text-first and citation-first rather than layout-faithful.

## Phase 4: Hierarchy and anchor degradation

- Claim resolution uses both source-role level and configured source-kind rank.
- Implemented behavior: lower-precedence high-rank sources do not reopen or displace higher-precedence governing sources unless they are truly same-rank under the configured hierarchy.
- Implemented behavior: weak anchors degrade to `document_only` and are not treated as technical extraction failures.
- Implemented behavior: only missing anchors with retrievable governing content can reach the audited document-only `confirmed` path, and the audit note is persisted into ledger artifacts.

## Phase 6: Evaluation gate

- Fixture and real-corpus validation use the same scenario ids, the same artifact bundle shape, and the same review vocabulary, while allowing corpus-specific expectations where the governing source set differs.
- Implemented behavior: both suites run through `scripts/run_eval.py`, every reviewable bundle includes `manual_review.json` and `manual_review_report.md`, and grouping-capable paths emit `provisional_grouping.json`.
- Implemented behavior: corpus-backed runs additionally emit `corpus_coverage_report.json` and fail the gate when required source-family coverage is not admitted.
- Implemented behavior: `manual_review.json` is explicitly stored as an automated review prefill (`artifact_type="automated_review_prefill"`, `human_reviewed=false`) so it is not mistaken for completed human review.
- Implemented behavior: the binding real-corpus review samples require `manual_review_report.md` to end in `accept`, and the report surfaces digest, provenance, `policy_id`, `entrypoint_id`, `discovery_strategy`, `admission_rule`, and `discovery_query` for any approved fetched web source.
- Implemented behavior: evaluation scenarios can now gate separately on discovery-page records, discovered-link records, fetched-document records, and required observed web domains.
- Implemented behavior: Scenario D closeout now uses a separate harness (`scripts/run_scenario_d_closeout.py`) that keeps the normal eval gate deterministic while recording a spawned-validator proof in the closeout bundle.
- Implemented behavior: Scenario D closeout records both `spawned_validator_request.json` and `spawned_validator_result.json`, and folds the spawned-validator judgment into `blind_validation_report.json` under a nested `spawned_validator` block.
- Implemented behavior: configured high-risk scenarios can now run through the generic optional spawned-validator gate (`scripts/run_spawned_validator_gate.py`), which writes per-scenario sidecars plus a top-level `spawned_validator_gate_manifest.json`.
- Implemented behavior: validated-current-state reporting can record spawned-validator gate evidence as supplemental by default and can only make it binding when explicitly asked via `--promote-spawned-validator-gate`.
- Implemented behavior: validator subprocess failure, timeout, invalid output, inherited context, or `central_reconstruction` all fail the closeout harness without changing the ordinary eval gate contract.
- Accepted limitation: the spawned validator's raw-document reads are currently self-reported by the validator output contract; the harness validates the report shape and failure conditions but does not independently sandbox-check every file read.
- Deliberate V2 boundary: real-corpus review readiness means reviewable, uncertainty-aware, source-bound output on the real corpus, not exact textual parity with the fixture corpus.

## PR closeout discipline

- Implemented workflow expectation: discovery/governance changes should go through multiple self-review rounds before PR creation, covering schema/API migration, governance boundaries, and reviewer-surface completeness.
- Implemented workflow expectation: the expected pre-PR verification remains `python3 scripts/run_tests.py` and `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`.
- Implemented workflow expectation: Copilot feedback should be reduced to confirmation or minor follow-ups; the main bug-finding pass should happen in the explicit self-review rounds, not after PR creation.
