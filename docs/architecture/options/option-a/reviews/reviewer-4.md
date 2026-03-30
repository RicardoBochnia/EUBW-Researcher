# Option A Implementation Plan Review

Status: completed review
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
- The core safety mechanism is still not operationally specified enough to code or test. Phase 4 and Phase 5 say the controller will block unsupported core claims, downgrade weak ones, and preserve contradiction and uncertainty, but the plan never defines the claim-state model or the decision rules that separate `confirmed`, `interpretive`, `open`, `blocked`, and document-only cases. Because avoiding unsupported or wrongly supported core claims is the non-negotiable requirement and the main reason Option A was selected, this needs to be fixed before core-path coding starts.
- The retrieval-gap and web-expansion contract is still too abstract for implementation readiness. Phase 2 and Phase 3 require ranked traversal, explicit gap records, and defensive web fallback, but they do not define what evidence signals count as "under-supported," when high-rank local search is considered exhausted, or what concrete test proves the system caught a missed-governing-source case. That leaves the highest-available-source rule and the main residual Option A risk untestable.

### P2 / important risk
- The first thin vertical slice is pointed at Scenario C, which is narrower than the architecture's main V1 risk profile. Scenario C is useful for standards retrieval, but it does not pressure-test the cross-layer EU-first flow, the governing-source-miss failure mode, or the primary success scenario's provisional grouping. The first slice should include at least one cross-layer or failure-mode fixture, not Scenario C alone.
- Anchor fallback is named as a required control, but the degraded behavior is not defined. The plan requires ingestion reports and a visible fallback when anchors are weak or missing, yet it does not decide when document-level citation is still acceptable, when a claim must be downgraded, or when the answer should refuse a claim. This will become a live ambiguity as soon as real corpus ingestion starts.

### P3 / improvement
- Evaluation artifacts should be made explicit, not implied. For each scenario run, the plan should require storage of the retrieval plan, gap record, approved ledger, and final answer so later manual review can diagnose whether a failure came from retrieval, normalization, controller logic, or synthesis.

## 4. Summary verdict

- Overall verdict: `not ready`
- Short rationale: The plan is disciplined on scope and stays aligned with the chosen Option A architecture, but two implementation-critical contracts are still missing: the controller rules for blocking or downgrading claims, and the retrieval-gap/web-trigger rules that defend the highest-available-source requirement. Those need to be locked before core-path coding starts.

## 5. What the plan gets right

- It stays inside the selected Option A architecture instead of quietly drifting toward graph-first or multi-specialist designs.
- It keeps V1 scope narrow: EU-first, curated corpus first, defensive web second, no separate UI, no broad member-state engine, and no freshness automation.
- The phase sequence maps cleanly onto the Option A architecture components: corpus foundation, ranked retrieval, defensive web expansion, evidence ledger, source-role control, answer composition, and evaluation.
- It preserves the right quality stance for this project: explicit controls, visible configs, visible logs, and an evaluation gate that includes the required scenarios and the high-risk failure pattern.

## 6. Missing implementation decisions

- The claim-state and answer contract need to be specified: what counts as a core claim, what minimum support is needed for each claim state, and when document-only support is acceptable versus downgrade or block.
- The retrieval-gap contract needs explicit triggers and stop conditions: how the planner decides a high-rank source layer has been searched sufficiently, when web fallback is allowed, and what artifact records that decision.
- The source hierarchy needs operational tie-break rules for partially overlapping evidence across regulation, implementing acts, standards, and official project material.
- The anchor-degradation contract needs to be fixed: what the answer may still say when anchors are weak or absent, and how that changes ledger status.

## 7. Scope or architecture drift risks

- If ranking, gap detection, or source-role exceptions end up living mainly in prompt text instead of visible config and controller code, the implementation will drift away from Option A's inspectable-control premise.
- Scenario C first can bias the build toward a standards-only happy path and delay the harder cross-layer and failure-mode work that actually justified choosing Option A.
- Anchor weakness could silently widen into "document citation is always enough" unless the degraded-answer rules are explicitly bounded now.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | Partially meets | The plan names `source_hierarchy.yaml`, but not the operational ranking semantics or tie-break behavior needed by the planner and controller. |
| Web allowlist is explicit | Partially meets | The plan names `web_allowlist.yaml` and an allowlisted fetch path, but not the concrete trigger or review rule for adding domains or expanding source classes. |
| Unsupported-claim blocking is explicit | Partially meets | The requirement is repeated clearly, but the actual block/downgrade decision table is still missing. |
| Retrieval-miss failure is explicitly tested | Partially meets | The high-risk failure pattern is present in Phase 6, but the plan does not yet define concrete fixtures or pass/fail signals for a missed-governing-source test. |
| Anchor weakness has a fallback path | Partially meets | A fallback is required and anchor reporting is planned, but the degraded answer behavior is not specified. |
| V1 non-goals are protected | Meets | Non-goals are explicit and consistent with the selected architecture. |

## 9. Gate recommendation

- Can coding start after this review? `no`
- If no, what must change first? `Lock three implementation contracts before core-path coding: (1) claim-state plus block/downgrade rules, (2) retrieval-gap plus web-trigger rules, and (3) degraded answer behavior when anchors are weak or missing. Also change the first vertical slice so it exercises at least one cross-layer or missed-governing-source case, not Scenario C alone.`
