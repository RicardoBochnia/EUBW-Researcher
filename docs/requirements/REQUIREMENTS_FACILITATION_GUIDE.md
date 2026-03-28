# Requirements Facilitation Guide

This file is a companion to `AGENTS.md`.
It is not the primary rule source.

If guidance here appears to conflict with explicit rules in `AGENTS.md`, **`AGENTS.md` takes precedence**.

## Purpose

This guide exists to reduce two risks:
1. the session becomes too loose and solution-driven
2. the session becomes too formal, taxonomic, or ceremonial

The goal is not process display.
The goal is a requirement basis strong enough to constrain architecture.

## What good facilitation looks like

Good facilitation:
- asks sharp questions
- forces tradeoffs
- grounds claims in scenarios
- surfaces contradictions
- distinguishes strong requirements from vague aspirations
- moves forward once something is sufficient-for-now

Bad facilitation:
- narrates the process too much
- turns every answer into a taxonomy display
- treats every open point as equally important
- keeps probing low-leverage ambiguities
- confuses process neatness with design readiness

## Interpreting the categories

### Confirmed requirement
Specific enough to constrain later design choices and grounded in at least one concrete scenario.

### Plausible assumption
A likely but still unverified claim.

### Unresolved design question
An open question that materially affects design.

### Evaluation criterion
A statement about how usefulness, adequacy, trust, or success would be judged.

### Design hypothesis
A solution idea or mechanism that might address a requirement but is not itself the requirement.

### Out-of-scope item
A request, scenario, or concern that is explicitly excluded from the current target system.

## Using categories without turning the session into a taxonomy exercise

Use the internal classification scheme rigorously.

Important distinction:
- **good externalization** = using concise status labels in recaps when they improve clarity
- **bad externalization** = narrating the methodology itself or over-labeling every conversational move

Do **not** suppress useful status labels in recaps.
Do suppress needless methodology narration.

## Stability labels

### Stable
Scenario-grounded and not in unresolved contradiction with other confirmed requirements.

### Provisional
Potentially important, but not sufficiently pressure-tested yet.

### Validation-needed
Depends on assumptions, unresolved contradictions, stakeholder disagreement, or later empirical validation.

## Dependency tagging

Use dependency tags only when they materially matter.

A requirement may depend on:
- stakeholder type
- scope choice
- deployment context
- review workflow
- assurance regime
- local-only vs augmented behavior

Do not tag dependencies just for completeness.

## What counts as a good question

A good question:
- narrows uncertainty
- forces prioritization
- exposes a hidden tradeoff
- converts abstraction into a scenario
- reveals a failure condition
- or resolves a contradiction

A weak question:
- invites aspiration without constraint
- asks for more detail without leverage
- repeats already-adequate understanding
- sounds sophisticated without improving design-relevant clarity

## Escalation guidance

If the user is vague:
- ask for a concrete scenario
- ask what failure would look like
- ask what would count as good enough
- ask what competing goal would be sacrificed

If the user remains vague:
- do not promote the point
- reclassify it
- state what would be needed to make it operational

If the user keeps hedging:
- record an assumption if the point is high-leverage
- allow “unknown and unresolved” if the point is low-leverage or premature to force

## High- vs low-leverage unknowns

Do not spend equal effort on all unknowns.

High-leverage unknowns are those that materially affect:
- architecture
- scope
- validation strategy
- trust / assurance claims
- stakeholder acceptance

Low-leverage unknowns may remain open without blocking useful progress.

When in doubt, prioritize the unknown that most constrains the next real design choice.

## Stakeholder conflicts

Do not assume the primary user is the only relevant stakeholder.

Potentially relevant actors may include:
- primary researcher
- occasional user
- reviewer
- maintainer
- domain expert
- sponsor / owner

Surface stakeholder conflicts when they materially affect:
- success criteria
- acceptable error
- evidence expectations
- review burden
- maintainability
- adoption
- scope

## Decision-grade practical interpretation

The formal definition lives in `AGENTS.md`.

In practice, the basis is **not** decision-grade if:
- the main user is still fuzzy
- the core job is still broad
- scenarios are too generic
- tradeoffs are listed but not prioritized
- core unknowns remain high-leverage
- architecture options would still be mostly speculative

The basis **may** still be decision-grade if:
- some edge cases remain open
- some low-leverage unknowns remain unresolved
- some assumptions are still provisional but clearly marked and non-blocking

## Avoiding process theater

Prefer:
- fewer, sharper recaps
- fewer, higher-leverage questions
- explicit prioritization
- visible contradictions
- concrete scenarios

Avoid:
- excessive recap volume
- over-classification in live interaction
- over-probing just to “complete the method”
- forcing closure on low-leverage uncertainties

## When to revisit earlier phases

Revisit earlier phases if:
- a materially different user group appears
- the core job-to-be-done changes
- the scope expands significantly
- a new scenario undermines earlier assumptions
- a stakeholder conflict changes what “success” means

Do not protect linearity at the expense of truth.

## Suggested usage pattern

Recommended usage:
- use `AGENTS.md` as the active Codex-facing instruction file
- use this guide as companion guidance for calibration and interpretation
- use `REQUIREMENTS_FACILITATION_REVIEW.md` afterward to review a session or artifact critically
