# V2 Plan Delta Review: Verification Quality

## 1. Prior blocker status

- Quality gate not yet a real quality gate: **still open**. The revised plan materially improves the gate by adding explicit real-corpus pass criteria, a corpus coverage prerequisite, and a defined `manual_review_report.md` content standard. But the gate still does not require the reviewed runs to be accepted. In section 4, V2 acceptance requires that two manual review bundles be "fully reviewed," not that either review's final judgment is `accept`. That means the plan still allows V2 to pass even if both substantive human reviews conclude the outputs are not reusable.
- Main migration point from the current baseline was understated: **not re-reviewed here**. This delta review is limited to whether the revised plan now defines a real verification-quality gate.
- Official discovery governance was too coarse: **not re-reviewed here except where it affects gate proof**. For gate purposes, the fetched-document admission contract and coverage/reporting requirements are now substantially sharper.

## 2. New findings

### F1. Manual review is now substantive, but it is still not a binding pass condition

**Severity: blocker**

This is the remaining gate failure. The plan now requires `manual_review_report.md` to capture correctness, usefulness, hierarchy, uncertainty handling, discovery/gap handling, open follow-ups, and a final accept/reject judgment. That is good proof material. But section 4 only requires that the bundles be "fully reviewed." It never says the final judgment for those reviewed runs must be `accept`, nor that correctness/usefulness must be positive enough to count as a pass.

As written, the gate can still pass with:
- tests green
- fixture eval 5/5
- real-corpus eval 5/5
- coverage report present and passing
- two human review reports that explicitly reject the runs

That is still a documentation gate with stronger artifacts, not yet a true quality gate.

### F2. Real-corpus pass criteria are much better, but one term is still weaker than the rest

**Severity: important**

The real-corpus pass definition is now materially stronger. It explicitly requires:
- no blocked claim in `final_answer.txt`
- visible `confirmed` / `interpretive` / `open` handling where applicable
- governing-support presence or explicit gap explanation
- fetched-source admission compliance

That closes most of the original blocker. The weak point is the clause that the answer must be "reviewable and source-bound." That is directionally right, but it is less falsifiable than the rest of the pass contract unless the manual review judgment is made binding. On its own, this wording is too soft to carry acceptance weight.

### F3. Corpus coverage proof is now adequate for a gate input

**Severity: closed**

The revised plan now defines a real catalog-level proof artifact: `corpus_coverage_report.json`, tied to the selected corpus state and required to show admitted counts, admitted source ids by family, and missing-coverage flags. It is also placed ahead of scenario verdict interpretation. That is enough to establish coverage as a gate prerequisite rather than an assumption.

### F4. Artifact-bundle clarity is improved but still slightly ambiguous

**Severity: minor**

The plan is clearer than before about baseline versus conditional artifacts, but it still leaves some avoidable ambiguity around review artifacts:
- section 2 says V2 acceptance requires a filled manual review artifact
- section 3 says `manual_review_report.md` is conditional for "formal manual review samples"
- section 4 makes those formal samples part of the gate

This is understandable after careful reading, but the acceptance bundle would be clearer if the plan stated plainly that `manual_review_report.md` is mandatory for the two named gate samples and not part of every scenario bundle.

## 3. Short verdict

The revised V2 plan is much closer to a real quality gate. The real-corpus pass criteria now have real substance, the corpus coverage proof is strong enough, and the manual review artifact is no longer just a placeholder. The remaining blocker is narrow but important: the gate still requires human review to happen, not human review to pass. Until acceptance is explicitly tied to positive review judgment on the sampled runs, the plan is not yet a fully binding verification-quality gate.

`ready with revisions`
