# Option A Hardening Notes

This note records the remaining deliberate V2 boundaries after the completed hardening pass.

## Phase 3: Web expansion

- V2 web expansion is allowlist-only and bounded to official domains configured in `configs/web_allowlist.yaml`.
- Implemented behavior: web expansion requires a stored gap record, prefers same-rank official web kinds before lower-rank kinds, and preserves discovery/fetch traces in both `gap_records.json` and `web_fetch_records.json`.
- Implemented behavior: official discovery now performs a depth-limited crawl from configured official entrypoints and only follows links that satisfy the domain policy, path-prefix admission, blocked-keyword filters, and same-rank/layer discipline.
- Implemented behavior: fetched document admission is stricter than hostname allowlisting alone. Successful normalization is necessary but not sufficient; admitted fetched evidence must also satisfy the configured path/document-class policy and carry the full stored metadata contract.
- Implemented behavior: fetched `html`, `xhtml`, `xml`, and `pdf` sources are normalized into the normal ingestion path; malformed fetched documents stay explicit as normalization failures and do not enter the approved ledger.
- Implemented behavior: discovery defaults are config-driven and conservative: one-hop depth, per-domain admitted-fetch cap, and per-run admitted-fetch cap.
- Deliberate V2 boundary: no arbitrary-site search and no crawling outside the configured allowlist.

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
- Implemented behavior: the binding real-corpus review samples require `manual_review_report.md` to end in `accept`, and the report surfaces digest/provenance evidence for any approved fetched web source.
- Deliberate V2 boundary: real-corpus review readiness means reviewable, uncertainty-aware, source-bound output on the real corpus, not exact textual parity with the fixture corpus.
