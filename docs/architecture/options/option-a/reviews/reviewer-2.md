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
- `None.` The revisions successfully addressed previous blockers regarding gap detection and anchor fallbacks.

### P2 / important risk
- **Tie-break logic complexity**: The rules for resolving conflicts between admissible evidence (Section 5.1) are conceptually sound, but programmatically determining which provision is "more directly on-point" among same-rank sources could be fragile. The system might default too often to an `open` state if this logic is strictly applied, which should be closely monitored during Phase 4.

### P3 / improvement
- **Phase 1 metadata output**: While anchor extraction logging is required by Phase 1, the ingestion report should also explicitly list the `source role level` mapped to each document to ensure Phase 2's planner receives the correct baseline metadata.

## 4. Summary verdict

- Overall verdict: `ready`
- Short rationale: The revised plan thoroughly translates the architecture into a concrete build plan. By explicitly defining operational contracts for claim-states (block vs. downgrade), web-expansion triggers, and anchor-degradation fallbacks, the plan establishes strict guardrails for compliance without being functionally paralyzed.

## 5. What the plan gets right

- **Explicit operational contracts**: Sections 5.1 to 5.3 successfully migrate the architecture from abstract rules to actionable, testable code states (`confirmed`, `interpretive`, `open`, `blocked`, and gap records).
- **Shift-left on failure testing**: Moving the test for the highest-risk failure mode ("missed governing source") up into Phase 2 ensures the core retrieval planner handles absence properly before the rest of the ledger is built.
- **Protects V1 scope**: Rejects unnecessary multi-agent orchestrations and explicitly defines manual-effort minimization boundaries.

## 6. Missing implementation decisions

- **Top Candidate Thresholds**: The gap-record contract states a high-rank layer is exhausted when "top local candidates" are inspected, but does not yet establish the specific tuning bounds (e.g., top-K documents or semantic distance thresholds). This is an acceptable minor tuning decision left to implementation.

## 7. Scope or architecture drift risks

- **Tie-breaker drift**: Implementing the "more directly on-point provision" tie-breaker could inadvertently introduce resource-heavy semantic evaluation loops during the Source Role Controller step (Phase 4), functioning as an opaque, mini orchestrator. The initial implementation here must be kept intentionally simple.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | Meets | Requires verification during Phase 1 logging. |
| Web allowlist is explicit | Meets | Addressed via configuration and phase requirements. |
| Unsupported-claim blocking is explicit | Meets | Claim-state logic explicitly forces `blocked` outcomes. |
| Retrieval-miss failure is explicitly tested | Meets | Promoted to a hard acceptance criterion in Phase 2. |
| Anchor weakness has a fallback path | Meets | Explicitly resolved via the `document_only` citation quality flag. |
| V1 non-goals are protected | Meets | Safe; explicitly documented out-of-scope boundaries. |

## 9. Gate recommendation

- Can coding start after this review? `yes`
- If no, what must change first? `n/a`
