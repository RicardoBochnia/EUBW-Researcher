# Option A Implementation Plan Review

Status: completed
Reviewer: reviewer-1
Date: 2026-03-30
Review target: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 1. Required inputs

- [../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../PLAN.md](../PLAN.md)
- [../REVIEW.md](../REVIEW.md)
- [../../../OPTIONS_COMPARISON.md](../../../OPTIONS_COMPARISON.md)
- [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 2. Review goal

Assess whether the implementation plan is concrete enough, disciplined enough, and narrow enough to start coding without silently reopening architecture or scope.

## 3. Findings

### P1 / blocker

- None found.

### P2 / important risk

- **Gap-detection trigger is still unspecified.** The architecture review (REVIEW.md §5) already flagged that the concrete rule for when web expansion fires and how the retrieval planner decides a higher-ranked source is "still missing" is underspecified. The implementation plan repeats the intent (Phase 2: "explicit gap record", Phase 3: "only used after a documented local-corpus gap") but does not add an implementable rule or even a placeholder decision contract. This is the single most load-bearing design decision that remains open, because it directly gates the non-negotiable property. Without it, Phase 2 and Phase 3 cannot be acceptance-tested against each other.
- **Hard-block vs. downgrade threshold for unsupported claims is not operational.** Phase 4 says the controller "blocks unsupported core claims" and "downgrades weakly supported claims." The distinction between block and downgrade needs at least a working definition before implementation — otherwise the Phase 4 acceptance criteria ("no core claim can reach the final answer without at least document-level support") will be interpreted ad hoc during coding.
- **Anchor extraction failure mode needs a concrete fallback contract.** Phase 1 acceptance criteria require that anchor extraction failures are "visible in logs or reports, not silent." Phase 5 says answers include "anchor references where available." What is missing is the explicit rule for what happens downstream when anchors fail: does the evidence ledger entry degrade to document-level only, does it carry a quality flag, does the answer composer render it differently? The architecture REVIEW.md §5 also flagged this gap. The implementation plan should specify at least the default fallback path so that Phases 1, 4, and 5 are consistent.

### P3 / improvement

- **Scenario references in Phase 6 are abstract.** Phase 6 lists "primary success scenario, Scenario A, Scenario B, Scenario C, high-risk failure pattern" but does not tie them to concrete fixture expectations or pass/fail criteria beyond the manual checklist. Adding one concrete pass/fail example per scenario (even if rough) would make the evaluation gate actually testable rather than procedural.
- **No explicit dependency or ordering constraint between Phases 2 and 3.** The plan's Phase 3 (web expansion) conceptually depends on Phase 2's gap detection output. This dependency is implicit but not called out as a build-sequence constraint. Since §10 already proposes a "thin vertical slice through Phases 2 to 5," the dependency is likely handled in practice, but it would be cleaner to make it explicit.
- **The "thin vertical slice" strategy in §10 is good but could name the slice's exit criterion.** §10 recommends starting with Scenario C as the first vertical slice, which is a sound choice (it is the narrowest and most contained). But there is no stated exit criterion for when the slice is considered complete enough to broaden. A lightweight gate (e.g., "Scenario C produces a reviewable answer with document-level citations and correct source-role tags before broadening") would prevent scope creep from the start.
- **`evaluation/` module purpose is thin.** The repo shape lists `evaluation/` as "scenario runner and result logging." Given that Phase 6 is the hardening gate and the evaluation scenarios are the primary V1 quality signal, the implementation plan should clarify whether `evaluation/` also owns the pass/fail criteria definitions or whether those live in `configs/evaluation_scenarios.yaml`. This is a minor structural ambiguity.

## 4. Summary verdict

- Overall verdict: `ready with revisions`
- Short rationale: The plan is well-structured, scope-disciplined, and faithful to the architecture choice. It does not silently reopen the architecture or inflate V1 scope. The three P2 items (gap-detection trigger, block-vs-downgrade threshold, anchor-failure fallback) are not blockers because the plan can start with Phase 0 and Phase 1 while those decisions are specified. But they must be resolved before Phase 2 and Phase 4 acceptance testing can be meaningful.

## 5. What the plan gets right

- Faithful to the selected architecture: the plan does not smuggle in graph persistence, multi-agent orchestration, or UI scope. The frozen design choices in §3 are exactly the right constraints.
- The build sequence is well-phased with clear deliverables and acceptance criteria per phase. Each phase has a testable output.
- The V1 non-goals in §7 are explicit and well-chosen, directly matching the requirements basis scope boundaries.
- The risk controls in §8 are concrete and auditable — they name six specific things that must exist, not abstract quality goals.
- The recommended build order in §10 (Scenario C first as the narrowest vertical slice) is a disciplined choice that keeps the first coded path debuggable.
- The manual-effort minimization rules in §9 show awareness that the real user cost is not just answer quality but also operational overhead.
- The implementation assumptions in §4 are honest and appropriately scoped (Python, CLI-first, no separate UI, local metadata model).

## 6. Missing implementation decisions

- **Gap-detection rule**: what quantitative or structural signal tells the retrieval planner that a higher-ranked source is "still missing"? At minimum, define whether this is coverage-based (no high-rank hits above a relevance threshold), role-based (no source from a required role layer), or both.
- **Block vs. downgrade threshold**: what distinguishes a "core claim" that must be blocked from a "weakly supported claim" that can be downgraded? Candidates: source-role level of the best supporting evidence, number of supporting sources, explicit vs. inferred connection to the user question.
- **Anchor-failure fallback path**: when anchor extraction fails or produces low-confidence results, does the evidence ledger entry degrade to document-level, carry a confidence flag, or both? How does the answer composer render document-level-only evidence differently from anchor-grounded evidence?
- **Reranking specifics in Phase 2**: the plan mentions a "reranking step that incorporates source role and likely topical fit" but does not specify whether this is LLM-based, embedding-based, or rule-based. This choice has direct cost and latency implications.

## 7. Scope or architecture drift risks

- **Low risk overall.** The plan is notably disciplined about not expanding scope.
- **Minor drift risk in Phase 5**: "non-blocking clarification behavior for broad questions" is listed as a deliverable. The requirements basis (§5) explicitly says clarification is desirable but not a must-have. The implementation plan should ensure this does not become a dialog-flow feature that exceeds V1 scope. The current wording ("non-blocking") suggests awareness of this boundary, but it is worth a lightweight gate: if clarification behavior takes more than trivial effort, defer it.
- **No architecture drift detected.** The plan does not reintroduce persistent graphs, multi-agent patterns, or broad member-state machinery.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | Present: §1 fixed constraints, §3 frozen choices, `configs/source_hierarchy.yaml` in repo shape | None. |
| Web allowlist is explicit | Present: `configs/web_allowlist.yaml` in repo shape, Phase 3 deliverables | None. |
| Unsupported-claim blocking is explicit | Present: Phase 4 deliverables and acceptance criteria | The block-vs-downgrade threshold needs operationalizing (see P2 findings). |
| Retrieval-miss failure is explicitly tested | Present: Phase 6 includes high-risk failure pattern as a required scenario | Pass/fail criteria for the scenario are not yet concrete (see P3 findings). |
| Anchor weakness has a fallback path | Partially present: Phase 1 requires visible failures, Phase 5 says "where available" | The explicit downstream fallback path is missing (see P2 findings). |
| V1 non-goals are protected | Present: §7 lists six explicit non-goals | No drift detected. |

## 9. Gate recommendation

- Can coding start after this review? `yes, with conditions`
- Conditions before Phase 2 begins:
  1. Specify a working gap-detection rule (even a simple initial heuristic) so that Phase 2 and Phase 3 can be tested against each other.
  2. Define the block-vs-downgrade threshold so that Phase 4 acceptance criteria are testable.
  3. Specify the anchor-failure fallback path so that Phases 1, 4, and 5 are internally consistent.

Phase 0 and Phase 1 can proceed immediately. The three conditions above should be resolved in a lightweight addendum before Phase 2 work begins.
