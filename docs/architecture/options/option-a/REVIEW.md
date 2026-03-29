# Option A Review

Status: consolidated from external review wave
Reviewed option: option-a

## 1. Reviewed inputs

- PLAN used: [PLAN.md](./PLAN.md)
- Requirements basis used: [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Masterplan used: [../../MASTERPLAN.md](../../MASTERPLAN.md)
- Requirements patches used: [../../REQUIREMENTS_PATCHES.md](../../REQUIREMENTS_PATCHES.md) (no decided patches at initial handoff)

Consolidation note: this file summarizes the raw batch reviews in [../../reviews/reviewer-1.md](../../reviews/reviewer-1.md), [../../reviews/reviewer-2.md](../../reviews/reviewer-2.md), [../../reviews/reviewer-3.md](../../reviews/reviewer-3.md), and [../../reviews/reviewer-4.md](../../reviews/reviewer-4.md).

## 2. Summary verdict

- Overall verdict: `Strongest serious V1 fit`
- Short rationale: `Across all four reviewers, Option A is the clearest match to the non-negotiable requirement to avoid unsupported or wrongly supported core claims while staying operationally plausible for V1. Its main residual risk is not design mismatch but whether ranked retrieval and anchor extraction are good enough to keep the evidence ledger complete.`

## 3. Supported findings

- The option defines the clearest staged path from question analysis through ranked retrieval, evidence normalization, source-role control, and final synthesis.
- The curated corpus is explicitly privileged, and web expansion is gap-driven and restricted to acceptable official or standards-like sources.
- Source ranking, source-role preservation, conflict marking, and unsupported-claim blocking are all first-class design elements rather than post-hoc answer wording.
- EU-first handling is explicit, with Germany and other national material treated as controlled best-effort extension rather than baseline dependency.
- The plan openly accepts higher latency in exchange for defensibility and inspectability, which matches the requirements basis.

## 4. Judgment calls

- This is the best-balanced V1 option because it addresses the core pain points without taking on the graph-ingest burden of Option B or the orchestration burden of Option C.
- The same conservative evidence gating that best supports compliance may also make the option somewhat less rich on relationship-heavy grouping and exploratory discovery than the more ambitious alternatives.
- The simpler control flow is likely to be more inspectable and easier to discipline in real use than the more complex options.

## 5. Unresolved uncertainties

- The plan does not yet specify the concrete rule for gap detection that triggers web expansion or how the retrieval planner decides that a higher-ranked source is still missing.
- Anchor extraction quality is load-bearing for the evidence ledger, but the plan does not yet show how anchor failures are detected or degraded gracefully.
- The controller is conceptually strong, but the exact mechanism for hard blocking versus downgrading unsupported claims remains design-level rather than operationally specified.
- Requirement grouping in the primary success scenario may remain somewhat shallow because the design optimizes for traceability first and richer structural modeling second.

## 6. Likely later evaluation needs

- Retrieval-completeness testing on questions where a governing higher-ranked source exists but is easy to miss.
- Audits of article- and section-level anchor quality on the highest-value EU and standards sources.
- Scenario-based testing of whether provisional grouping remains useful without overstating certainty.
- Adversarial checks that the source-role controller really prevents false elevation when lower-rank material is highly relevant but non-governing.

## 7. Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Meets | `PLAN Sections 1, 4, 5` | None material. |
| R2 | Meets | `PLAN Sections 3, 4, 5, 7` | Cross-document lateral discovery still depends on retrieval quality rather than persistent relationship modeling. |
| R3 | Meets | `PLAN Sections 5, 7, 8, 10` | Final answer rendering of hierarchy is not yet concretely exemplified. |
| R4 | Meets | `PLAN Sections 4, 5, 10` | If the governing source is never retrieved, the downstream controller cannot fully compensate. |
| R5 | Meets | `PLAN Sections 7, 8` | National best-effort coverage may remain thin where metadata is sparse. |
| R6 | Meets | `PLAN Sections 8, 9` | None material. |
| R7 | Meets | `PLAN Sections 4, 5, 6` | Gap-detection trigger remains underspecified. |
| R8 | Meets with caveat | `PLAN Sections 7, 8, 9, 10` | Practical success on grouping-heavy questions depends on retrieval completeness and anchor reliability. |

## 8. Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Strong for V1: proposal and annex material can be aligned in one evidence ledger and turned into a provisional grouping. | Grouping quality may remain somewhat shallow because traceability is prioritized over richer structural discovery. |
| Scenario A | Strong for V1: stage-gated cross-layer retrieval maps naturally to regulation, acts, standards, and official implementation material. | Weakly linked national or project documents may still be hard to discover. |
| Scenario B | Strong for V1: EU-first reasoning is explicit and Germany is treated as controlled best-effort extension. | National nuances may be missed if retrieval signals are weak. |
| Scenario C | Good for V1: targeted standards retrieval plus anchor-level evidence supports more than a yes/no answer. | Subtle protocol interpretation may still be less elegant than in a richer structural model. |
| High-risk failure pattern | Better defended than the other options because ranked planning and ledger approval explicitly guard against under-supported synthesis. | A higher-ranked source missed entirely during retrieval remains the key residual failure mode. |

## 9. Reviewer-perspective notes

### Traceability / Compliance
- Best explicit source-role discipline and clearest direct guard against unsupported core claims in the set.
- Main compliance risk is not internal flattening but silent upstream retrieval misses.

### System / Data / Performance
- Moderate complexity, cost, and maintenance burden relative to the value promised in V1.
- Strong dependence on anchor extraction quality and ranked retrieval behavior.

### Research Workflow / User Value
- Best fit for the current EU-first deep-research workflow because it reduces repeated manual source-landscape reconstruction without heavy persistent infrastructure.
- Likely dependable in early use, though less exciting than Option B for relationship-heavy exploratory grouping.
