# External Review Batch Files

Status: ready for reviewer use
Purpose: prevent reviewer collisions while keeping reviews comparable across all options

## 1. Review ownership rule

- Each external reviewer must review all four frozen option plans.
- Each external reviewer must write to exactly one reviewer-owned batch file in this directory.
- No two reviewers may share or overwrite the same batch file.

Recommended naming:
- `reviewer-1.md`
- `reviewer-2.md`
- `reviewer-3.md`

If you already know the reviewer identity, use a clearer name such as:
- `compliance-reviewer.md`
- `systems-reviewer.md`
- `workflow-reviewer.md`

## 2. Required inputs for every reviewer

- [../MASTERPLAN.md](../MASTERPLAN.md)
- [../REVIEW_RUBRIC.md](../REVIEW_RUBRIC.md)
- [../REQUIREMENTS_PATCHES.md](../REQUIREMENTS_PATCHES.md)
- [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../options/option-a/PLAN.md](../options/option-a/PLAN.md)
- [../options/option-b/PLAN.md](../options/option-b/PLAN.md)
- [../options/option-c/PLAN.md](../options/option-c/PLAN.md)
- [../options/baseline/PLAN.md](../options/baseline/PLAN.md)

## 3. Output rule

- Use [TEMPLATE_ALL_OPTIONS.md](./TEMPLATE_ALL_OPTIONS.md) as the starting structure.
- Review all four options in the same file.
- Keep supported findings, judgment calls, and unresolved uncertainties separate.
- If a potential requirements patch is discovered, do not edit `REQUIREMENTS_PATCHES.md`; record it in the batch review using the label `Potential requirements patch:`.

## 4. What happens next

- After the raw external review wave is complete, the Architecture Facilitator consolidates the reviewer batch files into the per-option review syntheses under `docs/architecture/options/*/REVIEW.md`.
- Only after that consolidation step should [../OPTIONS_COMPARISON.md](../OPTIONS_COMPARISON.md) be completed.
