# EUBW Research Assistant Elicitation Summary

Date: 2026-03-29
Status: sufficient-for-now, decision-grade requirements basis
Architecture: intentionally not covered in this artifact

## Session outcome

The elicitation produced a requirements basis for a Codex-based research assistant that answers questions about the EU Business Wallet, SSI for organizations, eIDAS, OpenID4VC, SD-JWT, and adjacent topics through source-bound answer synthesis.

The basis is considered decision-grade for later design work because the following are now explicit:
- primary user and job-to-be-done
- baseline workflow and major pain points
- primary, representative, difficult, technical, and failure scenarios
- must-have capabilities versus later-stage items
- primary optimization target, acceptable compromise, and unacceptable tradeoff
- source-role expectations and minimum evidence behavior

## Completed phases

### Phase 1: Vision
- Primary operational user: a Codex-based agent.
- Primary value owner and quality judge: the researcher.
- Core job: deliver useful, source-bound answer syntheses for SSI / EU Business Wallet research questions.
- Primary success condition: the researcher can use answers as a reliable starting point for research and team questions without rebuilding the source landscape manually.
- Worst failure: unsupported or incorrectly supported core claims.

### Phase 2: Baseline, scenarios, pain points
- Current research requires cross-reading regulation, implementing acts, technical standards, and national or project documentation.
- Main pain points are distributed sources, missed documents, uncertain freshness, and the effort needed to connect sources across layers.
- Primary anchor scenario: extract and provisionally group Business Wallet requirements from the proposal and annex.
- Additional scenarios:
  - Registration / access certificate analysis across layers
  - Registration certificate obligation: EU versus member-state choice, with Germany as an important case
  - Technical protocol question: OpenID4VCI versus OpenID4VP and authorization server role
- Explicit failure pattern: answers that contain unsupported or wrongly supported core claims.

### Phase 3: Functional requirements
- Must-have:
  - source-bound answer synthesis with reasoning, not just retrieval
  - finding relevant sources across layers
  - making contradictions, hierarchy, and uncertainty explicit
- Important but not first-line must-have:
  - dialogic clarification of underspecified questions
  - broad member-state coverage
  - automated freshness checking

### Phase 4: Quality attributes
- Primary optimization target: useful, broad answer synthesis.
- Quality over latency: deep-research behavior is preferred over chatbot speed.
- Acceptable compromise: freshness can initially be curated manually.
- First cut under scope pressure: broad member-state coverage.
- Non-negotiable failure condition: unsupported or incorrectly supported core claims.

### Phase 5: Epistemic / source-role constraints
- For every supporting core claim, the system should actively seek the highest-available source.
- Lower-ranked sources may still be used when higher-ranked sources do not fully answer the question.
- Such use must preserve the actual role of the source and must not present lower-ranked material as binding regulation.
- Minimum evidence form: document-level citation; for strong claim-specific statements, section / article references are preferred.

### Phase 6: Open tensions and conflicts
- No material stakeholder conflict was identified beyond the researcher's own quality standard.
- Remaining tensions are mostly calibration questions, not blockers:
  - exact clustering logic for Business Wallet requirements
  - finer placement of some project artifacts in source ranking
  - more detailed web-source policy

## Key decisions captured during elicitation

- The system is primarily an answer-synthesis system, not a pure research directory.
- If higher-ranked sources are insufficient, the system should still aim for useful synthesis using lower-ranked sources.
- Transparent uncertainty is acceptable if it increases usefulness and does not hide source weakness.
- Version 1 may be EU-focused first; Germany-specific answers are best-effort rather than mandatory.
- Web expansion is preferred when the curated offline set is not enough.
- Web use should stay defensive: official, standard-setting, or clearly attributable project/pilot artifacts can support core claims; random vendor blogs should not.

## Non-blocking open items

- The exact clustering scheme for Business Wallet requirements remains part of the research itself.
- The source-ranking treatment of some project artifacts may need refinement.
- A more explicit web-search policy may be added later.
- Automated freshness checks can be added after the first useful version exists.

## Review disposition

The requirements basis was reviewed after synthesis.
Three initially flagged soft spots were intentionally kept only partially specified for version 1 and explicitly accepted as risks:
- the practical success threshold remains qualitative
- the out-of-scope boundary remains explicit but soft
- the source-role rule uses an illustrative negative example rather than a full edge-case catalog

## Companion artifact

This session is paired with a structured requirements artifact in `docs/requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md`.
That document captures the confirmed requirements basis, quality attributes, source-role rules, and open tensions without moving into architecture yet.
