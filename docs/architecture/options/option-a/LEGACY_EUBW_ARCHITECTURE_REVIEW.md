# Legacy EUBW Architecture Review

Status: exploratory architecture note
Reviewed legacy repository: `/Users/ricardo/Documents/GitHub/EUBW`
Current target architecture: [PLAN.md](./PLAN.md), [V2_PLAN.md](./V2_PLAN.md), [V2_2_PLAN.md](./V2_2_PLAN.md)

## 1. Purpose

This note reviews the older `EUBW` repository as an architecture reference for the current `EUBW-Researcher` Option A system.

Goal:
- identify what the older project built well
- identify where complexity accumulated
- extract only the architecture extensions that would improve the current Option A system without recreating the earlier complexity explosion

## 2. Legacy architecture in one view

The older repository is not a single query runtime.
It is a layered research pipeline with several persistent artifact strata.

Main layers:

1. **Source and catalog layer**
   - local source archive under `sources/`
   - source catalogs and coverage audit

2. **Chunk layer**
   - separate A-first chunk basis
   - separate B/C chunk basis

3. **Claim layer**
   - claim seed generation
   - draft claim generation

4. **Relation layer**
   - relation candidate extraction
   - optional relation expansion during answering

5. **Retrieval-index layer**
   - lexical retrieval over JSONL artifacts
   - optional SQLite FTS
   - optional semantic hash index
   - optional dense bi-encoder index

6. **Profile and query orchestration layer**
   - many query profiles
   - topic-aware routing
   - single-pass and multi-pass query flows

7. **Agent/runtime facade**
   - `agent_tools/` as a stable runtime API over the query core
   - deterministic router
   - structured evidence contract

8. **Evaluation and operational governance**
   - schema validation
   - gold benchmarks
   - smoke tests
   - manual review baseline dataset
   - generated current-state/status summary

In effect, the legacy repo became a local knowledge-base platform with a growing retrieval laboratory around it.

## 3. Where complexity accumulated

### A. Too many persistent intermediate layers

The pipeline stores and maintains:
- catalogs
- A chunks
- B/C chunks
- claim seeds
- claim drafts
- relation candidates
- answer records
- multiple retrieval indexes
- multiple manifests and batch manifests

This gives strong inspectability, but it also creates high rebuild, consistency, and maintenance cost.

### B. Topic and profile combinatorics

The repo accumulated many topics and many query profiles, each with slightly different behavior.
That is useful for experimentation, but it pushes the system toward profile-selection overhead instead of product-level runtime clarity.

### C. Optional retrieval layers turned into a matrix

The retrieval path grew from:
- lexical
to
- lexical + FTS
- lexical + semantic
- lexical + dense
- reranked variants
- multi-pass combinations

Each layer is defensible in isolation.
Together they create calibration burden and a larger surface for silent interaction effects.

### D. Agent abstraction on top of an already rich core

`agent_tools/` is reasonable on its own, but in the legacy repo it sits on top of a query/profile stack that is already operationally dense.
That makes the agent-facing layer cleaner while the underlying system remains hard to reason about end to end.

### E. Evaluation became broad and partially heterogeneous

The legacy repo has strong validation discipline.
The tradeoff is that it maintains several proof channels at once:
- core gold benchmarks
- paraphrase benchmarks
- dense prototype benchmarks
- manual review dataset
- state snapshots

This improves confidence, but also makes it easier for the project to grow sideways into verification infrastructure.

## 4. What is still valuable for the current Option A system

These are the strongest patterns worth carrying over.

### 1. A stable agent-facing runtime contract

The legacy `agent_tools/` layer is a good pattern:
- one stable runtime entry
- deterministic routing
- structured evidence output
- separation between internal core complexity and external agent usage

For the current project, this argues for keeping the CLI/runtime contract stable and explicit rather than exposing internal modules ad hoc.

### 2. Reproducible corpus and status reporting

The legacy repo is strong at:
- source catalogs
- coverage audit
- generated status summaries
- explicit artifact validation

For the current project, the main transferable idea is not the whole pipeline but the habit of generating:
- compact coverage/status artifacts
- explicit corpus-selection reports
- reproducible proof of what the current local corpus actually contains

### 3. Manual-review datasets built from real questions

The manual review baseline in the legacy repo is a useful pattern.
For Option A, this suggests a narrow, curated real-question set for ongoing regression and review, rather than relying only on synthetic scenarios.

### 4. Selective, local retrieval augmentation

The old project is right that lightweight local retrieval augmentation can be valuable.
The best candidate to borrow is a minimal local lexical index over already normalized artifacts if the current corpus grows materially.

This is much more attractive than jumping directly into heavier semantic stacks.

### 5. Explicit coverage and open-issue signaling

The legacy use of:
- coverage hints
- backlog mirrors
- open issues

maps well to the current Option A philosophy.
The useful lesson is that the system should say where it is thin instead of hiding uncertainty behind polished answer text.

## 5. What is only conditionally useful

These ideas should be adopted only if a concrete pain point appears and a tight proof case exists.

### 1. Relation candidates

Conditionally useful if:
- they remain narrow
- they are generated from already accepted evidence artifacts
- they stay supplemental

Do not adopt them as a new primary reasoning substrate.
They are only worth it if they reduce repeated manual cross-document stitching for a clearly recurring question family.

### 2. FTS or similar local index

Conditionally useful if:
- corpus size grows enough that current retrieval becomes slow or recall-poor
- the index stays derivative of existing artifacts
- the authority policy remains downstream and unchanged

This is a reasonable future extension, but not something to add just because the old repo has it.

### 3. Dense / semantic retrieval

Conditionally useful only if:
- there is measured evidence of repeated recall failure on paraphrased or indirect questions
- the gain survives the current real-corpus evaluation gate
- the dense layer stays optional and tightly benchmarked

Without that proof, it is more likely to recreate retrieval complexity than to improve practical answer quality.

### 4. Multi-pass analysis

Conditionally useful only if:
- one concrete question family repeatedly benefits from a strict-plus-broader paired answer
- the outputs remain inspectable
- the additional pass does not become the default answer path for everything

The legacy repo shows that multi-pass workflows are feasible.
It also shows how easily they become another permanent branch in the runtime tree.

## 6. What should clearly not be copied

### 1. Do not copy the full persistent knowledge-base stack

The current Option A system should not grow into:
- persistent claim seed pipelines
- persistent draft-claim stores as the center of product answering
- broad relation candidate stores
- multiple parallel manifests for every intermediate stage

That architecture is powerful for research infrastructure, but too heavy for the current product shape.

### 2. Do not copy the profile explosion

The old repo accumulated many profiles because it doubled as an experimentation platform.
For the current system, a small number of explicit modes and gates is materially better than profile sprawl.

### 3. Do not copy the retrieval-layer matrix as baseline

Lexical + FTS + semantic + dense + reranker + multi-pass is not a sensible default shape for the current project.
If more retrieval power is needed later, it should be added one layer at a time behind explicit benchmarks.

### 4. Do not copy separate complexity just to preserve optionality

The older repo pays a real cost for:
- extra environments
- extra manifests
- extra benchmark sets
- extra routing logic

The current project should not adopt parallel complexity preemptively.
It should only absorb extensions when a specific failure mode justifies them.

### 5. Do not drift back toward graph-like persistence through relations

The old repo is not literally Option B, but a large claim/relation knowledge base starts to reproduce some of the same maintenance and false-completeness risks.
That is exactly what the current Option A architecture chose to avoid.

## 7. Recommended architecture extensions from this review

If the current project is extended, the highest-value sequence would be:

1. **Add a narrow real-question regression pack**
   - keep it small
   - model it after the legacy manual-review idea
   - use it to catch usefulness regressions, not just structural ones

2. **Add compact corpus/status artifacts**
   - selection summary
   - coverage summary
   - current-state snapshot

3. **Keep a stable agent runtime contract**
   - one clear entry path
   - structured review artifacts
   - no silent fallback to internal subsystems

4. **Only if justified later: add a lightweight lexical index**
   - derivative of current artifacts
   - no authority-policy change
   - benchmark-gated

Everything beyond that should require an explicit new work order.

## 8. Bottom line

The older `EUBW` repo contains good ideas, but most of its value is in:
- validation discipline
- corpus/accounting discipline
- stable runtime contracts

Its main risk for the current project is not wrongness.
Its main risk is that it normalizes a large research-platform architecture with too many persistent layers, profiles, and optional retrieval branches.

The right move for the current Option A system is therefore:
- borrow the governance and proof patterns
- borrow only the lightest retrieval/runtime improvements
- avoid copying the large persistent knowledge-base and retrieval-lab shape
