# Option A Implementation Plan Review

Status: completed (revised plan review)
Review target: [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 1. Required inputs

- [../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../PLAN.md](../PLAN.md)
- [../REVIEW.md](../REVIEW.md)
- [../../../OPTIONS_COMPARISON.md](../../../OPTIONS_COMPARISON.md)
- [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)
- [../IMPLEMENTATION_REVIEW.md](../IMPLEMENTATION_REVIEW.md) (consolidated wave 1 review)

## 2. Review goal

Assess whether the revised implementation plan is concrete enough, disciplined enough, and narrow enough to start coding without silently reopening architecture or scope. This review focuses specifically on whether the revisions address the gaps identified in review wave 1.

## 3. Findings

### P1 / blocker
- None. The three load-bearing gaps identified in my wave 1 review — web-expansion trigger, unsupported-claim gate, and anchor-failure fallback — are now addressed by explicit operational contracts in sections 5.1–5.3.

### P2 / important risk
- **Gap-record exhaustion criteria may be too strict for V1 practice.** Section 5.2 requires that both lexical and semantic retrieval have been run on the required source layer and that top local candidates have been inspected before a layer is considered exhausted. This is the right principle, but strict enforcement could make web expansion prohibitively slow for queries that span multiple source layers. A regulation-heavy question touching three source layers would need six retrieval passes (lexical + semantic × 3 layers) plus candidate inspection before any web expansion is allowed. The plan should acknowledge this latency risk explicitly and allow the implementation to decide whether the two-method requirement can be satisfied in parallel.
- **Tie-break rules for conflicting admissible evidence (section 5.1) introduce a "more directly on-point" judgment.** This is conceptually correct — among same-rank admissible sources, the more specific provision should win. But "more directly on-point" is not mechanistically defined and could depend on LLM interpretation during the Source Role Controller step. If this judgment is implemented as an LLM call, it becomes an opaque mini-evaluation inside the controller, which works against the plan's inspectability goals. The initial implementation should use a simple structural heuristic (e.g., provision specificity measured by scope or article granularity) rather than a semantic judgment call.
- **The contradiction rule in section 5.2 could under-serve the "open" scenario.** The rule states that contradictory local evidence does not itself justify web expansion, which is correct to prevent unnecessary web sprawl. However, when two high-rank sources materially contradict each other (the `open` state from section 5.1), the user may need the system to look for a resolving higher-rank source or a later amendment. The plan should clarify that `open` claim states should be surfaced as an explicit answer-level uncertainty even if web expansion is not triggered — ensuring the researcher knows where to dig manually.

### P3 / improvement
- **Phase 1 ingestion report should also emit source-role level per document,** not just anchor quality. Phase 2's retrieval planner depends on accurate source-role metadata. If the ingestion step does not explicitly validate and report mapped source-role levels, misclassification could silently propagate through the entire pipeline.
- **Section 5.3 anchor-degradation contract is good but could specify one additional case:** what happens when a document is clearly governing but has neither anchor- nor document-level structure (e.g., a PDF without article/section markers)? The current contract assumes at least document-level citation is always available. For the V1 corpus this is likely true, but a one-line fallback rule (e.g., full-document citation with a `structure_poor` flag) would close the gap.
- **The build sequence's second thin slice (step 4 in section 11) now addresses my wave 1 concern about early regulation-heavy testing.** This is a clear improvement. However, the exit criteria for the second slice are still implicit. A one-sentence gate — such as "the second slice is complete when it produces a reviewable answer for a missed-governing-source case with correct `blocked` or `open` claim states" — would make Phase 6 less of a catch-all.

## 4. Summary verdict

- Overall verdict: `ready`
- Short rationale: The revised plan has addressed the three critical gaps from wave 1 — web-expansion trigger, claim-state operationalization, and anchor-degradation fallback — with concrete, testable contracts. The remaining P2 items are implementation-time calibration risks, not design-level gaps. They do not block coding; they need monitoring during Phases 2 and 4.

## 5. What the plan gets right

- **Sections 5.1–5.3 are the single most important improvement.** They transform the three abstract design commitments that all wave 1 reviewers flagged into explicit operational contracts with defined states, rules, and fallbacks. The claim-state model (`confirmed`, `interpretive`, `open`, `blocked`) is well-aligned with the requirements basis and is directly testable.
- **The gap-record structure (section 5.2) is the right mechanism** for making web-expansion decisions auditable. Requiring a documented record of what was searched, what was inspected, and why local evidence is insufficient makes the gap-detection decision itself inspectable, not just its outcome.
- **The anchor-degradation contract (section 5.3) correctly distinguishes** between technical extraction failures (which can still yield `confirmed` if the governing source is clear) and epistemic gaps (which must downgrade to `interpretive` or lower). This prevents the system from being paralyzed by extraction noise while still enforcing source-quality discipline.
- **The revised build sequence (section 11, steps 3–4)** addresses the wave 1 concern about the first thin slice being too narrow. Starting with Scenario C and then immediately testing a regulation-heavy or missed-governing-source case before broadening correctly front-loads the architecture's main residual risk.
- **V1 scope protection remains strong.** No drift toward persistent graphs, multi-agent orchestration, broad member-state coverage, or UI work.
- **The plan stays inside the requirements basis** without silently reinterpreting, weakening, or extending the frozen requirements.

## 6. Missing implementation decisions

- **Parallel vs. sequential exhaustion for multi-layer queries.** Section 5.2 requires both lexical and semantic retrieval per layer before exhaustion, but does not say whether layers can be processed in parallel. For V1 latency, this matters.
- **Reranking method.** Phase 2 mentions reranking that incorporates source role and topical fit but does not specify whether this is LLM-based, embedding-based, or rule-based. This is an acceptable implementation-time decision, but its cost and latency implications should be tracked.
- **Top-K threshold for candidate inspection.** Section 5.2 says "top local candidates" must be inspected, but does not set a default K. This is a tuning parameter, but an initial default (e.g., K=5) would help Phase 2 acceptance testing be concrete.

## 7. Scope or architecture drift risks

- **Low risk overall.** The plan does not reintroduce graph persistence, multi-agent patterns, or broad member-state machinery.
- **Tie-break logic (section 5.1) could drift into a semantic evaluation loop** if the "more directly on-point" judgment is implemented as an LLM call. This should be kept as a simple structural rule in the first implementation.
- **Phase 5 clarification behavior** remains "non-blocking" per the plan, which is appropriately scoped. The requirements basis (§5) says clarification is desirable but not must-have. If clarification takes more than trivial implementation effort, it should be deferred.
- **No architecture drift detected.** The plan does not smuggle in design patterns from Options B or C.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | Meets | Config file is named; hierarchy is carried from the requirements basis. Phase 1 ingestion should also emit per-document source-role level for validation. |
| Web allowlist is explicit | Meets | Config file is named; section 5.2 defines when web expansion is allowed. Section 5.3 defines the minimum metadata contract for normalized web sources. |
| Unsupported-claim blocking is explicit | Meets | Section 5.1 defines `blocked` state with clear trigger conditions and tie-break rules. Testable on examples. |
| Retrieval-miss failure is explicitly tested | Meets | Phase 2 acceptance criteria require a negative fixture that produces a gap record. Build sequence step 4 adds an early regulation-heavy or missed-governing-source test. |
| Anchor weakness has a fallback path | Meets | Section 5.3 defines `document_only` flag, downstream ledger behavior, and answer rendering rules. Core claims may still use document-only evidence under specified conditions. |
| V1 non-goals are protected | Meets | Section 8 lists six explicit non-goals; no drift detected. |

## 9. Gate recommendation

- Can coding start after this review? `yes`
- Phase 0 and Phase 1 can proceed immediately.
- Phase 2+ can proceed once this review wave confirms the revised contracts are accepted.
- Watchpoints for implementation: (1) monitor latency impact of strict multi-method exhaustion in section 5.2, (2) keep tie-break logic structurally simple in the first cut, (3) track reranking method choice for cost implications.
