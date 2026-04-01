# Option A Manual Review Checklist

Use this checklist when reviewing the stored evaluation artifacts under `artifacts/eval_runs/` or `artifacts/eval_runs_real_corpus/`.

## Core checks

- Confirm that no unsupported core claim appears in `final_answer.txt`.
- Confirm that every rendered claim block has at least document-level citation support.
- Confirm that lower-rank or web/project material is not presented as binding EU regulation.
- Confirm that any mixed-support answer keeps `confirmed`, `interpretive`, and `open` distinctions visible.
- Confirm that `manual_review.json` is explicitly marked as an automated prefill, not a completed human review.
- Confirm that `manual_review_report.md` exists and is substantively filled enough to support human review.
- For the binding real-corpus review samples, confirm that `manual_review_report.md` ends in `accept`.

## Retrieval and gap checks

- Review `retrieval_plan.json` to verify EU-first ranked traversal for regulation-heavy questions.
- Review `gap_records.json` to confirm that unresolved or contradictory claims keep a traceable audit record.
- For any `official_web_search` action, confirm that the local ranked layers were exhausted first.
- For any unresolved contradiction, confirm that the gap reason explains why the point stayed unresolved.
- For any discovery-driven web expansion, confirm that `gap_records.json` carries the discovery and fetch URLs that were attempted.
- For any real-corpus review run, confirm that `corpus_coverage_report.json` passes and covers every required source family.

## Web expansion checks

- Review `web_fetch_records.json` to confirm that every fetched URL is allowlisted.
- Confirm that admitted fetched URLs satisfy the configured path/document-class constraints, not only the hostname allowlist.
- Confirm that each admitted web source has canonical URL, domain, source role, jurisdiction if known, retrieval timestamp, and citation quality.
- Confirm that `manual_review_report.md` surfaces digest/snapshot evidence and provenance for any approved fetched web source.
- Confirm that disallowed or metadata-incomplete web sources do not appear in the approved ledger.
- Confirm that malformed fetched documents remain explicit normalization failures instead of disappearing from the review artifacts.

## Anchor and citation checks

- Review `ledger_entries.json` to confirm weak anchors degrade to `document_only`.
- Confirm that any document-only `confirmed` claim has a credible technical-anchor audit note rather than an epistemic shortcut.
- Confirm that structure-poor sources render as full-document citations only.
- Review `ingestion_report.json` to confirm that local normalization failures remain explicit and do not silently disappear.
- Where fetched pdf/xml material was admitted, confirm that the corresponding ingestion-report entries carry the actual normalization format rather than a generic placeholder.

## Grouping checks

- If `provisional_grouping.json` is present, confirm that every grouping item remains explicitly provisional.
- Confirm that every grouping item is traceable back to claim ids and source ids.

## High-risk failure checks

- Look specifically for missed governing-source patterns: a plausible lower-rank explanation should not displace a retrieved higher-rank source.
- For contradiction cases, confirm that only same-rank admissible conflicts reopen a claim to `open`.
- Confirm that blocked claims remain in the stored ledger but do not surface in the final rendered answer.
