# Option A Implementation Plan

Status: revised after implementation-plan review wave 1
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

## 5. Operational contracts that must be fixed before core-path coding

### 5.1 Claim-state and answer contract

Treat the following as the minimum operational model:

- A `core claim` is any claim that directly answers the user's main question or asserts an obligation, allowance, prohibition, requirement, or protocol behavior.
- Each ledger entry must carry:
  - claim text
  - claim type
  - source role level
  - jurisdiction
  - support directness (`direct` or `indirect`)
  - citation quality (`anchor_grounded` or `document_only`)
  - contradiction status
  - final claim state

Allowed final claim states:
- `confirmed`
- `interpretive`
- `open`
- `blocked`

Initial V1 rules:
- `confirmed`
  - allowed only when at least one admissible high-rank source or referenced technical standard directly supports the claim
  - must have document-level citation
  - should have anchor-level citation when extractable
- `interpretive`
  - used when support is admissible but indirect, medium-rank, or only document-level because anchor extraction failed
  - must be visibly rendered as interpretive rather than settled
- `open`
  - used when the question is relevant but the search path remains under-supported, contradictory, or unresolved after allowed search steps
- `blocked`
  - used when no admissible support exists for a core claim
  - also used when only low-rank, disallowed, or falsely elevated material supports the claim

Block-versus-downgrade rule for V1:
- if the best available support is disallowed, low-rank only, or missing entirely for a core claim -> `blocked`
- if the best available support is admissible but indirect, medium-rank, or document-only due to technical anchor failure -> `interpretive`
- if two admissible high-rank sources materially conflict and no governing resolution is found -> `open`

Tie-break rules for conflicting admissible evidence:
- binding EU-level regulation outranks national implementation or project material
- among admissible same-rank sources, the more directly on-point provision wins for `confirmed`; otherwise downgrade to `open`
- national implementation material may explain or illustrate but must not override binding EU-level material

### 5.2 Retrieval-gap and web-expansion contract

Web expansion is allowed only when a `gap record` exists.

A gap record must contain at least:
- sub-question or claim target
- required source role level
- local source layers searched
- retrieval methods used
- candidate sources inspected
- reason local evidence is still insufficient
- next allowed action

For V1, a high-rank local layer is considered exhausted only when:
- lexical retrieval has been run on the required source layer
- semantic retrieval has been run on the required source layer
- the top local candidates for that required source role have been inspected, or the source catalog shows none are available
- no admissible direct-support passage was found for the sub-question

Web expansion may then occur only if:
- the gap record explicitly names official-web search as the next action
- the allowed target domain is in the allowlist
- the expected web source role is equal to or lower than the unresolved target layer and still acceptable under the requirements basis

Contradiction rule:
- contradictory local evidence does not itself justify web expansion
- web expansion is justified only if an official higher-rank or same-rank source could plausibly resolve the contradiction and is not already present locally

### 5.3 Anchor-degradation contract

When anchor extraction is weak or missing:
- the ingestion layer must mark the source as `document_only`
- the ledger entry must preserve that citation-quality flag
- the answer composer must render the claim with document-level citation only and not pretend anchor-level grounding exists

For core claims:
- a high-rank or referenced-standard source with document-only support may still be used, but only as:
  - `confirmed` if the governing source is clearly identified and the missing anchor is a technical extraction failure rather than an epistemic gap
  - otherwise `interpretive`
- medium-rank or lower-rank document-only evidence must not be used to confirm a core claim

## 6. Target repository shape

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
artifacts/
  eval_runs/
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
- `evaluation/`: scenario runner, result logging, and pass/fail helpers
- `artifacts/eval_runs/`: stored retrieval plans, gap records, approved ledgers, and final answers for manual inspection

## 7. Build sequence

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
- at least one negative fixture demonstrates the "governing source still missing" condition and produces a gap record instead of silently continuing

### Phase 3: Defensive web expansion

Deliverables:
- allowlisted web search/fetch path for official institutional, standards, and official project sources
- normalization step for fetched web material
- source-role assignment for web results before they can enter the evidence ledger
- explicit rule that web expansion is only used after a documented local-corpus gap
- minimum metadata contract for normalized web sources:
  - canonical URL
  - title
  - domain
  - source role level
  - jurisdiction if known
  - retrieval timestamp
  - citation quality flag

Acceptance criteria:
- disallowed domains do not enter the retrieval path
- web results are tagged with source role and origin before use
- the system logs when and why web expansion was triggered
- the answer path can still complete without web material when high-rank local sources suffice
- a normalized web source cannot support a core claim unless the minimum metadata contract is complete

### Phase 4: Evidence ledger and source-role controller

Deliverables:
- evidence ledger object model with:
  - claim text
  - supporting source(s)
  - anchor(s) where available
  - source-role level
  - contradiction markers
  - uncertainty markers
  - citation-quality flag
  - final claim state
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
- the controller implements the claim-state rules from section 5.1 and is testable on blocked, open, interpretive, and confirmed examples

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
- per-scenario artifact bundle containing:
  - retrieval plan
  - gap record
  - approved ledger
  - final answer
- implementation hardening pass on the biggest failure cases found

Acceptance criteria:
- the system can produce reviewable outputs for all required scenarios
- the high-risk failure pattern is explicitly tested rather than assumed away
- known weak points are documented with either mitigation or conscious acceptance
- scenario artifacts are stored so failures can be traced back to retrieval, normalization, controller logic, or answer composition

## 8. Explicit non-goals for the first implementation

Do not expand V1 into these unless a later plan explicitly changes scope:
- persistent provenance graph
- specialist multi-agent orchestration
- broad member-state comparison engine
- automated freshness monitoring across the corpus
- opinion-piece or commentary-heavy retrieval as a primary answer basis
- separate end-user UI

## 9. Risk controls that must exist before implementation is considered ready

- A visible source hierarchy config, not hidden prompt logic only
- A visible allowlist for web expansion
- A hard rule that unsupported core claims do not reach answer composition
- A visible claim-state decision table for confirmed, interpretive, open, and blocked outcomes
- A visible log or artifact for why web fallback was triggered
- A visible test for the "missed governing source" failure mode
- A visible fallback when anchors are weak or missing

## 10. Manual-effort minimization rules

Because user-side effort is itself a practical cost, implementation should minimize recurring manual burden:
- prefer simple, inspectable config files over heavy graph maintenance
- keep source ranking editable without code changes
- treat Germany or national expansion as optional add-on, not core ingestion burden
- keep corpus ingestion and evaluation scripts runnable in small batches
- avoid introducing control loops that require constant human steering per query

## 11. Ready-to-code gate

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
4. one second thin slice that explicitly tests a regulation-heavy or missed-governing-source case before broader expansion
5. then broaden to the primary success scenario and Scenario A

This ordering keeps the first coded slice narrow enough to debug while ensuring that the first hardening step does not ignore the architecture's main residual risk.
