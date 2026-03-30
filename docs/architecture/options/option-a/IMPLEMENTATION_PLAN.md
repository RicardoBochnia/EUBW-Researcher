# Option A Implementation Plan

Status: drafted for implementation-plan review
Selected architecture basis: [PLAN.md](./PLAN.md)
Purpose: turn the chosen Option A architecture into an implementation-ready build plan for V1

## 1. Inputs and fixed constraints

This implementation plan is grounded in:
- [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [./PLAN.md](./PLAN.md)
- [./REVIEW.md](./REVIEW.md)
- [../../OPTIONS_COMPARISON.md](../../OPTIONS_COMPARISON.md)

Fixed constraints carried into implementation:
- V1 is EU-first; Germany and national material are best-effort only.
- The non-negotiable property is avoiding unsupported or wrongly supported core claims.
- The first implementation must prefer curated/offline material and use defensive web expansion only for documented gaps.
- The system must preserve hierarchy, contradiction, uncertainty, and source role in its answer behavior.
- Quality is more important than latency.

## 2. V1 delivery objective

Build a first working research assistant that can:
- start from a natural-language question alone
- retrieve across regulation, implementing acts, referenced standards, and acceptable official project/web material
- assemble a structured evidence ledger
- block or downgrade unsupported core claims
- return a source-bound answer with document-level citations and anchor-level citations where available

This plan assumes a greenfield implementation. The current repository contains requirements and architecture artifacts, but no application code yet.

## 3. Frozen design choices for implementation

These choices are treated as fixed for the first implementation unless a real blocker appears:
- staged evidence-first pipeline instead of graph-first or multi-specialist orchestration
- ephemeral per-query evidence ledger instead of a persistent provenance graph
- ranked source traversal before synthesis
- curated corpus first, constrained web second
- single answer path with explicit source-role control before final answer emission
- no broad member-state support, no freshness automation, no heavy dialog flow as V1 baseline

## 4. Implementation assumptions

These are implementation assumptions, not reopened architecture options:
- Use a Python-based service/library implementation because the repo is greenfield and the main work is document processing, retrieval control, and structured synthesis.
- Start with a code-first backend and a CLI or programmatic interface for Codex-agent use; do not build a separate end-user UI in V1.
- Keep large corpora outside git; only schemas, configs, fixtures, and small test artifacts belong in the repository.
- Use a simple, inspectable local metadata model for source ranking and allowlisted web expansion instead of a database-heavy first cut.

If one of these assumptions becomes a real blocker, record it before changing direction.

## 5. Target repository shape

This is the intended initial project shape:

```text
src/
  eubw_researcher/
    config/
    models/
    corpus/
    retrieval/
    evidence/
    answering/
    web/
    evaluation/
tests/
  fixtures/
  integration/
configs/
  source_hierarchy.yaml
  web_allowlist.yaml
  evaluation_scenarios.yaml
scripts/
  ingest_sample_corpus.py
  run_eval.py
```

Minimal purpose of each area:
- `config/`: runtime loading of hierarchy, thresholds, and allowed domains
- `models/`: typed objects for source entries, evidence units, claims, and answers
- `corpus/`: ingestion, chunking, metadata extraction, anchor extraction
- `retrieval/`: ranked planning, local retrieval, reranking, gap detection
- `evidence/`: ledger construction, conflict marking, source-role checks
- `answering/`: synthesis and answer rendering
- `web/`: constrained official-source fetching and normalization
- `evaluation/`: scenario runner and result logging

## 6. Build sequence

### Phase 0: Bootstrap and fixture setup

Deliverables:
- project skeleton under `src/`, `tests/`, `configs/`, and `scripts/`
- typed config loading and logging
- initial sample corpus fixture set for the four key scenarios
- minimal CI or local test command that runs unit and integration tests

Acceptance criteria:
- repository builds and tests run from one documented command
- configuration is externalized instead of hardcoded
- at least one fixture document per source layer exists for local tests

### Phase 1: Corpus and source catalog foundation

Deliverables:
- source catalog schema with at least:
  - source id
  - title
  - source role level
  - jurisdiction
  - publication status/date if known
  - local path or canonical URL
  - anchorability flags
- document ingestion pipeline for local curated sources
- chunking and anchor extraction at document/article/section level where possible
- ingestion report that shows which sources have strong, weak, or missing anchors

Acceptance criteria:
- local curated sources can be ingested into a consistent internal representation
- the system can emit document-level citations for all ingested sources
- anchor-level references are available where source structure permits
- anchor extraction failures are visible in logs or reports, not silent

### Phase 2: Ranked retrieval planner and local retrieval

Deliverables:
- query intent and scope analyzer with EU-first default behavior
- ranked retrieval planner that decides which source layers to query first
- local retrieval engine over curated corpus
- reranking step that incorporates source role and likely topical fit
- explicit gap record when high-rank evidence is weak or missing

Acceptance criteria:
- a regulation-heavy query searches high-rank EU sources before lower-rank material
- a standards-heavy technical query can prioritize the relevant standards set without first using web fallback
- the retrieval layer can explain why it considers a question still under-supported
- local retrieval returns enough metadata for downstream ledger construction

### Phase 3: Defensive web expansion

Deliverables:
- allowlisted web search/fetch path for official institutional, standards, and official project sources
- normalization step for fetched web material
- source-role assignment for web results before they can enter the evidence ledger
- explicit rule that web expansion is only used after a documented local-corpus gap

Acceptance criteria:
- disallowed domains do not enter the retrieval path
- web results are tagged with source role and origin before use
- the system logs when and why web expansion was triggered
- the answer path can still complete without web material when high-rank local sources suffice

### Phase 4: Evidence ledger and source-role controller

Deliverables:
- evidence ledger object model with:
  - claim text
  - supporting source(s)
  - anchor(s) where available
  - source-role level
  - contradiction markers
  - uncertainty markers
- controller rules that:
  - block unsupported core claims
  - downgrade weakly supported claims
  - preserve contradictory evidence instead of flattening it
  - prevent false elevation of lower-rank sources

Acceptance criteria:
- no core claim can reach the final answer without at least document-level support
- lower-rank material cannot be rendered as binding EU regulation
- contradictory evidence remains visible in the ledger
- the ledger can distinguish confirmed, interpretive, and open points

### Phase 5: Answer composer and interaction contract

Deliverables:
- final answer composer that only reads approved ledger entries
- answer rendering format with:
  - direct answer or synthesis
  - visible uncertainty handling
  - citations per claim block
  - optional distinction between confirmed, interpretive, and open points
- non-blocking clarification behavior for broad questions

Acceptance criteria:
- every answer includes document-level citations
- claim-specific statements include anchor references where available
- the answer does not flatten source hierarchy when multiple source roles are involved
- broad questions can still produce a useful first-pass answer without forcing a long interview loop

### Phase 6: Evaluation and hardening gate

Deliverables:
- scenario runner for:
  - primary success scenario
  - Scenario A
  - Scenario B
  - Scenario C
  - high-risk failure pattern
- manual review checklist for:
  - missing higher-ranked source
  - false elevation
  - weak anchor support
  - overconfident synthesis
- implementation hardening pass on the biggest failure cases found

Acceptance criteria:
- the system can produce reviewable outputs for all required scenarios
- the high-risk failure pattern is explicitly tested rather than assumed away
- known weak points are documented with either mitigation or conscious acceptance

## 7. Explicit non-goals for the first implementation

Do not expand V1 into these unless a later plan explicitly changes scope:
- persistent provenance graph
- specialist multi-agent orchestration
- broad member-state comparison engine
- automated freshness monitoring across the corpus
- opinion-piece or commentary-heavy retrieval as a primary answer basis
- separate end-user UI

## 8. Risk controls that must exist before implementation is considered ready

- A visible source hierarchy config, not hidden prompt logic only
- A visible allowlist for web expansion
- A hard rule that unsupported core claims do not reach answer composition
- A visible log or artifact for why web fallback was triggered
- A visible test for the "missed governing source" failure mode
- A visible fallback when anchors are weak or missing

## 9. Manual-effort minimization rules

Because user-side effort is itself a practical cost, implementation should minimize recurring manual burden:
- prefer simple, inspectable config files over heavy graph maintenance
- keep source ranking editable without code changes
- treat Germany or national expansion as optional add-on, not core ingestion burden
- keep corpus ingestion and evaluation scripts runnable in small batches
- avoid introducing control loops that require constant human steering per query

## 10. Ready-to-code gate

The plan is ready to move into implementation only when all of the following are true:
- repository shape and module boundaries are accepted
- the source catalog and hierarchy model are accepted
- the answer contract is accepted
- the evaluation gate is accepted
- no reviewer finds a blocker that reopens the architecture choice itself

If this gate passes, implementation should start with:
1. Phase 0 bootstrap
2. Phase 1 corpus foundation
3. one thin vertical slice through Phases 2 to 5 for Scenario C
4. then broaden to the primary success scenario and Scenario A

This ordering keeps the first coded slice narrow enough to debug while still exercising the full evidence-first pipeline.
