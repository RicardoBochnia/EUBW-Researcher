# Option A Plan

Status: frozen for external review
Option type: serious path
Slug: option-a

## 1. Summary

- Option thesis: Evidence-First Layered Pipeline.
- One-sentence problem-solving approach: Use a mostly deterministic, source-rank-aware research pipeline that builds a claim/evidence ledger before final answer synthesis.
- Why this option is materially different: It keeps orchestration intentionally stage-gated and centers control on a per-query evidence ledger rather than a graph model or specialist workers.

## 2. Primary architecture levers

- Lever 1: staged orchestration with explicit gates between retrieval, evidence normalization, and synthesis
- Lever 2: ephemeral article/section-level claim-evidence ledger instead of a persistent graph
- Optional additional lever: gap-driven web expansion only after curated high-rank retrieval has been attempted

## 3. Main components and responsibilities

| Component | Responsibility |
| --- | --- |
| Query Intent and Scope Analyzer | Interpret the user question, determine whether it is broad or specific, and set the initial EU-first research scope. |
| Ranked Retrieval Planner | Decide which source layers must be consulted and in what order, starting from the highest available source role. |
| Layered Retriever Stack | Fetch evidence from the curated corpus first and then, only if needed, from constrained official web sources. |
| Evidence Ledger Builder | Normalize candidate evidence into claims, source references, anchors, and conflict markers. |
| Source Role and Conflict Controller | Preserve hierarchy, mark contradictions, and block or downgrade unsupported claims. |
| Final Answer Composer | Produce the final answer only from the approved evidence ledger. |

## 4. End-to-end answer flow

Describe the path from user prompt to final answer synthesis.

1. Parse the user question and determine scope, likely source layers, and whether clarification would be useful but non-blocking.
2. Build a ranked retrieval plan that starts from regulation and referenced standards, then expands only if the higher-ranked layers do not fully answer the question.
3. Retrieve from the curated corpus, add constrained official-web evidence only for identified gaps, and normalize all usable evidence into a claim/evidence ledger.
4. Detect conflicts, preserve source roles, block unsupported core claims, and compose the answer from the approved ledger with document and anchor references.

## 5. Source handling

### Curated / offline corpus
- The curated/offline corpus is the primary research base.
- Retrieval is source-rank-aware and favors regulation, implementing acts, and referenced standards before medium- and low-rank material.

### Web expansion
- Web expansion is used only when the curated corpus leaves a documented gap.
- The allowed target set is defensive: official institutional sites, recognized standard-setting bodies, and clearly attributable official project or pilot artifacts.

### Source ranking and source roles
- Source ranking is explicit in the retrieval planner and preserved in the ledger.
- Medium- or low-rank evidence may support a useful answer only when higher-rank sources do not fully resolve the point.
- The final answer must not present ARF, project artifacts, or national implementation material as binding EU regulation.

### Conflict and uncertainty handling
- Conflicts between source layers are preserved as separate ledger entries.
- Unsupported claims are either dropped or explicitly marked as uncertain before the final synthesis stage.
- The answer structure can include "confirmed", "interpretive", and "open" segments if needed.

## 6. Data and corpus assumptions

- Assumption 1: The curated corpus provides usable document-level metadata and enough article/section structure to support anchor-level citations for key sources.
- Assumption 2: Official web material needed for gap-filling can be converted into text with enough structure to retain source-role boundaries.
- Main risk if assumptions fail: The pipeline stays traceable but misses the best evidence because document anchors or source-rank signals are too weak.

## 7. Scenario coverage

| Scenario | How this option handles it | Main weak point | V1 judgment |
| --- | --- | --- | --- |
| Primary success scenario | Strong fit: the pipeline can extract proposal and annex requirements, align them in one evidence ledger, and produce a provisional grouping. | Provisional clustering may stay shallow because the design is optimized for traceability first, clustering second. | Strong for V1. |
| Scenario A | Strong fit: stage-gated cross-layer retrieval can traverse regulation, implementing acts, standards, and official implementation material in a controlled order. | Lateral discovery across weakly linked project or national documents may still depend on retrieval quality rather than modeled relationships. | Strong for V1. |
| Scenario B | Strong fit: the design naturally answers EU-first and then extends to Germany only if needed and evidenced. | Best-effort national reasoning may still miss unofficial but relevant implementation signals if metadata is sparse. | Strong for V1. |
| Scenario C | Good fit: targeted standards retrieval plus anchor-level evidence makes protocol distinctions explainable rather than yes/no only. | Edge cases that depend on implicit protocol interpretation may remain less elegant than in a more model-rich design. | Good for V1. |
| High-risk failure pattern | Good fit: the ranked planner and ledger explicitly try to detect when a higher-ranked source is still missing. | If retrieval misses the governing source entirely, the pipeline may still produce a plausible but incomplete answer. | Good for V1 with reviewer attention on retrieval completeness. |

## 8. V1 fit and constraints

- EU-first fit: Very strong. The pipeline naturally starts from high-rank EU-level sources.
- Germany / national best-effort handling: Supported as a controlled extension, not as a default dependency.
- Quality-over-latency fit: Very strong. Stage gates and evidence control intentionally trade speed for defensibility.
- Main V1 boundary: The design is less ambitious on persistent knowledge modeling and may underperform on relationship-heavy clustering tasks.

## 9. Cost, latency, and maintenance view

- Expected latency posture: Medium to medium-high because evidence normalization and conflict control are explicit steps.
- Expected operational cost posture: Medium; more steps than a baseline RAG path, but no persistent graph-wide reasoning or heavy multi-agent fan-out.
- Expected maintenance burden: Medium; ranking rules, corpus connectors, and answer structure need maintenance, but the architecture stays relatively inspectable.

## 10. Strengths and failure modes

### Expected strengths
- Best alignment with the non-negotiable requirement to avoid unsupported or wrongly supported core claims.
- Strong traceability and source-role discipline with comparatively understandable control flow.

### Likely failure modes
- Over-reliance on retrieval quality when cross-document relationships are not explicit in metadata or citations.
- Conservative evidence gating may reduce richness in answers that depend on looser but still useful source relationships.

## 11. Open assumptions and dependencies

- Article- and section-level anchors are reliably extractable for the highest-value sources in the initial corpus.
- The source-rank policy can be encoded consistently enough to drive retrieval and answer control without a full provenance graph.

## 12. Freeze checklist

- Same structure as the other option plans: `yes`
- Same scenario coverage as the other option plans: `yes`
- Comparable argumentative depth: `yes`
- Explicit data assumptions: `yes`
- Explicit treatment of source roles and uncertainty: `yes`
