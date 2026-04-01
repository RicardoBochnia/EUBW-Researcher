# Option A V2.1 Plan Review

Status: completed
Reviewer: v2_1-reviewer-1
Date: 2026-04-01
Review target: [V2_1_PLAN.md](../V2_1_PLAN.md)

## 1. Required inputs

- [../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../PLAN.md](../PLAN.md)
- [../V2_PLAN.md](../V2_PLAN.md)
- [../V2_1_PLAN.md](../V2_1_PLAN.md)
- [../HARDENING_NOTES.md](../HARDENING_NOTES.md)
- [../REVIEW_GUIDE.md](../REVIEW_GUIDE.md)
- [../MANUAL_REVIEW_CHECKLIST.md](../MANUAL_REVIEW_CHECKLIST.md)
- [./v2-reviewer-1.md](./v2-reviewer-1.md) (V2 plan review for baseline context)

## 2. Review goal

Assess whether V2_1_PLAN.md is a well-scoped, concrete, and architecture-faithful work order that closes the identified usefulness gap without (a) reopening architecture choices, (b) drifting beyond the stated narrow target, or (c) introducing obligations that conflict with the accepted V2 baseline or the requirements basis.

## 3. Findings

### P1 / blocker

- None found.

### P2 / important

- **The blind validation subagent contract is operationally underspecified.** Section 5 requires a "new subagent" that is created "without inherited thread context" and receives only the repository, the anchor question, and a minimal instruction to use the product's own runtime path. This is the right idea — it directly tests the product-path usefulness claim. However, the plan does not define what "materially more useful" looks like from the validating subagent's perspective, nor what constitutes "substantial direct document research." Without an explicit pass/fail criterion for the validation pass, the developer agent has full discretion to judge its own work. Suggested fix: define at minimum that the validating subagent must produce its answer primarily from the product's `final_answer.txt` and supporting artifacts, and that if the subagent's answer relies on information not present in or derivable from the product output, the validation fails.

- **Intent-specific review checks (section 4D) lack a minimal structural contract.** The plan says intent-specific review checks "can be implemented through intent-specific review checks, expected answer facets, or equivalent artifact-level coverage checks." This breadth of implementation options is appropriate for a plan document, but the acceptance gate (section 6) then requires that the review surface prevent effectively positive reviews when central facets are ignored. Without specifying what artifact the facet checks produce or how they integrate into the existing `manual_review.json` / `manual_review_report.md` pipeline, there is a risk that this requirement is satisfied by informal inspection rather than a reproducible automated check. Suggested fix: require that the facet coverage checks either (a) produce named fields in the existing `manual_review.json` prefill, or (b) emit a separate `facet_coverage.json` artifact that the eval gate can verify structurally.

### P3 / minor

- **The "not explicitly defined" answer pattern (section 4E) could benefit from a structural template.** The plan describes the desired answer shape in prose — four bullet points showing what a good answer for this question class looks like. This is clear enough to implement against, but it does not define whether this becomes a reusable answer pattern for other undefined-term questions in the future, or whether it is a one-off shaping for the anchor question only. If it is intended as a reusable pattern, naming it and defining its structural contract now would prevent ad-hoc reimplementation later. If it is anchor-specific, saying so explicitly would prevent scope creep during implementation.

- **Corpus expansion rule (section 4C) is appropriately narrow but the admission rationale is implicit.** The plan says to review and likely include `SRC-W-TEC-64_discussion_topic_x_rp_registration.html`, and states clear constraints (remains `project_artifact`, remains `medium`, must not override governing material). This is well-disciplined. However, the plan does not require that the admission rationale be recorded in any inspectable artifact. Since V2 already requires `corpus_coverage_report.json` to document admitted source coverage, adding a brief admission-reason field for V2.1-added sources would maintain the corpus curation audit trail without meaningful effort.

- **Regression protection is stated but not structurally tightened.** Section 6 requires "the V2 regression gates remain green," which is the right baseline protection. But V2.1 introduces a new dedicated intent path (`certificate_topology_analysis`) that necessarily changes analyzer routing. If an existing V2 scenario formerly routed through the coarse `certificate_layer_analysis` path for a related question, the new dedicated path could change that routing. The plan should state explicitly whether existing V2 scenario routing must remain stable, or whether re-routing through the new path is acceptable as long as the V2 scenario verdicts remain green.

## 4. Summary verdict

- Overall verdict: `ready with minor revisions`
- Short rationale: V2.1 is an unusually well-disciplined incremental work order. It correctly identifies a specific usefulness gap, traces it to concrete implementation shortcomings (coarse analyzer routing, missing corpus material, and review-surface weakness), and proposes targeted fixes without reopening the architecture. The anchor question is explicit and the acceptance gate is concrete. The two P2 items — underspecified blind-validation pass/fail and unstructured facet-coverage checks — do not block implementation, but must be resolved before the acceptance gate can function as a real quality check rather than a procedural formality.

## 5. What the V2.1 plan gets right

- **The failure diagnosis (section 3) is concrete, specific, and honest.** It identifies exactly three failure modes in the current V2 on the anchor question, and correctly classifies them as usefulness gaps rather than architecture failures. This prevents the work order from being used to justify architecture changes.
- **The anchor question is explicit and in the original language.** This eliminates ambiguity about what question shape is being targeted and prevents the implementation from optimizing for a sanitized English paraphrase rather than the real research question.
- **Source-role separation (section 4B) is correctly scoped as a required capability.** The plan does not merely ask for better wording; it specifies four distinct evidential tiers (governing direct support, governing interpretive, medium-rank project artifacts, not explicitly defined) and requires the answer to distinguish them. This directly implements requirements basis §7 (source-role and evidence rules) without overgeneralizing.
- **Corpus expansion (section 4C) is maximally narrow.** One specific already-archived source, with explicit rank constraints and an explicit prohibition on override. This is exactly the discipline needed to prevent "just add more sources" scope creep.
- **The blind validation mechanism (section 5) is the right verification concept.** Spawning a fresh subagent without inherited context is a genuine product-path usability test, not a confirmation ritual. The concept is more rigorous than typical plan-level verification requirements.
- **Boundaries (section 7) are explicit and protective.** No open-web search, no graph persistence, no UI work, no multi-agent orchestration, no broad corpus expansion. Every known V2 scope boundary is reaffirmed.
- **The acceptance gate (section 6) is falsifiable.** Eight concrete conditions, each testable. This is materially stronger than a subjective "V2.1 is good enough" judgment.
- **The plan correctly preserves V2 infrastructure.** The new intent, review checks, and corpus entry integrate into the existing V2 artifact bundle, eval pipeline, and review surface rather than introducing parallel infrastructure.

## 6. Missing decisions or ambiguities

- **Blind-validation pass/fail criterion.** What specifically must the validating subagent produce, and what constitutes failure? See P2 finding above.
- **Facet-coverage check artifact.** How do the intent-specific review checks integrate into the automated review pipeline? See P2 finding above.
- **Answer-pattern reusability scope.** Is the "not explicitly defined" pattern a reusable answer template or an anchor-specific shaping? See P3 finding above.
- **Admission-reason recording for corpus additions.** Should V2.1 corpus additions carry an inspectable admission rationale? See P3 finding above.
- **V2 scenario routing stability.** Is re-routing through `certificate_topology_analysis` acceptable for existing V2 scenarios? See P3 finding above.

## 7. Scope or architecture drift risks

- **Very low risk overall.** This is one of the most scope-disciplined incremental plans in the review history of this project.
- **The dedicated intent path is the only structural change to the analyzer.** Adding `certificate_topology_analysis` is a net addition, not a refactor of the V2 generalized analyzer. As long as existing V2 intents are not removed or renamed, routing drift risk is minimal.
- **No architecture drift detected.** The plan does not reintroduce persistent graphs, open-web search, multi-agent orchestration, UI, or any other V2 non-goal. It does not extend the source hierarchy, the web expansion policy, or the discovery bounds. It operates entirely within the accepted V2 architecture envelope.
- **The blind-validation concept is novel process, not novel architecture.** It adds a verification obligation, not a runtime component. No architectural surface area increase.

## 8. Requirements basis alignment check

| Requirements basis item | V2.1 alignment | Notes |
| --- | --- | --- |
| §2 Primary success scenario | Not directly targeted | V2.1 targets a different question family; no regression risk to §2 |
| §3 Scenario A (registration/access cert) | Directly targeted | The anchor question is a specialization within Scenario A's question family |
| §5 Must-have #3 (make uncertainty visible) | Directly advanced | Section 4B and 4E require explicit uncertainty surfacing for this question class |
| §6 Non-negotiable (no unsupported core claims) | Preserved | Section 4B prohibits presenting medium-rank material as governing law |
| §7 Source-role rules | Directly advanced | Four-tier evidential distinction in section 4B directly implements §7 |
| §8 Source hierarchy | Preserved | New corpus entry stays `medium`; governing material cannot be overridden |
| §9 Web expansion policy | Preserved | Section 7 explicitly excludes open-web search |
| §10 Scope boundaries | Preserved | No member-state expansion, no architecture redesign |

## 9. Recommended changes before approval

1. **Define a concrete pass/fail criterion for the blind validation** (P2). At minimum: the validating subagent's answer must be primarily derivable from the product's `final_answer.txt` and run artifacts; if the subagent must perform substantial direct-source research outside the product output to address a central facet, the validation fails.
2. **Specify how facet-coverage checks integrate into the review pipeline** (P2). Either add named facet-coverage fields to the existing `manual_review.json` schema, or require a separate `facet_coverage.json` artifact that the eval gate can structurally verify.
3. **State whether the "not explicitly defined" answer pattern is reusable or anchor-specific** (P3). One sentence is sufficient.
4. **Require an inspectable admission rationale for V2.1 corpus additions** (P3). A brief `admission_reason` field in the corpus selection config or coverage report.
5. **Clarify V2 scenario routing stability** (P3). State whether existing V2 scenarios may be re-routed through the new `certificate_topology_analysis` intent, or whether only new scenarios use it.

## 10. Gate recommendation

- Can implementation start after this review? `yes, after P2 items are addressed`
- The P2 items do not require rethinking the plan; they require two concrete additions (validation pass/fail criterion and facet-check artifact contract) that can be resolved in a plan revision within minutes.
- All P3 items are implementation-time decisions that do not block the start of coding.
