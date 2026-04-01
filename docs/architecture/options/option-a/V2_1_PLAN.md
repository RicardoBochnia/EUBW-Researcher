# Option A V2.1 Plan

Status: targeted work order after accepted V2
Selected architecture basis: [PLAN.md](./PLAN.md)
Current implementation baseline:
- [V2_PLAN.md](./V2_PLAN.md)
- [HARDENING_NOTES.md](./HARDENING_NOTES.md)
- [REVIEW_GUIDE.md](./REVIEW_GUIDE.md)

Purpose: close a concrete usefulness gap in the accepted Option A V2 implementation without reopening the architecture

## 1. Objective

Option A V2.1 is a narrow follow-up release.
It does not change the architecture.
It improves the system's usefulness on nuanced certificate-topology questions where the current V2 implementation under-answers and leaves too much work to the human or validating agent.

The target is not "broader intelligence" in the abstract.
The target is a more useful, more explicit, and more self-contained product answer on certificate multiplicity, intended-use scoping, and non-defined terminology.

## 2. Anchor validation question

The exact anchor question for this work order is:

> Gibt es abgeleitete Access bzw. Registration Certificates? Also kann eine Wallet-Relying-Party mehrere solcher Zertifikate besitzen oder gibt es nur Hauptzertifikat fuer die Ganze Organisation?

Normalized English reading for implementation and eval design:

> Are there derived access or registration certificates for wallet-relying parties? Can one wallet-relying party hold multiple such certificates, or is there only one organisation-level certificate?

V2.1 is successful only if the system becomes materially more useful on this exact question shape.

## 3. Current failure diagnosis

The accepted V2 implementation already helps with:
- finding relevant governing sources
- separating high-rank from medium-rank support
- producing a conservative source-bound partial answer

But for the anchor question it currently fails in three specific ways:
- the analyzer maps the question into a coarse certificate-layer path instead of decomposing the multiplicity / topology sub-questions
- the curated runtime corpus does not yet expose all useful medium-rank supporting material for this question class
- the direct-run review surface can still mark the run as acceptable even when the central facets of the question were not answered

This is therefore a usefulness and question-coverage gap, not an architecture-choice failure.

## 4. Required V2.1 changes

### A. Add a certificate-topology question path

The analyzer must recognize this question class explicitly.

V2.1 must introduce a dedicated intent for questions about:
- derived certificates
- multiple certificates vs single organisation-level certificate
- intended-use scoping
- service-scoped vs organisation-scoped certificate interpretation

Suggested intent name:
- `certificate_topology_analysis`

This path must not collapse into the existing coarse `certificate_layer_analysis` path.

The dedicated path must decompose the question into at least these answerable sub-questions:
- whether `derived certificate` is an explicit defined term in governing EU sources
- what the governing EU sources say about the role of the registration certificate
- what the governing EU sources say about the role of the access certificate
- whether intended use, service scope, or issuance/management language supports one-certificate-only or multiple-certificate interpretation
- what remains only interpretive or medium-rank supported

### B. Preserve explicit source-role separation for this question

The final answer for this question class must clearly distinguish:
- what is directly supported by governing EU sources
- what is only interpretive from governing sources
- what is additionally supported by medium-rank ARF / official project artifacts
- what remains not explicitly defined

For this question class, the system must be able to say explicitly:
- the term is not found or not defined in governing sources
- the governing text supports a narrower related conclusion
- a broader multiplicity interpretation is only medium-rank or interpretive

This is a required capability, not an optional wording preference.

### C. Expand the curated corpus for this exact gap

The runtime-selected real corpus must include the most relevant medium-rank supporting artifact for this question class if it is already present in the local archive and attributable as an official project artifact.

At minimum, review and likely include:
- `SRC-W-TEC-64_discussion_topic_x_rp_registration.html`

If admitted into the curated selection:
- it remains `project_artifact`
- it remains `medium`
- it must not be allowed to override governing EU material
- its admission rationale must be recorded in an inspectable field such as `admission_reason`
  in the corpus selection config or a derived coverage artifact

The goal is not to widen project-artifact scope broadly.
The goal is to include the single most relevant already-archived source for this question family.

### D. Improve question-facet coverage in the direct-run review surface

The current automated prefill is too structural for this class of failure.

For direct runs and evals of `certificate_topology_analysis`, the review surface must additionally check:
- whether the answer addressed the multiplicity / single-certificate facet
- whether the answer addressed the `derived certificate` term-status facet
- whether the answer exposed any unresolved or only-interpretive status explicitly

For this question class, the review pipeline must emit a structural facet-coverage artifact:
- `facet_coverage.json`

This artifact must record, at minimum:
- whether the multiplicity / single-certificate facet was addressed
- whether the `derived certificate` term-status facet was addressed
- whether the registration-certificate role facet was addressed
- whether the access-certificate role facet was addressed
- whether unresolved or only-interpretive status was exposed explicitly

This artifact is part of the automated review surface for this intent.
It must be produced in a reproducible way and be structurally verifiable by the eval or direct-run gate.

A run for this question class must not receive an effectively positive review if it ignored the central topology question.

### E. Add a direct "not explicitly defined" answer pattern

The answer composer must support a useful response shape for nuanced terminology questions.
In V2.1 this is introduced as a reusable pattern, but only for intents that explicitly opt into undefined-term handling.

For this question class, a good answer may validly be:
- no explicit governing definition of `derived certificate` was found
- governing sources support role and linkage statements for registration and access certificates
- multiplicity is only interpretively supported from intended-use / service-scoping language
- medium-rank project artifacts make that broader interpretation more explicit

This is preferable to either:
- overclaiming multiplicity as confirmed law
- or returning only a thin certificate-role statement that does not address the asked topology

## 5. Verification and validation

### Automated additions

V2.1 must add at least:
- one retrieval/analyzer unit test for the exact anchor question
- one direct-run or integration test for the anchor question
- one real-corpus eval scenario for the anchor question or an equivalent dedicated verification path

The new verification path must require that the system answer covers these facets:
- derived-term status
- registration certificate role
- access certificate role
- multiplicity / intended-use / service-scope interpretation
- explicit uncertainty or interpretive labeling where needed

### Mandatory blind validation via fresh subagent

The implementing developer agent must perform one blind validation pass after implementing V2.1.

Rules:
- the developer agent must spawn a **new** subagent for this validation
- the new subagent must be created **without inherited thread context**
- do **not** pass prior analysis, expected answer, suggested sources, or implementation details
- do **not** fork the current conversation context

The validating subagent may receive only:
- the repository workspace
- the exact anchor question
- a minimal instruction to use the repository's own runtime path and instructions

The validating subagent should then attempt to answer the anchor question from the product as a user would.

The developer agent must treat this validation as a real check, not as a confirmation ritual.
For this work order, the blind validation passes only if:
- the validating subagent's answer is primarily derivable from the product output, meaning `final_answer.txt` plus the supporting run artifacts
- the validating subagent does not need to read additional raw source documents to answer a central facet of the question
- any supplemental inspection outside the product output is minor confirmation work, not the main reasoning path

For this work order, blind validation fails if:
- the validating subagent must perform substantial direct document research outside the product output to answer a central facet
- the product output omits one of the required core facets and the subagent has to reconstruct it manually
- the subagent's final answer materially relies on information that is not present in or reasonably derivable from the generated product artifacts

## 6. V2.1 acceptance gate

V2.1 is only accepted if all of the following are true:
- the testsuite remains green
- the V2 regression gates remain green
- existing V2 scenarios may reroute through the new intent only if their configured verdicts and quality expectations remain green
- the anchor question is classified into the dedicated topology path
- the direct product run produces a materially useful answer to the anchor question
- the answer explicitly distinguishes governing support, interpretive support, and medium-rank project-artifact support where applicable
- the answer explicitly states when `derived certificate` is not defined in governing sources if that remains true
- the curated corpus selection for this question class is documented and inspectable
- `facet_coverage.json` exists and marks all required topology facets as addressed or explicitly unresolved
- the fresh no-context validation subagent can answer the anchor question mainly from the product output rather than by replacing the product with manual research

For this work order, "materially useful answer" means at least:
- the answer does not dodge the multiplicity question
- the answer does not flatten everything into a generic certificate-role summary
- the answer does not present medium-rank project-artifact logic as governing law

## 7. Boundaries

V2.1 remains inside Option A.
It does not introduce:
- open-web search
- graph persistence
- UI work
- multi-agent orchestration in the product itself
- broad corpus expansion beyond what is needed for this question family

This is a narrow usefulness improvement release, not a new platform phase.
