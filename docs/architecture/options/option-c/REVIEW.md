# Option C Review

Status: consolidated from external review wave
Reviewed option: option-c

## 1. Reviewed inputs

- PLAN used: [PLAN.md](./PLAN.md)
- Requirements basis used: [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Masterplan used: [../../MASTERPLAN.md](../../MASTERPLAN.md)
- Requirements patches used: [../../REQUIREMENTS_PATCHES.md](../../REQUIREMENTS_PATCHES.md) (no decided patches at initial handoff)

Consolidation note: this file summarizes the raw batch reviews in [../../reviews/reviewer-1.md](../../reviews/reviewer-1.md), [../../reviews/reviewer-2.md](../../reviews/reviewer-2.md), [../../reviews/reviewer-3.md](../../reviews/reviewer-3.md), and [../../reviews/reviewer-4.md](../../reviews/reviewer-4.md).

## 2. Summary verdict

- Overall verdict: `Flexible but operationally risky for V1`
- Short rationale: `Reviewers agreed that Option C is the most naturally aligned with ambiguity-heavy mixed-source questions and future extensibility, but also the most operationally complex and hardest to audit. Its V1 challenge is not capability coverage but whether decomposition, specialist drift, and adjudication opacity create more control burden than the requirements basis actually needs.`

## 3. Supported findings

- The plan defines a concrete path from query decomposition through specialist investigation, shared evidence, adjudication, and final synthesis.
- It explicitly distinguishes regulatory, standards, and implementation/web work rather than flattening all sources into one search space.
- The curated corpus remains first search space, and web expansion is constrained to a specialist role rather than unconstrained browsing.
- Source-role enforcement and conflict handling are central responsibilities of the adjudicator.
- The plan openly acknowledges high latency, high operating cost, high maintenance burden, and specialist drift as core V1 risks.

## 4. Judgment calls

- This option is probably strongest on the hardest ambiguity-heavy questions where different source families genuinely demand different investigation styles.
- For V1, the added flexibility may not justify the control overhead unless decomposition is highly selective and the adjudicator is unusually disciplined.
- Compared with Option A, more of the trust story is pushed into orchestration quality and less into a simpler, fixed, auditable sequence.

## 5. Unresolved uncertainties

- The plan does not yet show when decomposition is triggered and when the system deliberately stays simple, which matters for cost and predictability.
- Specialist boundaries and overlap control remain under-specified, so duplicated work and drift remain real risks.
- The adjudicator is conceptually strong but not yet operationally transparent enough to show how conflicts are resolved and how those resolutions remain inspectable.
- Reproducibility across repeated runs of the same question is unclear once multiple specialists are involved.

## 6. Likely later evaluation needs

- Evaluate whether the orchestrator decomposes only when complexity justifies it, rather than by default.
- Probe for source-role drift by injecting lower-rank implementation material and checking whether adjudication consistently prevents false elevation.
- Test adjudication transparency: can a researcher understand why conflicting specialist findings were resolved in a particular way?
- Compare the quality gain on hard mixed-source questions against the added latency and token cost relative to Option A.

## 7. Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Meets | `PLAN Sections 1, 4, 5` | Synthesis quality depends strongly on adjudication quality. |
| R2 | Meets | `PLAN Sections 3, 4, 5, 7` | Coverage breadth is strong, but discipline of the decomposition path remains a practical concern. |
| R3 | Meets | `PLAN Sections 5, 7, 8, 10` | Multiple specialists create more opportunities for source-role drift before adjudication. |
| R4 | Meets with caveat | `PLAN Sections 4, 5, 10` | The safeguard depends on the strictness and transparency of the shared ledger and adjudicator. |
| R5 | Meets with caveat | `PLAN Sections 7, 8` | EU-first behavior is partly conditional on orchestration discipline rather than guaranteed by a fixed path. |
| R6 | Meets | `PLAN Sections 8, 9` | None material beyond high cost and latency. |
| R7 | Meets | `PLAN Sections 4, 5, 6` | Lower-rank web material may still enter too early if orchestration or adjudication is lax. |
| R8 | Meets with caveat | `PLAN Sections 7, 8, 9, 10` | Practical usefulness may be undermined if the architecture over-investigates ordinary prompts. |

## 8. Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Good coverage: specialists can extract proposal, annex, and supporting material and produce a provisional grouped answer. | Grouping consistency depends on adjudication and synthesis discipline rather than one stable structural model. |
| Scenario A | Very good fit because the question naturally spans regulation, standards, and implementation material. | The design may over-investigate even when a simpler ranked pipeline would be enough. |
| Scenario B | Plausible but only borderline for V1: EU-first plus Germany extension is conceptually supported. | Lower-rank implementation material may enter too early unless the adjudicator is strict. |
| Scenario C | Good fit through a standards specialist and section-level justification. | The full orchestrator may be overkill for narrow technical questions. |
| High-risk failure pattern | Better than the baseline because multiple specialists can cross-check before synthesis. | Poor decomposition can still miss the governing source while creating an impression of thoroughness. |

## 9. Reviewer-perspective notes

### Traceability / Compliance
- The shared ledger and adjudicator are the right conceptual control points, but they are also the main trust bottleneck.
- Compared with Option A, more of the traceability burden sits in coordination discipline and less in a simpler auditable sequence.

### System / Data / Performance
- Highest likely token, orchestration, and maintenance burden in the set.
- Greatest risk of duplicated work, tool drift, and non-deterministic behavior unless specialist boundaries are very tightly controlled.

### Research Workflow / User Value
- Potentially very valuable on the hardest mixed regulatory and technical questions.
- Likely less efficient on ordinary V1 prompts than the plan suggests, which weakens its near-term fit despite strong long-term extensibility.
