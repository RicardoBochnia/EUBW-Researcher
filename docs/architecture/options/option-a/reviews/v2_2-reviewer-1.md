# Option A V2.2 Plan Review

Status: completed
Reviewer: v2_2-reviewer-1
Date: 2026-04-02
Review target: [V2_2_PLAN.md](../V2_2_PLAN.md)

## 1. Required inputs

- [../PLAN.md](../PLAN.md)
- [../V2_PLAN.md](../V2_PLAN.md)
- [../V2_1_PLAN.md](../V2_1_PLAN.md)
- [../HARDENING_NOTES.md](../HARDENING_NOTES.md)
- [../REVIEW_GUIDE.md](../REVIEW_GUIDE.md)
- [../MANUAL_REVIEW_CHECKLIST.md](../MANUAL_REVIEW_CHECKLIST.md)

## 2. Review goal

Assess whether V2_2_PLAN.md is a well-scoped, concrete, and architecture-faithful work order that closes the remaining trust-and-traceability gap after V2.1 without reopening architecture choices or introducing scope creep.

## 3. Findings

### P1 / blocker

- None found.

### P2 / important

- **Pinpoint evidence and alignment check artifacts are structurally underspecified.** Sections 4A and 4B give the implementation an OR choice between enriching existing artifacts and creating new ones (`pinpoint_evidence.json`, `answer_alignment.json`). While offering design flexibility is acceptable, it risks a scenario where checks are performed informally rather than structurally. The plan should define how these checks integrate into automated verification (e.g., specific schemas or mandatory new fields in existing artifacts).
- **Blind validation recording artifact is only "suggested".** Section 4C states "Suggested artifact: blind_validation_report.json". Without structurally requiring this output, the evaluation gate cannot programmatically verify that the blind validation was performed under the strict "product-output-first" constraints. Suggested fix: mandate the artifact.

### P3 / minor

- **The boundary between "minor confirmation" and "central reconstruction" is qualitative.** Section 4C permits raw document reads for "minor confirmation" but fails the validation if they constitute "central reconstruction". While this distinction works for human reviewers, it is difficult to enforce programmatically. Providing a simple heuristic (e.g., if the validating subagent must discover a concept not present in `facet_coverage.json`, it is central reconstruction) would make this rule concrete.

## 4. Summary verdict

- Overall verdict: `ready with minor revisions`
- Short rationale: V2.2 is an exceptionally well-bounded hardening release. It accurately identifies the remaining usefulness gap—inspectability and pinpoint traceability. The anchor question remains unchanged, and the acceptance constraints are tight. The needed revisions simply ensure that the new alignment and validation checks are strictly enforced through required artifacts rather than left as informal suggestions.

## 5. What the V2.2 plan gets right

- **Diagnosis is precise:** It correctly identifies that while structural reasoning was solved in V2.1, reviewer trust through pinpoint evidence and traceability is still lacking.
- **Scope discipline:** Section 7 explicitly prohibits architecture changes, web expansion, and UI work, effectively preventing scope creep.
- **Stricter blind validation:** Tightening the validation rule so that the agent must answer primarily from the generated product artifacts is a powerful forcing function for practical completeness.
- **Artifact-first verification:** It continues to demand inspectable artifacts for every trust guarantee (e.g., alignment check, validation report), matching Option A's evidence-first philosophy.

## 6. Missing decisions or ambiguities

- **Artifact schemas for pinpointing and alignment:** Will these be new JSON files, or extensions of the current ledger? (See P2)
- **Validation report structural requirement:** Is `blind_validation_report.json` required or optional? (See P2)
- **Heuristic for Minor vs Central reads:** How is "central reconstruction" objectively defined for the validating subagent? (See P3)

## 7. Scope or architecture drift risks

- **Very low risk.** The plan is explicitly scoped as a trust-and-traceability gap closure. All changes operate exclusively at the artifact and validation layer, making no changes to fundamental retrieval mechanisms or system architecture.

## 8. Requirements basis alignment check

| Requirements basis item | V2.2 alignment | Notes |
| --- | --- | --- |
| Evidence and Traceability | Directly advanced | Pinpoint citations strictly enforce the need for rapid human verification without manual document hunting. |
| Visible Uncertainty | Directly advanced | Aligning answer wording with source role and explicit claim states prevents overclaiming and silent ranking failures. |

## 9. Recommended changes before approval

1. **Mandate the blind validation report** (P2). Change `Suggested artifact: blind_validation_report.json` to `Required artifact`.
2. **Define the structural integration for pinpointing and alignment** (P2). Either mandate the separate artifacts (`pinpoint_evidence.json`, `answer_alignment.json`) or require explicit, predictable new fields in the existing ledger and review artifacts.
3. **Provide a lightweight heuristic for minor vs central reconstruction** (P3). For example, state that if the subagent has to extract a domain concept not present in the pre-computed facet coverage, this constitutes central reconstruction and fails the gate.

## 10. Gate recommendation

- Can implementation start after this review? `yes, after P2 items are addressed`
