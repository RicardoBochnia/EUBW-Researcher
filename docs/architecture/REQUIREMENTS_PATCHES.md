# Requirements Patches

Status: no formal patches raised after external review wave
Purpose: handle real requirements contradictions or decision-critical gaps discovered during architecture drafting

## 1. Scope

This document is exception handling, not a second requirements process.

Use it only when a variant exposes one of the following:
- a real contradiction in the frozen requirements basis
- a real build blocker for one or more architecture options
- a missing, decision-critical requirement that prevents defensible option design

Do not use it for:
- opportunistic scope expansion
- architecture preference
- non-blocking detail gaps
- stylistic disagreement with the requirements text

## 2. Lifecycle

Patch statuses:
- `raised`
- `triaged`
- `accepted`
- `rejected`
- `carried_as_open_assumption`
- `implemented`

A patch is considered decided only if one of these happens:
- the requirements basis is corrected and the change is recorded
- the patch is explicitly rejected
- the affected option is explicitly allowed to carry the issue as an open assumption, and this assumption is visible in the option PLAN and later REVIEW

If a real blocker remains undecided, the affected option must not freeze for review.

## 3. Patch template

Use one row per patch.

| Patch ID | Status | Triggering option(s) | Type | Requirement area | Problem statement | Why this is a blocker | Proposed handling | Decision | Impact on affected PLANs | Owner | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 4. Current patch log

No requirements patches have been raised during the initial option-scoping and plan-drafting pass.

## 5. Decision notes

Use this section only for short explanatory notes that do not fit into the table.

- Initial handoff state: no blocker-level requirements contradictions were found while drafting the first 3+1 option set.
- External review wave outcome: no formal requirements patch was opened.
- One reviewer noted a possible clarification around internal-process inspectability. This was treated as a non-blocking architecture-comparison note rather than a formal requirements defect because the frozen basis already requires visible hierarchy, contradiction, uncertainty, and source-role preservation in the answer behavior.
