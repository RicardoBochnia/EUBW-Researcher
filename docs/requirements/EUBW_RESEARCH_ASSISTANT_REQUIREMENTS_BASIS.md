# EUBW Research Assistant Requirements Basis

Status: decision-grade requirements basis
Date: 2026-03-29
Architecture note: architecture options are intentionally omitted

## 1. Vision

### Purpose
Provide a Codex-based research assistant that answers questions about the EU Business Wallet and adjacent SSI topics through useful, source-bound synthesis.

### Primary user model
- Operational user: the agent.
- Real beneficiary and quality judge: the researcher working on SSI for organizations and the European Business Wallet.

### Core job-to-be-done
Turn research questions into answers that are useful for ongoing research and team work without forcing the user to manually reconstruct the full source landscape each time.

### Intended value
- reduce repeated manual source discovery
- connect relevant sources across layers
- provide reusable first-pass answers with evidence

### Worst failure
A core claim is unsupported, wrongly supported, or grounded in the wrong source role without that being visible.

## 2. Primary success scenario

### Anchor scenario
Question: what requirements apply to the Business Wallet, and how can they be provisionally structured?

### Minimum useful outcome
- extracts relevant requirements and constraints from the proposal and its annex
- connects central articles with the annex material
- provides a provisional grouping of findings
- makes clear that the grouping is provisional rather than the final research result

### Clear failure
- invents a requirement that is not present in the source basis
- imports remote or weak sources as if they were authoritative without making that visible

## 3. Representative scenarios

### Scenario A: Registration and access certificate analysis
- User goal: understand how the topic is regulated across multiple layers.
- Start input: only the natural-language question.
- Relevant source layers:
  - eIDAS / regulation-level source
  - implementing acts
  - referenced technical standards
  - national or implementation documentation when needed
- Useful result:
  - identifies the relevant source chain
  - explains how the pieces relate
  - gives a source-bound synthesis instead of a raw source list

### Scenario B: Is the registration certificate mandatory?
- User goal: understand whether the obligation is fixed at EU level or delegated to member states.
- Useful result:
  - addresses the EU level first
  - preserves member-state choice where applicable
  - may add Germany as best-effort context
- Unacceptable error:
  - states that it is optional everywhere without noting member-state discretion

### Scenario C: OpenID4VCI versus OpenID4VP authorization server
- User goal: understand a technical protocol distinction.
- Start input: only the question.
- Relevant source layers:
  - current published OpenID4VCI specification
  - current published OpenID4VP specification
- Useful result:
  - answers more than yes / no
  - explains why the protocol behavior differs
  - points to the relevant sections in the specifications
- Unacceptable error:
  - gives an unsupported yes / no answer without explanation from the specifications

### Difficult / ambiguity-heavy pattern
Questions that cross EU-level rules, member-state discretion, technical standards, and project documentation are expected and must preserve the differences between these layers.

### High-risk failure pattern
The system appears plausible while overlooking a higher-ranked source that actually governs the point.

### Explicit but soft out-of-scope anchor
For version 1, a prompt such as "Design a concrete target architecture for a German Business Wallet implementation" is outside the core target system and must not count as a success criterion for the research assistant.
This boundary is intentionally soft rather than a hard prohibition because adjacent support may still be useful in practice; that softness was reviewed and accepted as a version-1 risk.

## 4. Baseline workflow and pain points

### Current workflow
- start from a research question
- manually search regulation-level documents
- inspect implementing acts
- inspect referenced technical standards
- inspect national or project-specific documentation where needed
- connect the findings manually

### Main pain points
- important sources are distributed across layers
- some relevant documents are easy to miss
- freshness is uncertain
- cross-source linking is time-consuming
- questions often require more than retrieval; they require synthesis

### Adoption threshold
The system is worthwhile if, in normal use, the researcher can often stop after a source-bound first answer and continue with targeted spot-checking instead of rebuilding the source landscape from scratch.
This remains an intentionally qualitative threshold for version 1 because the research workflow is too irregular for a stronger quantitative benchmark; that softness was reviewed and accepted as a version-1 risk.

## 5. Confirmed functional requirements

### Must-have
1. Produce source-bound answer synthesis with explanation, not just source retrieval.
2. Find relevant sources across layers, initially focused primarily on the EU level.
3. Make contradictions, hierarchy, uncertainty, and source role visible instead of smoothing them over.

### Strong supporting requirements
- Use curated / offline material as a preferred base when available.
- Expand beyond the curated set through web research when needed.
- Start from the user's question alone; the agent is expected to infer what source types must be consulted.
- When questions are too broad, asking a clarifying follow-up is desirable, but not one of the first three must-have capabilities.

### Optional or later
- automated freshness checking
- broad member-state coverage
- richer dialogic clarification flows
- systematic use of opinion pieces and practice sources beyond supplementation

## 6. Quality attributes and prioritization

### Primary optimization target
Useful, broad answer synthesis.

### Non-negotiable property
Avoid unsupported or wrongly supported core claims.

### Acceptable compromise
Initial freshness may be managed through manual curation rather than automated checking.

### Unacceptable tradeoff
Increasing apparent usefulness by including unsupported core claims.

### First cut under scope pressure
Broad member-state coverage can be reduced before core answer-synthesis quality is reduced.

### Latency stance
Quality is more important than speed. Multi-minute deep-research behavior is acceptable.

## 7. Source-role and evidence rules

### Highest-available-source rule
For each supporting core claim, the system should actively look for the highest-available source rather than stopping at the first plausible source.

### Use of lower-ranked sources
If higher-ranked sources do not fully answer the question, lower-ranked sources may still be used to improve usefulness, provided their role is preserved.

### No false elevation
The system must not present ARF, project artifacts, national implementation documentation, or similar material as if it were binding EU regulation.
Illustrative unacceptable formulation: a sentence such as "The ARF requires X" or "EU regulation requires X" when X is only supported by ARF, project documentation, or national implementation material.

### Minimum evidence form
- baseline minimum: identify the document
- preferred for claim-specific statements: also identify the relevant article, section, clause, or equivalent location

### Status marking
The source reference itself may carry enough status information in many cases; the system does not need to redundantly narrate source status in every sentence if the citation already makes it clear.

## 8. Working source hierarchy

### High
- law / regulation
- implementing acts and equivalent regulatory material
- referenced technical standards

### Medium
- ARF
- official project artifacts
- scientific literature

### Low
- expert commentary
- practice sources

Note: some project artifacts may later need finer differentiation, but this is not blocking.

## 9. Web expansion policy

When the curated or offline set is insufficient, the system should expand through defensive web research.

### Acceptable web sources for supporting core claims
- official EU or other official institutional sources
- recognized standard-setting bodies
- clearly attributable official project or pilot artifacts

### Not acceptable as the main basis for core claims
- random vendor blogs
- marketing-style commentary
- weakly attributable opinion posts

Such sources may still appear as supplement, but not as the main support for core claims.

## 10. Scope boundaries for version 1

### In scope
- source-bound synthesis for EU Business Wallet / SSI research questions
- regulation-heavy and technical / techno-regulatory questions
- EU-level answering first

### Best-effort only in version 1
- Germany-specific or national-level answering when explicitly asked
- broader member-state comparison

### Not a core success case
- independent architecture design as the primary task
- normative or political argument writing as the primary task

## 11. Open but non-blocking points

- exact clustering logic for Business Wallet requirements
- finer source ranking for some project artifacts
- richer web-source policy
- stronger freshness automation

These remain open, but they do not block later design work because the primary user, job, scenarios, must-haves, quality priorities, and source-role rules are already explicit enough to constrain design choices.

## 12. Reviewed and accepted version-1 risks

The following points were explicitly revisited in review and are intentionally retained in a softer form for version 1:
- the success threshold remains qualitative rather than numerically operationalized
- the out-of-scope boundary remains explicit but soft, so adjacent help is not overconstrained
- the source-role-mixing rule is anchored by an illustrative negative example, while a richer catalog of edge cases is deferred

These are not accidental omissions. They are known limitations that were reviewed and accepted for the current version of the requirements basis.

## 13. Decision-grade assessment

This basis is considered decision-grade because:
- the primary user model and core job are explicit
- the baseline workflow and major pain points are clear
- primary, representative, technical, difficult, and failure scenarios are captured
- must-have versus optional capabilities are distinguished
- the main quality priorities and unacceptable failure mode are explicit
- major source-role expectations are defined
- remaining uncertainties are narrow enough to refine later without making all design discussion speculative

This document intentionally stops before architecture.
