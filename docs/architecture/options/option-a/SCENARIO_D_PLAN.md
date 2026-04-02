# Option A Scenario D Closeout Plan

Status: final closeout work order for the currently selected Option A scope
Architecture basis:
- [PLAN.md](./PLAN.md)
- [V2_PLAN.md](./V2_PLAN.md)
- [V2_1_PLAN.md](./V2_1_PLAN.md)
- [V2_2_PLAN.md](./V2_2_PLAN.md)
- [HARDENING_NOTES.md](./HARDENING_NOTES.md)

Purpose: close Option A with one explicit final proof case and make all remaining later work either tracked or explicitly excluded

## 1. Objective

Option A is already implemented through V2.2.
The remaining closeout task is not a new architecture phase.
It is a final regression-and-proof step centered on the certificate-topology anchor question.

Scenario D is the closing proof case because it exercises the most recently improved product qualities together:
- source-rank-aware synthesis
- facet coverage
- pinpoint traceability
- answer-to-evidence alignment
- blind validation without inherited analyst context

Once Scenario D is fully locked as a maintained regression and review case, Option A can be treated as complete for the currently accepted scope.

## 2. Anchor question

Scenario D remains anchored to this question:

> Gibt es abgeleitete Access bzw. Registration Certificates? Also kann eine Wallet-Relying-Party mehrere solcher Zertifikate besitzen oder gibt es nur Hauptzertifikat fuer die Ganze Organisation?

Normalized English reading:

> Are there derived access or registration certificates for wallet-relying parties? Can one wallet-relying party hold multiple such certificates, or is there only one organisation-level certificate?

## 3. Existing implementation basis

The implementation already contains a real-corpus Scenario D path under:
- `scenario_d_certificate_topology_anchor`

This plan intentionally keeps that existing scenario id rather than renaming it again.
The goal is closeout and regression stability, not nomenclature churn.

## 4. Required closeout work

### A. Lock Scenario D as the final Option A proof case

Scenario D must be treated as a maintained regression and manual-review anchor, not just an incidental test.

Required:
- the scenario stays present in the real-corpus evaluation suite
- its expected intent remains `certificate_topology_analysis`
- its acceptance criteria are kept aligned with the implemented V2.1/V2.2 trust model
- future changes to topology answering must preserve this scenario unless there is an explicit replacement decision

### B. Make the required proof surface explicit

For Scenario D, the run must produce and preserve at least:
- `final_answer.txt`
- `approved_ledger.json`
- `gap_records.json`
- `facet_coverage.json`
- `pinpoint_evidence.json`
- `answer_alignment.json`
- `blind_validation_report.json`
- `manual_review_report.md`

Scenario D is only useful as a closeout proof if these artifacts are treated as a single reviewable bundle.

### C. Keep the answer contract explicit

The Scenario D output must keep these distinctions visible:
- `derived certificate` is not explicitly defined in governing EU material
- role and coupling statements that are directly grounded in governing material remain clearly marked as such
- multiplicity and intended-use scoping are separated from governing statements when they depend on interpretive or medium-rank support
- the answer must not overclaim that the EU legal text itself states a strict `one` or `many` rule if that rule is not explicitly expressed there

### D. Require product-output-first validation

Scenario D must remain a proof that the product output is reusable on its own.

Required:
- blind validation uses a newly spawned agent
- the validating agent receives no inherited thread context
- the validating agent receives no prior analysis or expected answer
- validation passes only if the resulting answer is mainly derived from the product output and artifacts
- direct raw-document reading is allowed only for minor confirmation, not for reconstructing the main argument

### E. Record closeout status in docs

The closeout should leave a stable paper trail.

At minimum:
- Scenario D is referenced as the final Option A closeout proof case in the relevant project docs if needed
- accepted remaining limitations stay documented in `HARDENING_NOTES.md`
- later work is either tracked as an issue or explicitly excluded below

## 5. Acceptance gate

Scenario D closeout is accepted only if all of the following hold:

- the existing test suite remains green
- the existing V2 regression suite remains green
- real-corpus Scenario D passes
- the Scenario D artifact bundle is complete
- `facet_coverage.json` covers the topology question facets materially enough to support the final answer
- `pinpoint_evidence.json` gives reviewer-usable source jumps
- `answer_alignment.json` shows no wording-to-evidence role mismatch
- `blind_validation_report.json` records a pass, with any raw-document reads classified only as minor confirmation
- `manual_review_report.md` ends with acceptance, not merely structural completeness

If these conditions hold, Option A is considered complete for the currently accepted scope.

## 6. Deferred follow-up items

These are intentionally not part of Scenario D closeout, but they are tracked for later work:

- Freshness automation:
  - GitHub issue [#2](https://github.com/RicardoBochnia/EUBW-Researcher/issues/2)
- Germany beyond best-effort support:
  - GitHub issue [#3](https://github.com/RicardoBochnia/EUBW-Researcher/issues/3)
- Broader official web discovery beyond the current conservative path:
  - GitHub issue [#4](https://github.com/RicardoBochnia/EUBW-Researcher/issues/4)

## 7. Explicit exclusions for now

These are not currently planned follow-up items and are explicitly outside the accepted Option A scope unless a later architecture decision reopens them:

- persistent graph storage / provenance graph persistence
- unrestricted open-web search
- separate UI work
- product-side multi-agent orchestration
- broad multi-member-state coverage beyond the current bounded approach

## 8. Final decision rule

After Scenario D closeout, later work should only proceed through:
- a tracked follow-up issue, or
- an explicit new architecture/version work order

This prevents Option A from drifting through untracked “small” additions after formal completion.
