# Option A V2 Plan Delta Review

Reviewer: v2-reviewer-4
Date: 2026-04-01
Review target: [V2_PLAN.md](../V2_PLAN.md)
Scope: corpus and discovery governance delta only

## 1. Prior blocker status

- **Document admission rules:** substantially resolved. The revised plan now says allowlisted domain match is not sufficient and adds a concrete fetched-document admission contract with required metadata, normalization status, and provenance before evidence admission.
- **Official discovery bounds:** resolved. The revised plan now makes discovery one-hop, cap-bounded, timeout-bounded, same-domain or explicitly canonical-cross-domain only, and config-driven rather than implicit.
- **Corpus coverage gate:** resolved. The revised plan now requires catalog-level admitted coverage across the required source families and an inspectable `corpus_coverage_report.json`.

## 2. New findings

- **Remaining material gap: inspectability of approved fetched-source governance is still slightly under-specified at review time.** The plan now requires a content digest or stable archived snapshot reference for admitted fetched documents, which is a real improvement. But it still does not explicitly require the review bundle to carry, or clearly point to, the per-source digest/snapshot evidence in a reviewer-facing artifact. That leaves some room for implementation to satisfy admission structurally while keeping approval-time inspection weaker than it should be.

## 3. Short verdict

Most of the earlier corpus/discovery concerns are now closed. One small but still material reviewability gap remains around how approved fetched-source capture evidence is exposed to reviewers.

`ready with revisions`
