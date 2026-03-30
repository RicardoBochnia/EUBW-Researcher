# Option A Implementation Plan Review

Status: finalized after implementation-plan review wave 2
Review target: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## 1. Reviewed inputs

- [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [./PLAN.md](./PLAN.md)
- [./REVIEW.md](./REVIEW.md)
- [../../OPTIONS_COMPARISON.md](../../OPTIONS_COMPARISON.md)
- [./IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
- Raw reviews:
  - [./reviews/reviewer-1.md](./reviews/reviewer-1.md)
  - [./reviews/reviewer-2.md](./reviews/reviewer-2.md)
  - [./reviews/reviewer-3.md](./reviews/reviewer-3.md)
  - [./reviews/reviewer-4.md](./reviews/reviewer-4.md)

## 2. Findings

### P1 / blocker

- No blocker remains after the revised-plan review pass. The previously load-bearing gaps around claim-state handling, retrieval-gap/web-trigger behavior, and anchor degradation are now explicitly specified in the implementation plan.

### P2 / important risk

- The remaining risks are now implementation-time calibration risks rather than design-level gaps:
  - keep tie-break logic structurally simple and inspectable
  - keep retrieval exhaustion practical by allowing parallel lexical/semantic execution and a configurable inspection depth
  - keep document-only `confirmed` cases tightly audited so the technical-exception path does not widen into a loophole
  - keep answer rendering visibly aligned with the claim-state model

### P3 / improvement

- Reviewers still preferred a few implementation-time tightening steps:
  - expose per-source source-role level clearly in Phase 1 reporting
  - make slice exit criteria explicit
  - keep the remaining tuning knobs visible in config or fixtures rather than implicit in code

## 3. Consolidated verdict

- Overall verdict before revision: `ready with revisions`, with one reviewer calling it `not ready` until the controller and gap-detection contracts were fixed.
- Overall verdict after wave 2: `ready`
- Short rationale: the updated reviews no longer identify blocker-level gaps. The remaining points concern tuning, inspectability, and calibration of already-explicit contracts, not missing architectural or implementation-defining decisions.

## 4. What changed across the two review waves

The implementation plan now explicitly includes:
- a claim-state and answer contract with `confirmed`, `interpretive`, `open`, and `blocked`
- a concrete retrieval-gap and web-expansion contract
- an anchor-degradation contract
- a minimum metadata contract for normalized web sources
- stored per-scenario artifacts for later diagnosis
- an early second slice that exercises a regulation-heavy or missed-governing-source case, not only Scenario C
- structural rather than semantic-first tie-break guidance
- explicit parallel-capable retrieval exhaustion defaults and a default candidate-inspection depth
- explicit answer-state visibility and slice exit criteria

## 5. Remaining watchpoints

- The contracts are now specific enough to code, but they still need implementation-time proof through fixtures and evaluation artifacts.
- The most important watchpoints during coding are:
  - tie-break simplicity and inspectability
  - practical retrieval latency under the exhaustion rules
  - disciplined handling of document-only `confirmed` cases
  - preserving claim-state visibility in final answer rendering

## 6. Gate recommendation

- Architecture reopening required? `no`
- Can implementation start? `yes`
- Recommended start condition: begin with Phase 0 and Phase 1, then follow the two-slice order in the finalized plan before broadening scope
