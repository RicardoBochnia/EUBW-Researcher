# Baseline Plan

Status: frozen for external review
Option type: baseline / control
Slug: baseline

## 1. Summary

- Baseline thesis: Constrained Hybrid RAG Baseline.
- One-sentence problem-solving approach: Use one hybrid retrieval-and-synthesis path over the curated corpus, with narrow official-web fallback and lightweight citation handling.
- Why this is a baseline: It reflects the simplest plausible architecture that could still try to deliver source-bound answers for V1.
- Why this is not a disguised full option: It intentionally avoids persistent graph modeling, specialist orchestration, and a dedicated multi-stage evidence-control pipeline.

## 2. Main design choices

- Choice 1: hybrid lexical/semantic retrieval over the curated corpus
- Choice 2: optional official-web fallback only when retrieval confidence is low
- Choice 3: single-pass synthesis with post-hoc citation packaging and a light source-rank filter

## 3. Main components and responsibilities

| Component | Responsibility |
| --- | --- |
| Hybrid Search Index | Retrieve relevant text from the curated corpus using a simple combined retrieval strategy. |
| Optional Web Fallback | Fetch additional material only from constrained official domains when retrieval appears insufficient. |
| Citation Post-Processor | Attach document references and basic anchors where available. |
| Final Responder | Produce the answer in one synthesis pass from the retrieved evidence. |

## 4. End-to-end answer flow

1. Receive the user prompt and run hybrid retrieval over the curated corpus.
2. If retrieval appears too weak, attempt a narrow official-web fallback rather than a deeper multi-stage investigation.
3. Pass the retrieved material to one synthesis step.
4. Attach citations and basic uncertainty notes, then return the answer.

## 5. Source handling

### Curated / offline corpus
- The curated corpus is the main source base and the main reason this baseline is still credible.
- The baseline assumes most useful V1 answers can start from this corpus without deeper orchestration.

### Web expansion
- Web expansion is intentionally narrow and only used when the initial retrieval path looks obviously insufficient.
- Web use must still remain limited to acceptable official or standard-setting sources.

### Source ranking and source roles
- Source ranking is applied in a simplified way through retrieval preferences and post-hoc filtering.
- This baseline can represent source roles, but not with the same rigor as the more advanced options.

### Conflict and uncertainty handling
- Conflict handling is shallow: the responder can note conflicts if they are visible in the retrieved material, but there is no dedicated adjudication layer.
- Uncertainty can be surfaced in the final answer, but mostly as response wording rather than as a controlled internal state.

## 6. Data and corpus assumptions

- Assumption 1: The curated corpus already contains enough of the highest-value material that a simple retrieval path can still find it.
- Assumption 2: Basic metadata and reranking signals are enough to keep the answer from leaning too heavily on low-rank sources.
- Main risk if assumptions fail: The baseline will produce plausible but under-governed answers that miss higher-ranked sources or flatten important conflicts.

## 7. Scenario coverage

| Scenario | How this baseline handles it | Main weak point | V1 judgment |
| --- | --- | --- | --- |
| Primary success scenario | Partial fit: it can retrieve proposal and annex text and synthesize a first answer. | Provisional grouping and cross-document requirement linking will likely remain shallow and unstable. | Acceptable as a control, weak as a target V1. |
| Scenario A | Partial fit: straightforward retrieval may find relevant regulation and standards. | Cross-layer linking and ranked gap-filling are likely weaker than in the serious options. | Acceptable as a control. |
| Scenario B | Partial fit: EU-first answers are possible if the right source is retrieved. | Best-effort Germany reasoning is fragile because the baseline has no strong distinction between source layers beyond simple filtering. | Acceptable as a control. |
| Scenario C | Good fit for direct protocol questions if the governing standards sections are retrieved cleanly. | If the right section is not retrieved, the answer quality drops sharply because there is little recovery logic. | Good as a control. |
| High-risk failure pattern | Weak fit: this is the option most likely to produce a plausible answer while still missing the governing source. | Missing higher-ranked evidence is harder to detect without a stronger evidence-control layer. | Useful as a control precisely because this risk stays visible. |

## 8. V1 fit and constraints

- EU-first fit: Acceptable, because the curated corpus can still be weighted toward EU-level material.
- Germany / national best-effort handling: Possible but weakly controlled.
- Quality-over-latency fit: Mixed; it can support deep-research use, but it does not inherently enforce quality-first behavior.
- Main V1 boundary: Weakest source-role control and weakest defense against plausible but under-supported synthesis.

## 9. Cost, latency, and maintenance view

- Expected latency posture: Low to medium.
- Expected operational cost posture: Low.
- Expected maintenance burden: Low to medium, driven mainly by corpus updates and retrieval tuning.

## 10. Strengths and failure modes

### Expected strengths
- Lowest complexity and lowest operating burden of the four options.
- Best control option for testing whether more architecture actually buys meaningful research quality.

### Likely failure modes
- Misses higher-ranked governing sources while still returning a confident-looking answer.
- Flattens conflicts or source-role differences because evidence control is too light.

## 11. Open assumptions and dependencies

- The curated corpus is already rich enough that simple retrieval plus synthesis is not immediately disqualifying.
- Lightweight citation packaging is enough to make the baseline comparable, even if not robust, against the serious options.

## 12. Freeze checklist

- Same structure and scenario coverage as the serious options where applicable: `yes`
- Baseline rationale is explicit: `yes`
- Not a disguised full option: `yes`
- Explicit data assumptions: `yes`
- Explicit treatment of source roles and uncertainty: `yes`
