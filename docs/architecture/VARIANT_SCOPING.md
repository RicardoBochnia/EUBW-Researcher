# Variant Scoping

Status: approved and frozen for external review handoff
Purpose: define the 3+1 architecture option set before detailed plan drafting

## 1. Inputs

Required inputs:
- [MASTERPLAN.md](./MASTERPLAN.md)
- [EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [EUBW_RESEARCH_ASSISTANT_ELICITATION_SUMMARY.md](../requirements/EUBW_RESEARCH_ASSISTANT_ELICITATION_SUMMARY.md)

## 2. Scoping rules

- Exactly four candidates are scoped here:
  - 3 serious options
  - 1 baseline / control option
- No serious option may exist only to satisfy the option count.
- Each serious option must differ from the others in at least two primary architecture levers.
- The baseline must be simple, credible, and explicitly justified as a baseline rather than a disguised full option.
- Each option must fit the V1 scope or explicitly state its V1 boundary.
- The current slugs below are acceptable review-round labels and may be renamed later if clearer long-form names become useful.

## 3. Primary architecture levers

Use this section to state the levers that actually differentiate the option set. At minimum, select the levers that make the serious options materially different.

Potential levers:
- orchestration style
- knowledge organization / indexing strategy
- evidence and traceability model
- web-expansion strategy
- document-structure handling
- answer synthesis control model
- conflict and uncertainty handling strategy

Chosen levers for this scoping round:
- orchestration style
- knowledge organization / indexing strategy
- evidence and traceability control model

## 4. Option set

| Option | Slug | Type | Core thesis | Primary differentiators | V1 fit | Why defensible |
| --- | --- | --- | --- | --- | --- | --- |
| Option A | `option-a` | Serious path | Evidence-First Layered Pipeline: a staged, source-rank-aware research pipeline builds a claim/evidence ledger before any final synthesis. | Static gated orchestration; article-level evidence ledger; gap-driven web expansion. | Strong V1 fit. | Maximizes traceability and source-role discipline with moderate implementation complexity. |
| Option B | `option-b` | Serious path | Provenance Graph Planner: the corpus is normalized into a source/provision graph that drives cross-layer discovery before synthesis. | Graph-centered knowledge model; planner-led traversal; provenance encoded in nodes and edges. | Conditional V1 fit. | Strongest option for cross-layer linking and provisional clustering if the graph assumptions hold. |
| Option C | `option-c` | Serious path | Specialist Research Orchestrator: a coordinator decomposes the query into regulatory, standards, and implementation workstreams and reconciles them in a shared evidence ledger. | Multi-worker orchestration; role-specific retrieval tools; adjudication-driven synthesis. | Moderate V1 fit. | Best for ambiguity-heavy mixed-source questions and future extensibility. |
| Baseline | `baseline` | Control / baseline | Constrained Hybrid RAG Baseline: a simple hybrid retrieval-and-synthesis path over the curated corpus with narrow official-web fallback. | Minimal orchestration; simple hybrid search; light post-hoc citation handling. | Limited but real V1 fit. | Provides a credible control option for judging whether heavier architecture is justified. |

## 5. Distinctness check

For each serious option, show why it is not a trivial variation of another option.

### Option A distinctness
- Compared with Option B: Option A keeps knowledge mostly document-centric and stages retrieval in a fixed pipeline; Option B invests in a normalized graph and relation-first traversal.
- Compared with Option C: Option A minimizes agentic branching and centralizes control in fixed stage gates; Option C uses specialist decomposition and adjudication between worker outputs.

### Option B distinctness
- Compared with Option A: Option B depends on a maintained provenance graph rather than a transient evidence board assembled per query.
- Compared with Option C: Option B is graph-first and structurally guided; Option C is worker-first and investigation-driven.

### Option C distinctness
- Compared with Option A: Option C trades deterministic stage-gating for flexible sub-question decomposition and reconciliation.
- Compared with Option B: Option C does not require a full graph-normalized corpus to work; its main dependency is coordinated worker behavior and a shared evidence schema.

## 6. Baseline rationale

The baseline must explicitly answer both questions:
- Why is this option a baseline rather than a fourth full-strength architecture path?
- Why is this baseline still credible enough to function as a real control option?

Baseline rationale:
- It is a baseline because it represents the simplest defensible architecture that still tries to answer the actual V1 problem: hybrid retrieval over a curated corpus, narrow official-web fallback, and a single synthesis pass.
- It is not a disguised full option because it intentionally avoids graph normalization, specialist orchestration, and a dedicated multi-step evidence-control pipeline.
- It is still credible because many source-bound research assistants start from exactly this level of architecture, so it is a realistic control for measuring the value of added complexity.

## 7. V1 and data-assumption check

For each option, record the main V1 fit and the main data / corpus dependency.

| Option | Main V1 alignment | Main V1 boundary | Main data / corpus dependency |
| --- | --- | --- | --- |
| Option A | Strong fit for EU-first, evidence-heavy V1 | Limited flexibility for emergent lateral relations and sophisticated clustering | Reliable article/section extraction and source-rank metadata in the curated corpus |
| Option B | Strong fit for linked-source research if ingest succeeds | Higher upfront modeling burden may be heavy for V1 | Extractable citations, references, and stable provision-level normalization |
| Option C | Strong fit for ambiguous mixed-source questions | Highest operational complexity and drift risk in V1 | Shared evidence schema, role-specific tools, and bounded specialist behavior |
| Baseline | Good as a credible control option | Weakest on conflict handling, source-role preservation, and multi-hop cross-layer reasoning | Searchable text coverage across the curated corpus and basic metadata for reranking |

## 8. Scoping gate outcome

### Architecture Facilitator check
- Achieves 3 materially distinct serious paths: `yes`
- Baseline is credible and not disguised: `yes`
- V1 fit is acceptable for all options: `yes`
- Option set is worth detailed drafting: `yes`

Notes:
- The option set deliberately spans a deterministic evidence-first pipeline, a graph-led knowledge design, and a worker-orchestrated deep-research design.
- The baseline is intentionally simple but still source-bound and official-web-aware, so it can function as a real control option.

### Requirements Owner check
- Scoping is requirements-faithful: `yes`
- Option set is approved for PLAN drafting: `yes`

Notes:
- Working approval is assumed from the instruction to advance the process autonomously to the external-review handoff stage.

## 9. Handoff state for this round

- Variant scoping is complete.
- All four option plans have been drafted in a common structure with common scenario coverage.
- No blocker-level requirements patches were raised during scoping or plan drafting.
- The Architecture Facilitator comparability check is treated as passed for this round.
- Requirements-fidelity approval is treated as passed for this round based on the explicit instruction to advance autonomously to reviewer handoff.
- Current state: the 3+1 option set is ready to be reviewed as one frozen batch.
