# Option B Review

Status: consolidated from external review wave
Reviewed option: option-b

## 1. Reviewed inputs

- PLAN used: [PLAN.md](./PLAN.md)
- Requirements basis used: [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Masterplan used: [../../MASTERPLAN.md](../../MASTERPLAN.md)
- Requirements patches used: [../../REQUIREMENTS_PATCHES.md](../../REQUIREMENTS_PATCHES.md) (no decided patches at initial handoff)

Consolidation note: this file summarizes the raw batch reviews in [../../reviews/reviewer-1.md](../../reviews/reviewer-1.md), [../../reviews/reviewer-2.md](../../reviews/reviewer-2.md), [../../reviews/reviewer-3.md](../../reviews/reviewer-3.md), and [../../reviews/reviewer-4.md](../../reviews/reviewer-4.md).

## 2. Summary verdict

- Overall verdict: `Promising but high V1 delivery risk`
- Short rationale: `All reviewers saw Option B as the strongest design for explicit cross-layer relationship modeling and provisional grouping, but also as highly dependent on graph completeness, provision-level normalization, and ongoing ingest quality. It remains attractive, yet materially riskier than Option A for an initial V1.`

## 3. Supported findings

- The plan defines a concrete path from query analysis through graph traversal, passage retrieval, evidence packaging, and final synthesis.
- Source role, jurisdiction, and provenance are explicit graph elements rather than left implicit until answer time.
- The curated corpus remains primary, and web additions are supposed to be typed before influencing synthesis.
- The plan honestly identifies graph incompleteness and maintenance burden as major V1 risks.
- Reviewers consistently agreed that this option is especially attractive for relationship-heavy questions and the primary success scenario's cross-document grouping need.

## 4. Judgment calls

- This is the option with the highest structural upside for cross-layer discovery, reference tracing, and relationship-heavy exploratory work.
- It is also the easiest serious option to over-trust: a clean graph can create an illusion of completeness even when a decisive higher-ranked source is missing.
- For V1, the graph-ingest and maintenance burden appears high relative to the requirements basis, which emphasizes source-bound synthesis and source-role discipline more directly than persistent structural elegance.

## 5. Unresolved uncertainties

- The plans do not yet show how provision segmentation, reference extraction, and graph quality will be verified on the actual corpus.
- It remains unclear what the system does when a query depends on material that should be in the graph but is not: explicit gap reporting, fallback retrieval, or silent undercoverage.
- Weakly linked national or project material may only enter the graph at coarse granularity, reducing practical value on those layers.
- The design is less explicit than Option A about a hard pre-answer controller that blocks weakly supported claims.

## 6. Likely later evaluation needs

- Run a proof-of-concept ingest on a small core set of EU sources to test provision-level segmentation and reference extraction quality.
- Benchmark graph completeness on explicit reference chains between proposal text, annex material, implementing acts, and standards.
- Probe for false completeness by intentionally removing governing links and measuring whether the system visibly degrades or silently overstates confidence.
- Compare the value of graph-backed grouping and cross-source discovery against the simpler evidence-ledger approach of Option A.

## 7. Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Meets | `PLAN Sections 1, 4, 5` | None material. |
| R2 | Meets | `PLAN Sections 3, 4, 5, 7` | Practical reach depends heavily on graph completeness and normalization quality. |
| R3 | Meets | `PLAN Sections 5, 7, 8, 10` | Hidden graph incompleteness can still distort the apparent hierarchy and provenance story. |
| R4 | Partially meets | `PLAN Sections 4, 5, 10` | The option is less explicit than Option A about a hard block-or-downgrade mechanism for unsupported core claims before answer emission. |
| R5 | Meets | `PLAN Sections 7, 8` | Germany or national reasoning remains feasible but coarser and more fragile in V1. |
| R6 | Meets | `PLAN Sections 8, 9` | Up-front modeling effort may delay useful V1 output. |
| R7 | Meets | `PLAN Sections 4, 5, 6` | Typed web additions are promising, but typing quality becomes part of the answer-risk surface. |
| R8 | Meets with caveat | `PLAN Sections 7, 8, 9, 10` | Success depends on graph maturity; without it, the option may look rigorous while staying incomplete. |

## 8. Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Potentially excellent because proposal-annex relations and grouping become first-class graph operations. | The graph may make provisional grouping look more settled than the requirements basis allows. |
| Scenario A | Strong for explicit regulation-to-acts-to-standards chains and reference tracing. | Weakly linked national or project material may remain coarse and reduce completeness. |
| Scenario B | Plausible but only medium-strength for V1 because jurisdiction encoding helps, yet Germany handling may stay thin unless national materials are normalized more deeply. | National nuance may lag behind EU-level modeling. |
| Scenario C | Good if standards sections and role relationships are normalized well enough. | Final explanation still depends on text interpretation quality rather than graph structure alone. |
| High-risk failure pattern | Strong in principle because absent required link types could reveal missing higher-ranked support. | Hidden graph incompleteness can itself become the high-risk failure mode. |

## 9. Reviewer-perspective notes

### Traceability / Compliance
- Strongest theoretical provenance model in the set because source role and jurisdiction are first-class graph elements.
- Main compliance risk shifts from answer composition to graph construction quality and invisible missing links.

### System / Data / Performance
- Highest data-model and maintenance burden among the serious non-orchestrated options.
- Strong dependence on provision segmentation, citation extraction, and graph integrity over time.

### Research Workflow / User Value
- Could reduce manual source-landscape reconstruction dramatically on relationship-heavy questions once structurally mature.
- Early V1 user value may be delayed if too much effort is spent on ingest and normalization before the graph becomes dependable.
