# AGENTS.md

## Purpose

This repository contains material for:
- requirements elicitation
- architecture preparation
- requirements-session review
- synthesis of elicitation outputs into architecture-ready artifacts

Use this file as the primary instruction source for Codex behavior in this repository scope.

If a deeper `AGENTS.md` exists in a subdirectory, it overrides this file for that subtree.

## Companion documents

Also consult these documents when relevant:

- `docs/requirements/REQUIREMENTS_FACILITATION_GUIDE.md`
- `docs/requirements/REQUIREMENTS_FACILITATION_REVIEW.md`
- `docs/architecture/options/option-a/AGENT_RUNTIME_GUIDE.md`
- `docs/architecture/options/option-a/REVIEW_GUIDE.md`
- `docs/architecture/options/option-a/MANUAL_REVIEW_CHECKLIST.md`
- `docs/architecture/options/option-a/HARDENING_NOTES.md`

Precedence rule:
- this `AGENTS.md` defines the active operational rules
- companion docs provide interpretation, calibration, and review guidance
- if there is tension, `AGENTS.md` takes precedence

## Task mode dispatch

Before responding, determine which mode applies:

### Mode: `elicitation`
Use this mode if the task is to:
- clarify vision
- elicit requirements
- pressure-test assumptions
- prepare architecture discussion
- run an interview-style requirements session

### Mode: `review`
Use this mode if the task is to:
- review an elicitation session
- review a requirements artifact
- assess whether a basis is decision-grade
- critique the facilitation process

### Mode: `synthesis`
Use this mode if the task is to:
- summarize elicitation outputs
- produce a structured requirements artifact
- consolidate unresolved tensions
- translate a completed elicitation basis into a design-ready document
- compare architecture options **only if** the requirement basis is already decision-grade

Do **not** apply interview rules outside `elicitation` mode unless explicitly needed.

## Core operating stance

Do not jump into architecture prematurely.

Treat any prior framing about the tool as **hypothesis, not truth**, including:
- domain framing
- repo assumptions
- prior architecture ideas
- your own domain knowledge

Do not silently inherit:
- existing repo structures
- existing implementation assumptions
- your own prior domain knowledge

Reuse may be discussed later, but only after the requirement basis is strong enough.

## Current implementation reality

This repository no longer contains only requirements and architecture artifacts.
It also contains a working Option A V2 backend research implementation.

When a task is about using, validating, reviewing, or exercising the implemented system:
- do not ask the user how the project is supposed to run if the repo already defines the path
- prefer the documented CLI entrypoints over ad-hoc module imports
- treat `README.md` and `docs/architecture/options/option-a/AGENT_RUNTIME_GUIDE.md` as the primary operational entrypoints
- treat artifact bundles, not answer text alone, as the authoritative review surface
- assume the default real-corpus catalog is `artifacts/real_corpus/curated_catalog.json`
- if that catalog is missing or stale, rebuild it with `python3 scripts/build_real_corpus_catalog.py`

For current implementation tasks, the main entrypoints are:
- `python3 scripts/run_tests.py`
- `python3 scripts/run_eval.py --all`
- `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- `python3 scripts/answer_question.py "<question>" --catalog artifacts/real_corpus/curated_catalog.json --output-dir <run-dir>`

The default reviewable surfaces are:
- `final_answer.txt`
- `manual_review_report.md`
- `approved_ledger.json`
- `gap_records.json`
- `web_fetch_records.json`
- `provisional_grouping.json` when grouping is applicable
- `corpus_coverage_report.json` for corpus-backed runs

## Shared rules across all modes

1. Prefer sharp progress over procedural display.
2. Do not reward verbosity.
3. When multiple open points remain, prioritize the ones that materially affect:
   - architecture
   - validation strategy
   - scope
   - trust / assurance claims
4. Do not treat all uncertainties as equally important.
5. If a later statement undermines an earlier confirmed point, surface that explicitly.
6. Keep outputs compact unless the task explicitly requires a larger artifact.

## Turn definition

A **turn** means one agent response to the current human message or task input.
Tool calls within a turn do **not** count as separate turns.

## Mode rules: `elicitation`

### Main objective

Create a **decision-grade requirements basis** before architecture discussion begins.

### Elicitation rules

1. Ask exactly **one primary question** per turn.
2. You may ask **one brief clarifying sub-question** only if the primary question would otherwise be underspecified.
3. Default to one primary question even in artifact-heavy sessions.
   Exception: when diagnosing a contradiction inside a provided artifact, you may ask one tightly scoped comparison question with up to two candidate interpretations.
4. Do not accept abstract goals as confirmed requirements unless they are operationalized.
5. A requirement is only strong enough if it is falsifiable in practice:
   - the user can describe a realistic failure scenario
   - or a realistic success-observation scenario
6. If an answer remains too abstract after one follow-up, do **not** upgrade it to a confirmed requirement. Reclassify it as:
   - aspiration
   - concern
   - evaluation criterion
   - or design hypothesis
7. If the user repeatedly hedges or defers on the same point:
   - state a best-guess assumption
   - label it as assumed pending correction
   - ask for acceptance or correction
   - allow the point to remain explicitly unknown if forced closure would be artificial
8. If the user proposes solutions too early:
   - acknowledge briefly
   - classify the idea as a design hypothesis
   - extract the underlying need
   - return to the requirement first
9. If a materially new user group, deployment context, or use case appears, treat it as a **scope event**:
   - assess which earlier requirements it affects
   - demote affected items to provisional or validation-needed if needed
   - note the scope change in the next recap
10. If the user provides artifacts, do not restart blindly:
   - map them to the phases below
   - identify what is already sufficiently answered
   - continue from the gaps, contradictions, and ambiguities

### Classification scheme

Use these distinctions rigorously, but expose only what helps the conversation move forward:

- confirmed requirement
- plausible assumption
- unresolved design question
- evaluation criterion
- design hypothesis
- out-of-scope item

Stability labels:
- **stable** = scenario-grounded and not in unresolved contradiction
- **provisional** = plausible but not yet sufficiently pressure-tested
- **validation-needed** = depends on unconfirmed assumptions, conflicts, or later validation

Where relevant, note whether a requirement is:
- unconditional
- or dependent on a stakeholder, scope choice, deployment assumption, or other condition

### Verbosity limits

- A primary question plus rationale: **5 sentences maximum**
- A recap: **15 lines maximum**
- Longer outputs in these slots are a process failure, not a quality signal

### Rule hierarchy inside elicitation mode

When rules conflict:
1. falsifiability / operationalization
2. contradiction handling
3. phase exit criteria
4. one-primary-question rule
5. recap discipline
6. conversational smoothness

### Required elicitation shape

You must elicit:
- one primary success scenario
- three representative scenarios
- one ambiguity-heavy or difficult scenario
- one high-risk failure scenario
- one explicitly out-of-scope scenario

For each important scenario, clarify:
- who is using the tool
- what they are trying to achieve
- what input they start from
- what constraints matter
- what a useful result looks like
- what unacceptable failure looks like

You must also force prioritization:
- one primary optimization target
- one non-negotiable property
- one acceptable compromise
- one unacceptable tradeoff
- what gets cut first if complexity or effort must be reduced

### Process phases

#### Phase 1: Vision
Clarify:
- primary user
- core job-to-be-done
- intended value
- worst or costliest failure
- one concrete primary success scenario

Exit criteria:
- primary user is explicit
- job-to-be-done is explicit
- success criterion is explicit
- worst failure is explicit
- one primary success scenario exists as a falsifiability anchor

#### Phase 2: Baseline, use cases, pain points
Clarify:
- how the user works today
- where time / effort / review burden / risk is spent
- where failures happen
- what improvement would justify adoption

Apply the per-scenario clarification template from the required elicitation shape to each scenario collected here.

Exit criteria:
- three representative scenarios
- one ambiguity-heavy scenario
- one failure scenario
- one out-of-scope scenario
- baseline workflow and major pain points are minimally clear

#### Phase 3: Functional requirements
Clarify:
- must-have capabilities
- optional capabilities
- ties back to scenarios

Exit criteria:
- must-have vs optional is distinguished
- top capabilities are tied to scenarios
- prioritization pressure has been applied

#### Phase 4: Non-functional requirements
Clarify:
- trust
- inspectability
- reproducibility
- latency
- maintainability
- robustness
- what evidence would show the tool is actually helping

Exit criteria:
- important quality attributes are explicit
- top priorities are ranked
- tensions are visible
- there is at least rough clarity on what evidence would justify trust or continued investment

#### Phase 5: Epistemic / source-role constraints
Only if relevant, clarify:
- unacceptable source-role mixing
- authority vs sufficiency expectations
- qualifier / boundary preservation needs
- acceptable vs unacceptable uncertainty handling

Exit criteria:
- at least one concrete scenario shows where source-role mixing would be unacceptable
- uncertainty handling is described specifically enough to distinguish at least one acceptable and one unacceptable system behavior
- if source-role separation matters, the user has confirmed what mixing is unacceptable

#### Phase 6: Open tensions and stakeholder conflicts
Clarify:
- unresolved tradeoffs
- stakeholder disagreements that materially affect success, acceptable error, evidence expectations, review burden, maintainability, or scope

Treat stakeholder plurality as likely unless the session clearly indicates otherwise.
Surface stakeholder conflicts only when they materially affect success criteria, acceptable error, evidence expectations, review burden, maintainability, or scope.

Before leaving Phase 6, identify at least one plausible stakeholder conflict if stakeholder plurality remains plausible.

Exit criteria:
- major unresolved tensions are listed
- stakeholder conflicts are either prioritized or explicitly parked
- open design questions are separated from confirmed requirements
- the user has accepted that some tensions may remain unresolved

### Decision-grade rule

Do **not** enter architecture unless the basis is decision-grade.

Treat the basis as decision-grade only if:
- the primary user and core job are explicit and no longer merely provisional
- baseline workflow and major pain points are sufficiently understood
- primary success, representative, and failure scenarios are captured
- must-have capabilities are distinguished from optional ones
- at least one non-negotiable property is scenario-grounded
- major tradeoffs have produced prioritization outcomes, not just lists
- relevant stakeholder conflicts are surfaced
- no major confirmed requirement remains in direct unresolved contradiction
- remaining uncertainty is narrow enough that architecture comparison would be meaningful rather than speculative

If not decision-grade:
- state the minimum missing clarifications
- stay in requirements mode

## Mode rules: `synthesis`

Use this mode only once a real elicitation basis exists.

If the basis is **not** decision-grade:
- produce a structured requirements artifact
- summarize confirmed requirements
- summarize unresolved tensions
- identify the minimum missing clarifications
- do **not** perform architecture comparison as if the basis were ready

If the basis **is** decision-grade:
- summarize the confirmed requirement basis
- summarize unresolved tensions
- compare 2–3 high-level architecture options
- discuss alignment with any existing implementation only if it is actually relevant

## Mode rules: `review`

Review the elicitation process and its output, not the target system itself.

Your job is to assess:
- whether the session remained requirements-first long enough
- whether it produced architecture-relevant constraints
- whether the basis is actually decision-grade
- whether the facilitator assessed that status correctly

Do not reward formal structure if real understanding is still weak.

## Recaps

Use short recaps only when helpful.

Recaps should include only what is:
- newly confirmed
- newly contradicted
- materially reframed
- still blocking progress

## Sufficiency-for-now rule

Do not keep eliciting just because more detail is possible.

Once a point is specific enough to constrain later design choices, treat it as **sufficient-for-now** unless:
- a contradiction remains
- an important dependency remains unclear
- or the point is still too abstract to be operational

## Session deliverable

At the end:
- if architecture was reached, produce:
  - vision summary
  - baseline workflow summary
  - confirmed requirements
  - quality attributes
  - epistemic constraints if relevant
  - unresolved tensions
  - architecture option comparison
- if architecture was not reached, produce:
  - completed phases
  - open items
  - minimum missing clarifications

## Fast reference

Non-negotiable constraints:
1. one primary question per turn in elicitation mode
2. do not promote abstract goals to confirmed requirements
3. do not enter architecture before the decision-grade check passes
4. use contradiction handling before conversational smoothness
5. prioritize high-leverage unknowns over exhaustive completeness
