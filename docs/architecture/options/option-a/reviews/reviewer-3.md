# Option A Implementation Plan Review

Status: completed
Review target: [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 1. Required inputs

- [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../PLAN.md](../PLAN.md)
- [../REVIEW.md](../REVIEW.md)
- [../../OPTIONS_COMPARISON.md](../../OPTIONS_COMPARISON.md)
- [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)

## 2. Review goal

Assess whether the implementation plan is concrete enough, disciplined enough, and narrow enough to start coding without silently reopening architecture or scope.

## 3. Findings

List findings first, ordered by severity.

### P1 / blocker
- No blocker found that reopens the Option A architecture choice.

### P2 / important risk
- The plan leaves the web-expansion trigger too underspecified. "Documented gap" and "higher-rank source still missing" are central control points for Option A, but there is no concrete implementation rule or threshold for when the planner must stop, fallback, or escalate uncertainty.
- Unsupported-claim control is still one design layer too abstract. The plan commits to blocking or downgrading unsupported claims, but does not yet define the operational contract for what minimum ledger state is required before a claim is allowed into answer composition.
- Scenario-first build order is sensible, but the thin vertical slice starts with Scenario C. That is useful for debugging the evidence pipeline, yet it under-tests the architecture's hardest V1 obligations around cross-layer source ranking, member-state best-effort handling, and the "missed governing source" failure mode.

### P3 / improvement
- The target repository shape is good, but the contract between `retrieval/`, `evidence/`, and `answering/` should be specified more explicitly before coding starts to reduce hidden interface churn.
- The plan should state the minimum metadata fields required for web-normalized sources to be eligible for answer use, not just for retrieval use.
- The evaluation phase should name at least one concrete negative test for false elevation and one for weak-anchor degradation, not only the category names.

## 4. Summary verdict

- Overall verdict: `ready with revisions`
- Short rationale: `The plan is disciplined, V1-bounded, and aligned with the requirements basis and the selected Option A architecture. Coding can start soon, but the web-expansion trigger, unsupported-claim gate, and early validation ordering should be tightened first because they are load-bearing for the non-negotiable support-fidelity requirement.`

## 5. What the plan gets right

- It stays inside Option A rather than drifting toward graph-first or multi-specialist redesign.
- It carries the requirements basis forward correctly: EU-first, quality over latency, curated corpus first, defensive web second, and explicit preservation of hierarchy, contradiction, uncertainty, and source role.
- The implementation phases are narrow enough to support a greenfield build without pretending V1 needs full productization.
- Risk controls are visible and correctly centered on source hierarchy, unsupported-claim blocking, fallback visibility, and retrieval-miss testing.

## 6. Missing implementation decisions

- What exact conditions count as a documented retrieval gap that justifies web expansion?
- What exact ledger state is sufficient for a claim to be rendered as confirmed, interpretive, or open?
- What is the fallback rendering rule when anchors are missing for a source that is otherwise clearly governing?
- What minimum metadata contract must a normalized web source satisfy before it can support a core claim?

## 7. Scope or architecture drift risks

- The Python/backend/CLI assumptions are acceptable as implementation assumptions, but they should remain implementation defaults and not drift into a broader platform-design exercise.
- Phase 3 web expansion can easily widen scope if allowlist and gap-detection logic are not kept narrow.
- Later evaluation could silently broaden into a benchmark program. For V1, it should remain tied to the named scenarios and failure patterns from the requirements basis.

## 8. Risk controls check

| Check | Assessment | Concern if any |
| --- | --- | --- |
| Source hierarchy is explicit | `yes` | The config is named, but the ranking/override logic is not yet operationally specified. |
| Web allowlist is explicit | `partially` | The allowlist file is planned, but the admission contract for normalized web evidence is still too implicit. |
| Unsupported-claim blocking is explicit | `partially` | The intention is explicit; the exact ledger-to-answer blocking rule still needs specification. |
| Retrieval-miss failure is explicitly tested | `yes` | Good at plan level, but should be pulled earlier into the first hardening slice, not left mostly to Phase 6. |
| Anchor weakness has a fallback path | `partially` | The plan says weak anchors must not fail silently, but the answer-side degradation behavior is not yet specified. |
| V1 non-goals are protected | `yes` | Non-goals are clear and appropriately narrow. |

## 9. Gate recommendation

- Can coding start after this review? `yes`
- If no, what must change first? `Not applicable, but coding should start only after tightening three points in the plan: (1) web-expansion trigger and stop conditions, (2) operational unsupported-claim gate between ledger and answer composer, and (3) early validation ordering so the first end-to-end slice also exercises at least one regulation-heavy retrieval-miss risk case in addition to Scenario C.`
