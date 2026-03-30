# Option A Implementation Plan Review

Status: consolidated from implementation-plan review wave 1
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

- Reviewers converged on one load-bearing issue: before core-path coding starts, the implementation plan must operationalize the controller and retrieval contracts that protect the non-negotiable support-fidelity requirement.

### P2 / important risk

- The most repeated risks were:
  - web-expansion trigger and stop conditions were too abstract
  - block-versus-downgrade behavior for claims was too abstract
  - anchor-failure fallback was named but not defined
  - the first thin vertical slice was too narrow if it only exercised Scenario C

### P3 / improvement

- Reviewers asked for clearer scenario artifacts and stronger traceability of failures to retrieval, normalization, controller logic, or answer composition.
- Reviewers also asked for the web-source metadata contract and module boundaries to become a little more explicit before coding begins.

## 3. Consolidated verdict

- Overall verdict before revision: `ready with revisions`, with one reviewer calling it `not ready` until the controller and gap-detection contracts were fixed.
- Overall verdict after revision: `ready for one more focused review pass`
- Short rationale: the architecture choice itself was not reopened, and no blocker challenged Option A as the selected direction. The review wave instead identified four concrete implementation contracts that needed to be made operational before coding could safely begin.

## 4. What changed in the revised plan

The implementation plan now explicitly includes:
- a claim-state and answer contract with `confirmed`, `interpretive`, `open`, and `blocked`
- a concrete retrieval-gap and web-expansion contract
- an anchor-degradation contract
- a minimum metadata contract for normalized web sources
- stored per-scenario artifacts for later diagnosis
- an early second slice that exercises a regulation-heavy or missed-governing-source case, not only Scenario C

## 5. Remaining watchpoints

- The revised contracts are now explicit, but they are still plan-level contracts and need implementation-time proof.
- The next review should focus on whether these contracts are specific enough to code without hidden reinterpretation.
- If a next reviewer still finds the controller or gap-detection contract too ambiguous, do not start Phase 2+ coding yet.

## 6. Gate recommendation

- Architecture reopening required? `no`
- Can Phase 0 and Phase 1 coding start? `yes`
- Can Phase 2+ coding start immediately? `only after the revised contracts are accepted in the next focused review pass`
