# Architecture Proposals Masterplan

Status: approved process baseline
Language: English
Purpose: produce an architecture decision basis, not a forced target architecture

## 1. Inputs and objective

This process is grounded in the frozen requirements basis:
- [EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [EUBW_RESEARCH_ASSISTANT_ELICITATION_SUMMARY.md](../requirements/EUBW_RESEARCH_ASSISTANT_ELICITATION_SUMMARY.md)

The goal is to produce:
- 3 serious architecture paths
- 1 credible baseline / control option
- standardized external reviews
- one comparison synthesis that separates supported findings, judgment, and unresolved uncertainty

This process does not force a final target architecture.

## 2. Roles

### Requirements Owner
- Owns the frozen requirements basis.
- Decides whether a requirements patch is accepted, rejected, or carried as an open assumption.
- Checks requirements fidelity before review freeze.
- Gives the final approval for the internal comparability gate.
- Decides in case of disagreement with the Architecture Facilitator.

### Architecture Facilitator
- Runs the architecture proposal process.
- Prepares the variant scoping.
- Ensures all variant plans use the same structure and level of abstraction.
- Performs the formal comparability check before review freeze.
- Consolidates the comparison synthesis.

### External Reviewers
- Review all frozen variant plans in the same review wave.
- Must review against the requirements basis and the review rubric.
- Must separate document-supported findings from judgment calls and unresolved uncertainty.
- Must write only to reviewer-owned raw review files and must not overwrite each other.

## 3. Artifacts

### Core process documents
- [VARIANT_SCOPING.md](./VARIANT_SCOPING.md)
- [REVIEW_RUBRIC.md](./REVIEW_RUBRIC.md)
- [REQUIREMENTS_PATCHES.md](./REQUIREMENTS_PATCHES.md)
- [OPTIONS_COMPARISON.md](./OPTIONS_COMPARISON.md)
- [reviews/README.md](./reviews/README.md)
- [reviews/TEMPLATE_ALL_OPTIONS.md](./reviews/TEMPLATE_ALL_OPTIONS.md)

### Per-option documents
- [options/option-a/PLAN.md](./options/option-a/PLAN.md)
- [options/option-a/REVIEW.md](./options/option-a/REVIEW.md)
- [options/option-b/PLAN.md](./options/option-b/PLAN.md)
- [options/option-b/REVIEW.md](./options/option-b/REVIEW.md)
- [options/option-c/PLAN.md](./options/option-c/PLAN.md)
- [options/option-c/REVIEW.md](./options/option-c/REVIEW.md)
- [options/baseline/PLAN.md](./options/baseline/PLAN.md)
- [options/baseline/REVIEW.md](./options/baseline/REVIEW.md)

### Raw external review documents
- `reviews/<reviewer-id>.md`

Raw external reviews are reviewer-owned batch files. The per-option `REVIEW.md` files are facilitator-owned consolidation targets and are not written directly by external reviewers.

The current option slugs are review-round labels. They may be renamed after this review round if clearer long-form names become useful.

## 4. Workflow and gates

### Gate 1: Requirements freeze
- The current requirements basis is the binding input.
- Architecture work must not silently reinterpret, weaken, or extend the requirements.

### Step 2: Data and corpus assumptions
- Record the current assumptions about source formats, curated/offline corpus, web expansion, structure quality, and obvious data risks.
- The purpose is to avoid architecture proposals that depend on hidden corpus assumptions.

### Gate 2: Variant scoping
- Define exactly four candidates in [VARIANT_SCOPING.md](./VARIANT_SCOPING.md):
  - 3 serious architecture paths
  - 1 credible baseline / control option
- Rules:
  - no filler variant just to satisfy the count
  - each serious option must differ in at least two primary architecture levers
  - the baseline must explain why it is a baseline and why it is not a disguised full option
  - each option must fit the V1 scope or explicitly state its V1 boundary
- The scoping must be reviewed for diversity, plausibility, and V1 relevance before plan drafting starts.

### Step 3: Draft all PLAN documents
- Draft all four option plans using the shared template shape.
- Each plan must cover the same scenario set, the same evidence and uncertainty topics, and comparable decision relevance.

### Step 4: Requirements patch handling
- Use [REQUIREMENTS_PATCHES.md](./REQUIREMENTS_PATCHES.md) only for true blockers:
  - a real contradiction in the requirements basis
  - a real build blocker for one or more options
  - a missing, decision-critical requirement
- Do not use patches for:
  - architecture taste
  - opportunistic scope expansion
  - non-blocking detail gaps
- A patch is considered decided only if:
  - the requirements basis is corrected, or
  - the affected option explicitly carries the uncertainty as an open assumption in its plan and later review
- An unresolved real blocker prevents the affected option from freezing.

### Gate 3: Internal comparability
The Architecture Facilitator checks all plans for:
- same structure
- same scenario coverage
- same level of abstraction
- comparable argumentative depth
- explicit treatment of uncertainty, source roles, data assumptions, and V1 constraints
- explicit cost / latency / maintenance view

The Requirements Owner then checks requirements fidelity and decides whether the gate passes.

If the Facilitator finds the set formally comparable but the Requirements Owner finds it insufficiently faithful to the requirements, the Requirements Owner decision prevails.

### Gate 4: Freeze for external review
- Freeze the full plan set only after Gate 3 passes.
- External review starts only after all four plans are frozen together.

### Step 5: External review
- Each review uses the same rubric in [REVIEW_RUBRIC.md](./REVIEW_RUBRIC.md).
- Each external reviewer reviews all four frozen option plans in the same review wave.
- Each external reviewer writes only to one reviewer-owned raw batch file under `docs/architecture/reviews/`, for example `docs/architecture/reviews/reviewer-1.md`.
- No two external reviewers may write to the same file.
- Each reviewer receives:
  - all four frozen option PLANs
  - the frozen requirements basis
  - the masterplan
  - the review rubric
  - relevant requirements patches
- Required reviewer perspectives:
  - Traceability / Compliance
  - System / Data / Performance
  - Research Workflow / User Value

### Step 6: Consolidate per-option review syntheses
- After the raw external review wave is complete, the Architecture Facilitator consolidates the reviewer-owned batch files into:
  - [options/option-a/REVIEW.md](./options/option-a/REVIEW.md)
  - [options/option-b/REVIEW.md](./options/option-b/REVIEW.md)
  - [options/option-c/REVIEW.md](./options/option-c/REVIEW.md)
  - [options/baseline/REVIEW.md](./options/baseline/REVIEW.md)
- Consolidation must preserve the same separation:
  - supported findings
  - judgment calls
  - unresolved uncertainties

### Step 7: Comparison synthesis
- Compare all options only with criteria mapped back to the requirements basis.
- The comparison document must separate:
  - supported findings
  - judgment calls
  - unresolved uncertainties
  - likely later evaluation needs

### Gate 5: Decision basis complete
- The process completes when the comparison synthesis is strong enough to support a later architecture decision without forcing one now.

## 5. Execution standards

- All architecture artifacts in this directory are written in English.
- Quality is more important than speed; this process optimizes for defensible comparison.
- The baseline must stay simple and credible, not intentionally weak.
- Evaluation is not built in this phase, but evaluation-critical assumptions must be logged per option.
- External review comparability is achieved by having each reviewer assess all four options under the same rubric rather than splitting the option set across different reviewers.

## 6. Acceptance criteria

- `MASTERPLAN.md` is acceptable when roles, gates, escalation, artifact boundaries, and patch handling are executable without additional decisions.
- `VARIANT_SCOPING.md` is acceptable when all 3 serious options are materially distinct and the baseline is credibly justified.
- `REVIEW_RUBRIC.md` is acceptable when each must-have and each critical quality constraint has at least one falsifiable review question, and the separation of findings / judgment / uncertainty is operationalized.
- A raw external review file under `reviews/` is acceptable when it reviews all four options under the same rubric and is owned by exactly one reviewer.
- An option `PLAN.md` is acceptable when it matches the common structure and covers the same scenarios and decision depth as the other options.
- An option `REVIEW.md` is acceptable when it is a facilitator-owned consolidation of the raw review wave and clearly separates supported findings from judgment.
- `OPTIONS_COMPARISON.md` is acceptable when every comparison criterion is mapped to the requirements basis and later evaluation needs are stated per option.
