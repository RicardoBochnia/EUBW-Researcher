# Requirements Facilitation Session Review Prompt

Review the attached or pasted requirements elicitation session critically.

Your task is to review:
- the quality of the elicitation process
- the quality of the resulting requirement basis
- whether the session stayed requirements-first long enough
- whether architecture discussion, if any, happened at the right time

Do **not** review the target system itself.
Review the elicitation session as a facilitation process and as an input to later architecture work.

## Decision-grade criteria

If `AGENTS.md` is available in context, use its decision-grade criteria.

If not, use this fallback definition.
A requirement basis is decision-grade only if:
- the primary user and core job-to-be-done are explicit and no longer merely provisional
- baseline workflow and major pain points are sufficiently understood
- primary success, representative, and failure scenarios are captured
- must-have capabilities are distinguished from optional ones
- at least one non-negotiable property is scenario-grounded
- major tradeoffs have produced prioritization outcomes, not just lists
- relevant stakeholder conflicts are surfaced
- no major confirmed requirement remains in direct unresolved contradiction
- remaining uncertainty is narrow enough that architecture comparison would be meaningful rather than speculative

## Review goals

Assess whether the session:
1. resisted premature solutioning
2. converted vague goals into operationalized requirements
3. used concrete scenarios rather than mostly abstractions
4. surfaced meaningful tradeoffs and prioritization
5. handled contradictions, uncertainty, and hedging honestly
6. surfaced stakeholder conflicts where relevant
7. produced a requirement basis that is actually decision-grade — or correctly recognized that it is not
8. generated enough real design constraints to differentiate plausible architecture options

A session is not strong merely because it is well structured; it must produce enough real constraints to make architecture comparison meaningfully less speculative.

## What to look for

### Vision quality
- Is the primary user clear?
- Is the job-to-be-done clear?
- Is success concrete?
- Is failure concrete?
- Is there a real primary success scenario?

### Scenario quality
- Are representative scenarios specific enough?
- Is there at least one difficult scenario?
- Is there at least one real failure scenario?
- Is out-of-scope treated clearly?
- Were scenarios clarified in terms of user / objective / input / constraints / useful result / unacceptable failure?

### Baseline / counterfactual quality
- Is the current workflow described concretely?
- Are pain points and costs visible?
- Is it clear what level of improvement would justify the tool?

### Requirement quality
- Are confirmed requirements actually operationalized?
- Are vague items correctly left provisional or reclassified?
- Are must-have vs optional capabilities distinguished?
- Are dependencies visible where they matter?

### Quality attributes and evidence
- Are important quality attributes explicit?
- Are they prioritized?
- Are tensions surfaced rather than smoothed over?
- Is there a credible notion of what evidence would show the tool is helping?

### Epistemic / assurance quality
- Are source-role or assurance constraints identified only when justified?
- Is uncertainty handled honestly?
- Are assurance constraints distinguishable from user-value needs where relevant?

### Stakeholder quality
- Are relevant stakeholder conflicts surfaced where they matter?
- Are they resolved or explicitly parked?

### Process discipline
- Did the facilitator ask sharp, useful questions?
- Did the session avoid empty process theater?
- Were recaps useful rather than bureaucratic?
- Was architecture delayed until the basis was strong enough?

## Required output format

### 1. Overall verdict
State whether the session is:
- weak
- acceptable
- good
- strong

### 2. Strongest strengths
List the 3–5 strongest aspects of the session.

### 3. Biggest weaknesses
List the 3–5 biggest weaknesses.

### 4. Structural blind spots
Identify anything important that is still missing, underexplored, or only superficially clarified.

### 5. Decision-grade assessment
Answer both separately:

**(a) Is the resulting requirement basis actually decision-grade?**  
Answer: yes / partially / no

**(b) Did the facilitator correctly assess whether the basis was decision-grade?**  
Answer: yes / partially / no

If these diverge, explain why.

### 6. What should be clarified next?
If the session ended before architecture:
- restrict assessment to completed phases
- identify which phases were not reached
- state the minimum missing content from them
- state the minimum clarifications needed before architecture should proceed

If architecture was reached:
- state the minimum remaining clarifications, if any

### 7. Process critique by failure mode
For each of the following, assess whether it was present:
- too vague in requirement operationalization
- too procedural / taxonomy-heavy
- premature closure
- excessive hedging / reluctance to commit
- architecture drift before the basis was ready
- formally structured but still architecturally underdetermined

Use examples where possible.

### 8. Architecture-differentiation test
Could this requirement basis already support a meaningful comparison between at least two plausible architecture options, or would such a comparison still be mostly speculative?

Explain why.

### 9. Improvement suggestions
Provide concrete improvements for the facilitation process itself, not for the target system.

## Review stance

Be skeptical.
Do not default to “looks good.”
Do not reward formal structure if real understanding is still weak.
Distinguish between:
- polished process
- and genuinely architecture-relevant requirement clarity.
