# Option A V2.2 Plan

Status: targeted work order after V2.1
Selected architecture basis: [PLAN.md](./PLAN.md)
Current implementation baseline:
- [V2_PLAN.md](./V2_PLAN.md)
- [V2_1_PLAN.md](./V2_1_PLAN.md)
- [HARDENING_NOTES.md](./HARDENING_NOTES.md)
- [REVIEW_GUIDE.md](./REVIEW_GUIDE.md)

Purpose: close the remaining trust-and-traceability gap after V2.1 without reopening the architecture

## 1. Objective

Option A V2.2 is a narrow trust-hardening release.
It does not change the architecture, the source-governance model, or the accepted Option A answer-policy model.

V2.2 exists because V2.1 materially improved the product answer for certificate-topology questions, but the product output is still not self-sufficient enough for a fresh validating agent to rely on it without meaningful raw-document rereading.

The target is therefore not broader reasoning.
The target is:
- stronger pinpoint evidence
- stricter answer-to-evidence alignment
- more trustworthy review artifacts
- a tighter blind-validation gate

## 2. Anchor validation question

The primary anchor question remains:

> Gibt es abgeleitete Access bzw. Registration Certificates? Also kann eine Wallet-Relying-Party mehrere solcher Zertifikate besitzen oder gibt es nur Hauptzertifikat fuer die Ganze Organisation?

Normalized English reading for implementation and eval design:

> Are there derived access or registration certificates for wallet-relying parties? Can one wallet-relying party hold multiple such certificates, or is there only one organisation-level certificate?

V2.2 is successful only if the product output for this question is strong enough that a fresh validating agent can answer mainly from the generated product artifacts rather than reconstructing the core reasoning from raw source documents.

## 3. Current post-V2.1 gap

After V2.1, the system now does the important reasoning work:
- it identifies that `derived certificate` is not explicitly defined in governing EU sources
- it separates governing role statements from broader multiplicity interpretation
- it uses medium-rank project artifacts to make the broader interpretation more explicit
- it produces `facet_coverage.json`

The remaining gap is narrower:
- the product output still benefits from direct raw-document confirmation because pinpoint evidence is not yet strong enough
- answer wording and evidence-role framing can still drift out of perfect alignment
- the current direct-run review output is still too generic to prove that the answer is reusable without outside reconstruction

This is a trust and inspectability gap, not a reasoning-gap or architecture-gap.

## 4. Required V2.2 changes

### A. Pinpoint-citation hardening

The product must move from broad document-level evidence toward reviewer-usable pinpoint evidence.

Required:
- every approved citation used in the final answer must carry a reviewer-usable pinpoint anchor
- if provision-level, section-level, or line-near pinpointing is available, it must be surfaced in the product artifacts
- if exact pinpointing is not available, the artifact must say so explicitly rather than implying stronger precision than exists

V2.2 must emit a dedicated pinpoint artifact:
- `pinpoint_evidence.json`

This avoids relying on implicit or informal ledger interpretation.

At minimum, `pinpoint_evidence.json` must map:
- answer claim or claim id
- cited source id
- source role level
- pinpoint locator type
- pinpoint locator value
- whether the locator is exact, provision-level, section-level, or approximate
- any explicit limitation note if exact pinpointing is not available

Minimum acceptance requirement:
- a reviewer or validating agent must be able to jump from an answer claim to a concrete local source location without broad manual hunting

### B. Claim-to-evidence alignment hardening

The answer layer must not mix claim framing and evidence role loosely.

For V2.2, all of the following must hold:
- no answer bullet may describe support as coming from `official project artifacts` while citing only governing EU material
- no answer bullet may describe a claim as governing if the supporting evidence is only medium-rank
- no answer bullet may suppress an `interpretive` or `open` status while relying on indirect or non-governing support
- answer wording, claim-state, and citation-role must remain aligned

V2.2 must add a structural alignment artifact:
- `answer_alignment.json`

At minimum, the structural check must verify:
- the wording category used in the answer
- the claim-state in the ledger
- the source-role level of the cited evidence
- whether the answer-language correctly reflects governing / interpretive / medium-rank / unresolved status

`answer_alignment.json` must be produced in a reproducible way and be structurally verifiable by tests or eval checks.
For V2.2, this artifact must be emitted from structural answer-generation metadata rather than post-hoc free-text interpretation.

For multi-source claims, alignment must follow this rule:
- if one answer bullet mixes governing and medium-rank support, the wording must either
  - explicitly partition the support by source role, or
  - stay at the strongest support level that is actually justified without silently inheriting broader confidence from lower-rank sources
- no mixed-source answer bullet may appear as purely governing if part of its reasoning depends on medium-rank support

### C. Product-output-first validation contract

V2.2 must tighten the V2.1 blind-validation rule into a stronger operational gate.

The fresh validation subagent must still:
- be newly spawned
- receive no inherited thread context
- not receive prior analysis, expected answer, or suggested sources
- not receive implementation hints beyond using the repository's runtime path and instructions

But the pass rule is now stricter.

Blind validation passes only if:
- the validating subagent's answer is primarily derived from `final_answer.txt` plus the run artifacts
- direct raw-document reads are limited to minor spot-check confirmation
- the validating subagent does not need to reconstruct a central reasoning step from raw sources

Blind validation fails if:
- the validating subagent must discover the main argument by reading source documents directly
- the product output omits a central answer facet and the validator has to rebuild it manually
- the validating subagent's final answer materially depends on information not present in or reasonably derivable from the generated product artifacts

The implementing developer agent must record this validation in an inspectable way.
At minimum, record:
- which artifacts the validating subagent used
- whether any raw-document reads occurred
- whether those reads were minor confirmation or central reconstruction
- whether the blind validation passed or failed

Required artifact:
- `blind_validation_report.json`

For this work order, use this lightweight heuristic for `minor confirmation` vs `central reconstruction`:
- `minor confirmation` means the validating subagent only spot-checks raw source locations that are already cited or directly discoverable from `final_answer.txt`, `facet_coverage.json`, `pinpoint_evidence.json`, or `approved_ledger.json`
- `central reconstruction` means the validating subagent has to discover a concept, source relationship, or answer facet that is not already present in those product artifacts
- if a central answer facet is absent from product artifacts and only appears after raw-document reading, blind validation fails

### D. Review-surface trust upgrade

The direct-run review output must become more honest and more useful for this question class.

Required:
- `manual_review_report.md` must reflect topology-specific trust checks, not only generic structural checks
- the direct-run review surface must say whether the answer is:
  - source-bound
  - pinpoint-traceable
  - wording-to-evidence aligned
  - reusable without raw-document reconstruction

If needed, add explicit review verdict fields such as:
- `pinpoint_traceability_verdict`
- `answer_evidence_alignment_verdict`
- `product_output_self_sufficiency_verdict`

These are trust-surface additions, not architecture changes.

### E. Optional but recommended: dedicated regression scenario

V2.2 should add a dedicated real-corpus scenario for this exact question family.

Recommended scenario id:
- `scenario_d_certificate_topology_multiplicity`

This scenario should verify at minimum:
- `certificate_topology_analysis` intent is selected
- `derived certificate` term-status is surfaced explicitly
- multiplicity / intended-use / service-scope interpretation is addressed
- governing vs medium-rank support is separated correctly
- `facet_coverage.json` is complete
- no answer-evidence alignment violation occurs
- the answer does not overclaim multiplicity as governing EU law

This scenario is optional in the sense that V2.2 can still be implemented without broadening the full scenario suite first.
However, if implementation cost stays small, it should be added and folded into the real-corpus regression gate.

## 5. Verification and validation

### Automated additions

V2.2 must add, at minimum:
- one unit or integration check for stronger pinpoint evidence generation on the anchor question path
- one structural check for answer-to-evidence alignment on the anchor question path
- one verification path for blind-validation recording artifacts

If the optional scenario is added, it becomes part of the automated regression suite.

### Direct-run validation

For the anchor question, the direct-run output must now be strong enough that:
- a reviewer can inspect the answer without broad source hunting
- a validating agent can follow the answer back to concrete evidence locations
- the product output is self-sufficient enough to support a research-grade first answer

### Required artifacts

The anchor-question run must continue to emit the V2 / V2.1 artifacts and additionally emit any new trust-hardening artifacts introduced in this version.

At minimum, V2.2 must preserve:
- `final_answer.txt`
- `approved_ledger.json`
- `gap_records.json`
- `manual_review_report.md`
- `facet_coverage.json`

And must add one or more inspectable trust artifacts for:
- pinpoint evidence
- answer-evidence alignment
- blind-validation result

For V2.2, these required trust artifacts are:
- `pinpoint_evidence.json`
- `answer_alignment.json`
- `blind_validation_report.json`

## 6. V2.2 acceptance gate

V2.2 is only accepted if all of the following are true:
- the V2 regression gates remain green
- the V2.1 topology behavior remains green
- the anchor question output contains reviewer-usable pinpoint evidence
- answer wording stays aligned with source role and claim-state
- no topology answer bullet shows mismatched evidence framing
- the direct-run review surface exposes trust-level judgments beyond generic structural checks
- `pinpoint_evidence.json` exists and passes structural verification
- `answer_alignment.json` exists and shows no blocking alignment violation
- `blind_validation_report.json` exists and records a passing product-output-first validation
- a fresh no-context validating subagent can answer mainly from the product artifacts
- if raw-document checks still occur, they are minor confirmation only
- if `scenario_d_certificate_topology_multiplicity` is added, it passes on the real corpus

For this work order, `reviewer-usable pinpoint evidence` means:
- a reviewer can move from answer claim to concrete local source position with minimal manual navigation
- the artifact does not pretend to exactness it does not have

For this work order, `aligned wording` means:
- governing claims are backed by governing evidence
- medium-rank explanations are labeled as such
- unresolved or only-interpretive conclusions remain visible as unresolved or interpretive

## 7. Boundaries

V2.2 remains narrow.
It does not introduce:
- architecture changes
- open-web search
- UI work
- graph persistence
- broad corpus expansion
- generalized agent orchestration inside the product

This is a trust-and-traceability hardening release, not a new product phase.

## 8. Defaults

- Architecture remains Option A.
- The anchor question remains the primary proof case.
- The optional dedicated regression scenario should be included if implementation cost stays small.
- If a tradeoff appears, reviewer-traceable evidence and wording correctness win over answer polish.
