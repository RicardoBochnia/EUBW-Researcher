# Option A Implementation Plan Review

Status: completed revised review
Review target: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## 1. Required inputs

- [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [./PLAN.md](./PLAN.md)
- [./REVIEW.md](./REVIEW.md)
- [../../OPTIONS_COMPARISON.md](../../OPTIONS_COMPARISON.md)
- [./IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## 2. Review goal

Assess whether the implementation plan is concrete enough, disciplined enough, and narrow enough to start coding without silently reopening architecture or scope.

## 3. Findings

List findings first, ordered by severity.

### P1 / blocker
- No blocker identified in the revised plan. The previous blocker-level gaps around claim-state rules, retrieval-gap and web-trigger rules, anchor degradation handling, and evaluation artifacts are now materially addressed.

### P2 / important risk
- The final answer contract is still slightly inconsistent with the new claim-state model. Section 5 makes `confirmed`, `interpretive`, `open`, and `blocked` central control states, but Phase 5 still describes the distinction between confirmed, interpretive, and open points as optional in rendering. If mixed-support answers can be rendered without visibly carrying those distinctions, the final step can still flatten uncertainty and source-role meaning.
- The retrieval-gap contract is much stronger now, but two implementation-shaping details are still open: how many "top local candidates" must be inspected before a layer is treated as exhausted, and whether same-rank official web sources must be preferred before lower-rank web material when a high-rank gap remains. Those details can change whether a claim ends as confirmed, interpretive, open, or blocked.
- The document-only `confirmed` exception is practical but risky. The plan now allows confirmation when the governing source is clear and the missing anchor is judged to be a technical extraction failure, but it still does not define the repeatable heuristic or review test that distinguishes technical extraction failure from a real epistemic gap.

### P3 / improvement
- Turn the remaining open control details into visible config or fixture rules before Phase 2 or 3 merges: candidate-inspection depth, same-rank-before-lower-rank web escalation, and the audit cases for document-only `confirmed` claims.

## 4. Summary verdict

- Overall verdict: `ready with revisions`
- Short rationale: The revised plan is now concrete enough to start coding and stays disciplined within the selected Option A architecture. The remaining issues are no longer blocker-level; they are tightening steps around final-state rendering visibility, retrieval exhaustion semantics, and the auditability of document-only confirmation.

## 5. What the plan gets right

- It directly addresses the main issues from the first review by adding explicit operational contracts for claim states, gap records, web triggering, anchor degradation, and evaluation artifacts.
- It stays inside the selected Option A architecture and does not drift toward graph-first, multi-specialist, or UI-heavy scope.
- It strengthens inspectability in the right places: visible configs, visible decision tables, visible gap records, visible scenario artifacts, and a testable controller contract.
- It improves build sequencing by adding a second thin slice that explicitly exercises a regulation-heavy or missed-governing-source case before broadening out.

## 6. Missing implementation decisions

- Decide whether mixed-state answers must visibly label `confirmed`, `interpretive`, and `open` blocks, or define an equally explicit alternative rendering rule that still preserves uncertainty and source role in the final answer.
- Fix the inspection-depth rule for "top local candidates" so retrieval exhaustion is reproducible and not left to implementation drift.
- Decide whether official same-rank web sources must be preferred before lower-rank web material whenever a high-rank gap remains.
- Define the test heuristic for when document-only support counts as a technical extraction failure rather than an epistemic insufficiency.

## 7. Scope or architecture drift risks

- If claim-state visibility remains optional in the final answer, the implementation can drift back toward smoother prose that hides support quality differences.
- If candidate-inspection depth and web escalation order live mainly in code or prompt behavior rather than config and fixtures, the plan will lose some of Option A's inspectable-control advantage.
- If document-only `confirmed` cases are not tightly audited, the technical-exception path can slowly widen into a loophole for overconfident answers.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | Meets with caveat | The hierarchy is now clearly intended as visible config plus decision rules, but same-rank EU-source ordering still needs one more operational rule. |
| Web allowlist is explicit | Meets with caveat | The allowlist and metadata contract are explicit, but the escalation order between same-rank and lower-rank web sources should be fixed. |
| Unsupported-claim blocking is explicit | Meets with caveat | The claim-state decision model is now explicit, but final rendering still needs to preserve those states visibly enough. |
| Retrieval-miss failure is explicitly tested | Meets with caveat | The plan now includes a negative fixture and stored artifacts, but the layer-exhaustion threshold still needs a concrete inspection-depth rule. |
| Anchor weakness has a fallback path | Meets with caveat | The degradation path is now specified, but the document-only `confirmed` exception still needs repeatable tests. |
| V1 non-goals are protected | Meets | No material concern. |

## 9. Gate recommendation

- Can coding start after this review? `yes`
- If no, what must change first? `n/a`
