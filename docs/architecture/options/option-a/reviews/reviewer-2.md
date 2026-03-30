# Option A Implementation Plan Review

Status: completed
Review target: [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 1. Required inputs

- [../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../PLAN.md](../PLAN.md)
- [../REVIEW.md](../REVIEW.md)
- [../../../OPTIONS_COMPARISON.md](../../../OPTIONS_COMPARISON.md)
- [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 2. Review goal

Assess whether the implementation plan is concrete enough, disciplined enough, and narrow enough to start coding without silently reopening architecture or scope.

## 3. Findings

List findings first, ordered by severity.

### P1 / blocker
- **Web-expansion trigger is underspecified**: The plan mentions "gap detection" as the condition to allow list-based web fallback, but does not define what constitutes a gap (e.g., no sources retrieved vs. low confidence vs. contradicted sources). 
- **Anchor extraction fallback is undefined**: The architecture review highlighted anchor extraction as load-bearing. The plan lists "visible fallback when anchors are weak" as a risk control, but misses specifying what the fallback actually entails (e.g., document-level citation only, or claim downgrade).

### P2 / important risk
- **Ledger block/downgrade mechanism is conceptual**: Phase 4 correctly mandates blocking unsupported claims, but lacks a technical strategy for how the logic differentiates between blocking a claim entirely versus downgrading it to an interpretive/open point.
- **High-risk failure untested until Phase 6**: The sequence keeps hardening and testing the high-risk failure pattern ("plausible but overlooks higher-ranked source") until Phase 6. This risks finding fundamental issues with the retrieval planner (Phase 2) late in implementation.

### P3 / improvement
- **Phase 1 metadata output**: The ingestion report should explicitly test that source-role rank is correctly loaded, as it is a firm prerequisite for Phase 2's planner.

## 4. Summary verdict

- Overall verdict: `ready with revisions`
- Short rationale: The plan successfully maps the evidence-first architecture into V1 build phases, but requires operational clarity on the web-fallback trigger and anchor fallback behaviors to prevent scope drift during coding.

## 5. What the plan gets right

- The phase sequence enforces the non-negotiable requirement of source-role discipline, focusing on curated corpus ingestion and evaluation before complex orchestrations.
- It correctly protects the V1 scope by actively minimizing manual effort loops and explicitly listing multi-agent flows or graph structures as non-goals.
- Evaluative testing and the high-risk failure scenario are first-class deliverables.

## 6. Missing implementation decisions

- The precise criteria that trigger Phase 3 web expansion based on a "local-corpus gap".
- The defined system behavior when Phase 1 fails to extract article/section-level anchors for critical documents (e.g., fallback to document-level citation).
- The operational logic that dictates whether a weakly supported claim is blocked completely or conditionally passed as an uncertain observation in Phase 4.

## 7. Scope or architecture drift risks

- **Gap-detection sprawl**: If left undefined, developers might implement an overly complex logic for gap-detection that silently introduces orchestration loops.
- **Web scraping boundary**: Web expansion normalization could pull in non-compliant material if the allowlist parser isn't strictly gated.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | Meets | Requires verification in the Phase 1 Ingestion Report. |
| Web allowlist is explicit | Meets | None material. |
| Unsupported-claim blocking is explicit | Meets | The mechanism is conceptual and needs a defined condition. |
| Retrieval-miss failure is explicitly tested | Meets | Slated for Phase 6; consider shifting a spike earlier. |
| Anchor weakness has a fallback path | Fails | The plan flags the control but does not declare the fallback behavior. |
| V1 non-goals are protected | Meets | Safe; clearly categorized in Section 7. |

## 9. Gate recommendation

- Can coding start after this review? `no`
- If no, what must change first? The implementation plan must define the exact trigger conditions for web expansion and the concrete fallback behavior for missing anchor metadata before Phase 1 commences.
