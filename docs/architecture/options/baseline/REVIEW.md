# Baseline Review

Status: consolidated from external review wave
Reviewed option: baseline

## 1. Reviewed inputs

- PLAN used: [PLAN.md](./PLAN.md)
- Requirements basis used: [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Masterplan used: [../../MASTERPLAN.md](../../MASTERPLAN.md)
- Requirements patches used: [../../REQUIREMENTS_PATCHES.md](../../REQUIREMENTS_PATCHES.md) (no decided patches at initial handoff)

Consolidation note: this file summarizes the raw batch reviews in [../../reviews/reviewer-1.md](../../reviews/reviewer-1.md), [../../reviews/reviewer-2.md](../../reviews/reviewer-2.md), [../../reviews/reviewer-3.md](../../reviews/reviewer-3.md), and [../../reviews/reviewer-4.md](../../reviews/reviewer-4.md).

## 2. Summary verdict

- Overall verdict: `Credible control, weak target V1`
- Short rationale: `All reviewers treated the baseline as a legitimate control option and not a disguised full architecture. They also agreed that it is materially weaker than the serious options on source-role fidelity, conflict handling, and protection against unsupported core claims, which makes it unsuitable as the preferred V1 target.`

## 3. Supported findings

- The baseline defines a real retrieval-to-synthesis path and is therefore a credible answering architecture rather than retrieval-only tooling.
- The curated corpus remains primary, and web fallback is narrow and limited to acceptable official domains.
- The plan honestly describes conflict handling as shallow and source-role control as weaker than in the serious options.
- The baseline clearly explains why it is a baseline and why it is not a disguised full option.
- Reviewers consistently agreed that its main value is as a comparison floor that keeps the core failure mode visible.

## 4. Judgment calls

- This is the right control option because it shows what a minimal credible architecture can do without heavy governance machinery.
- It may perform surprisingly well on narrow direct questions, but that does not rescue it as the main V1 direction because the requirements basis is shaped around avoiding under-supported synthesis on harder cross-layer questions.
- Choosing it as the primary target would amount to underreacting to the stated pain points and the non-negotiable quality bar.

## 5. Unresolved uncertainties

- The plan does not define how retrieval weakness is detected before web fallback or answer generation.
- It is unclear how often light source-rank filtering is enough to stop false elevation of medium- or low-rank sources.
- Post-hoc citation packaging is too lightly specified to judge how trustworthy anchor-level support would be.
- The baseline assumes the curated corpus is rich enough that simple retrieval is not immediately disqualifying, but that assumption remains untested.

## 6. Likely later evaluation needs

- Side-by-side benchmarking against Option A on higher-risk cross-layer questions.
- Measurement of false-elevation frequency and plausible-but-under-supported answers.
- Comparison of post-hoc citation accuracy and source-role fidelity against the more governed options.
- Testing whether the baseline materially reduces manual source reconstruction on multi-layer questions or mainly helps on narrow direct lookups.

## 7. Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Partially meets | `PLAN Sections 1, 4, 5` | The synthesis path is real but shallow and lightly governed. |
| R2 | Partially meets | `PLAN Sections 3, 4, 5, 7` | Cross-layer access is opportunistic rather than systematically planned. |
| R3 | Partially meets | `PLAN Sections 5, 7, 8, 10` | Source-role fidelity and conflict exposure are both weak and retrieval-dependent. |
| R4 | Does not meet | `PLAN Sections 4, 5, 10` | No strong evidence-control layer exists to prevent plausible but wrongly supported core claims. |
| R5 | Meets | `PLAN Sections 7, 8` | Germany best-effort handling is weakly controlled. |
| R6 | Partially meets | `PLAN Sections 8, 9` | Simplicity and low latency are gained partly by removing evidence-governance steps the requirements basis treats as important. |
| R7 | Meets | `PLAN Sections 4, 5, 6` | Fallback trigger and evidence governance after web expansion remain under-specified. |
| R8 | Meets | `PLAN Sections 7, 8, 9, 10` | Reviewability does not change the fact that the option remains weak on the core failure mode. |

## 8. Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Weak to partial: can retrieve proposal and annex material and produce a first synthesis. | Provisional grouping and cross-document linking are likely shallow and unstable. |
| Scenario A | Partial: straightforward retrieval may find relevant regulation and standards material. | There is no governed mechanism for cross-layer gap-filling or ranked escalation. |
| Scenario B | Partial: EU-first answers are possible if retrieval succeeds. | Source-role distinction between EU obligations and member-state discretion is too lightly controlled. |
| Scenario C | Good as a control on narrow direct protocol questions if the right section is retrieved. | Quality drops sharply when the governing section is not in the initial retrieval set. |
| High-risk failure pattern | Weak by design, which is acceptable for a control. | This is the option most likely to emit plausible but under-supported answers while missing the governing source. |

## 9. Reviewer-perspective notes

### Traceability / Compliance
- Weakest option on the non-negotiable support-fidelity requirement because source-role control is mostly post-hoc and retrieval-driven.
- Still useful as a control because the main compliance failure remains explicit rather than hidden behind richer machinery.

### System / Data / Performance
- Lowest complexity, cost, and maintenance burden in the set.
- That simplicity is purchased by giving up much of the explicit evidence governance the serious options use to defend answer quality.

### Research Workflow / User Value
- Could help on narrower direct questions where the curated corpus already contains the obvious governing source.
- Unconvincing as the main answer to the broader workflow pain point of reconstructing multi-layer source landscapes.
