# Review Rubric

Status: approved rubric template
Purpose: standardize external option reviews

## 0. Review-wave ownership rule

- In this architecture round, each external reviewer reviews all four frozen options, not just one.
- Each reviewer writes to exactly one reviewer-owned batch file under `docs/architecture/reviews/`.
- The per-option files under `docs/architecture/options/*/REVIEW.md` are facilitator-owned consolidation targets and must not be edited directly by external reviewers.

## 1. Required inputs

Every review must use all of the following inputs:
- all four frozen option `PLAN.md` files
- [EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [MASTERPLAN.md](./MASTERPLAN.md)
- relevant entries in [REQUIREMENTS_PATCHES.md](./REQUIREMENTS_PATCHES.md)

## 2. Review contract

Every review must:
- assess the option against requirements, not against architecture taste
- use the same question set as every other review
- distinguish supported findings from judgment calls
- explicitly log unresolved uncertainty
- identify likely later evaluation needs when needed

Reviewer personas are viewing angles, not writing styles.

Required reviewer perspectives:
- Traceability / Compliance
- System / Data / Performance
- Research Workflow / User Value

## 3. Output structure

Within the reviewer-owned batch file, each option review must produce the following sections in this order:
1. Summary verdict
2. Supported findings
3. Judgment calls
4. Unresolved uncertainties
5. Likely later evaluation needs
6. Requirement-by-requirement assessment
7. Scenario coverage assessment
8. Reviewer-perspective notes

## 4. Falsifiable review questions

Each requirement below has at least one falsifiable review question. A review is incomplete if it skips any item.

| ID | Requirement source | Falsifiable review question | Failure signal |
| --- | --- | --- | --- |
| R1 | Must-have: source-bound answer synthesis | Does the option define an explicit path from retrieved source material to a synthesized final answer with reasoning, rather than stopping at source retrieval or snippet aggregation? | The option can only return retrieved material or leaves synthesis implicit. |
| R2 | Must-have: cross-layer source finding | Can the option, as documented, reach regulation, implementing acts, referenced technical standards, and official project or web material when needed for an answer? | One or more mandatory source layers have no documented path into the answer flow. |
| R3 | Must-have: visible contradictions / hierarchy / uncertainty / source role | Does the option preserve source role and hierarchy in its answer behavior and expose conflicts or uncertainty instead of flattening them? | Lower-ranked sources can appear as binding authority, or conflicts are silently flattened. |
| R4 | Non-negotiable: avoid unsupported or wrongly supported core claims | Does the option define a mechanism that blocks, downgrades, or clearly marks unsupported core claims before the final answer is emitted? | Core claims can reach the answer without document-level support or explicit uncertainty handling. |
| R5 | V1 scope: EU-first, DE best effort | Does the option match the V1 scope instead of assuming broad member-state support as a baseline capability? | The option depends on broad national coverage to be viable in V1. |
| R6 | Quality over latency | Does the option favor defensible answer quality over chat-style speed in its control flow and evidence handling? | The option clearly trades away evidence quality mainly to reduce latency. |
| R7 | Curated corpus plus defensive web expansion | Does the option explain how curated/offline material is preferred and how web expansion is constrained to acceptable source roles? | Web expansion is unconstrained or the curated corpus has no privileged role. |
| R8 | Accepted V1 risk: qualitative success threshold | Is the option still reviewable against a practical success threshold, even though the threshold is qualitative rather than numeric? | The option gives no plausible basis to judge whether it would reduce manual reconstruction of the source landscape. |

## 5. Scenario checks

Every review must explicitly assess the option against these scenarios:
- Primary success scenario: provisional Business Wallet requirements extraction and grouping
- Scenario A: registration / access certificate analysis across layers
- Scenario B: registration certificate obligation with EU-first reasoning and DE best effort
- Scenario C: OpenID4VCI versus OpenID4VP protocol distinction
- High-risk failure pattern: plausible answer while overlooking a higher-ranked source

For each scenario, the reviewer must state:
- what the option appears able to do
- what the likely weak point is
- whether the documented design is enough for V1

## 6. Findings / judgment / uncertainty rules

### Supported findings
Only include statements that are directly supported by:
- the option plan
- the requirements basis
- decided requirements patches

### Judgment calls
Use this section for comparative or architectural judgment that is not strictly proven by the documents.

### Unresolved uncertainties
Use this section for anything that remains open because:
- the option plan is underspecified
- the data or corpus assumptions are not strong enough
- later evaluation or prototyping would be needed

## 7. Reviewer-perspective prompts

### Traceability / Compliance
- Where could this option lose source-role fidelity?
- Where could evidence links break or become ambiguous?
- Does the option help avoid unsupported core claims?

### System / Data / Performance
- What does this option depend on in the corpus and document structure?
- Where are the main operational or maintenance risks?
- Is the cost / latency / complexity burden plausible for V1?

### Research Workflow / User Value
- Would this option plausibly reduce repeated manual reconstruction of the source landscape?
- Does it fit the EU-first, deep-research workflow?
- Where would the user still need heavy manual intervention?

## 8. Acceptance criteria for the rubric

This rubric is acceptable when:
- every must-have and each critical quality constraint has at least one falsifiable review question
- required inputs are explicit
- the output structure is fixed
- supported findings, judgment, and uncertainty are operationally separated
