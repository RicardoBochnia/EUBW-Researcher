# EUBW Agentic RAG Target Architecture

Status: reviewer-validated target draft
Date: 2026-05-06
Scope: target architecture only, not an implementation plan
Review validation: completed on 2026-05-06; evidence-governance,
agent-usability, and migration-feasibility reviewers reported satisfied with
no remaining blockers.

## 1. Purpose

This document defines the target architecture for an agent-facing answering and
data assistant for the eIDAS / EUBW context.

The system should answer arbitrary, realistic questions about legal,
technical, architectural, and operational EUBW topics without requiring a new
hand-authored intent for every benchmark family.

The goal is not a classic "question in, top-k chunks out, final answer"
pipeline. The goal is an evidence navigation system that lets an agent find
what is relevant, inspect the source basis, follow relationships, and then
produce a qualified answer with reviewable evidence.

## 2. Primary Design Position

The RAG layer is not the primary answer writer.

The RAG layer is the agent's knowledge navigation substrate:

- where sources live,
- what each source says at claim level,
- which claims are related,
- which source roles and legal statuses apply,
- which conflicts, gaps, or delegated questions are known,
- where the agent should read next.

The agent remains responsible for final synthesis. The system must therefore
support evidence-only operation as a first-class mode, not as an afterthought.

Hard boundary: the Knowledge Service and Source Reader must not generate
final-answer prose. They may emit structured summaries, labels, ranking
explanations, and reading suggestions only as navigational aids tied to source,
claim, chunk, concept, and relation IDs. Final answer synthesis is owned by the
agent or by a separate Answer Composer that consumes an explicit evidence
selection.

## 3. Target User And Operating Model

Primary user:

- an Answering/Data-Agent operating over a local eIDAS / EUBW knowledge base.

Secondary user:

- a human reviewer who inspects artifacts, sources, and traceability after the
  agent has answered.

Main workflow:

1. User asks a domain question.
2. Agent decomposes the question into likely evidence needs.
3. Knowledge service retrieves candidate claims, chunks, sources, relations,
   and open issues.
4. Agent reads the most important source passages directly.
5. Agent requests verification or ledger construction for the claims it wants
   to rely on.
6. Agent writes a qualified answer.
7. Runtime emits reviewable artifacts showing evidence, gaps, source roles,
   and answer/evidence alignment.

## 4. Architectural Principles

### 4.1 Claim-first discovery, verification-first acceptance

Discovery should start from broad claim, chunk, and relation retrieval.

Acceptance should remain strict:

- no final answer claim without source support,
- no proposal-stage material flattened into final law,
- no technical specification treated as binding legal authority,
- no broad fallback accepted for EUBW-shaped questions.

This combines the legacy EUBW repo's flexibility with EUBW-Researcher's
artifact discipline.

### 4.2 Intents are rendering aids, not the knowledge gateway

Specialized intents remain useful for:

- answer layout,
- regression cases,
- high-risk review gates,
- domain-specific checklists.

They must not be required for the system to discover relevant evidence.

An unseen question should still retrieve plausible claim clusters, related
sources, and open issues even when no specialized intent exists.

### 4.3 Evidence objects are more important than answer prose

The stable output for agents and reviewers is structured evidence, not only
the rendered answer.

Answer text is a product surface. Evidence objects are the review surface.

### 4.4 Source role and legal status are first-class data

The system must preserve both:

- source/evidence tier: `A`, `B`, `C`;
- binding level: `binding`, `proposed`, `official_non_binding`,
  `non_binding`, `unknown`.

The current `high` / `medium` / `low` source role can remain as a derived
runtime simplification, but it must not replace the richer source semantics.

Minimum source-governance policy:

- Tier A: binding or governing legal / regulatory material for the relevant
  jurisdiction and date, including adopted EU regulations and applicable
  implementing acts.
- Tier B: official non-binding, proposal-stage, delegated, explanatory, or
  project material that may contextualize or indicate direction but cannot by
  itself establish current binding law.
- Tier C: technical standards, specifications, literature, commentary, and
  practice material that may support technical, architectural, or interpretive
  claims but cannot be elevated into legal authority.

Binding-level rules:

- `binding` material may support current legal-obligation claims when
  jurisdiction, effective date, and locator are valid.
- `proposed` material must be rendered as proposal-stage and must not support
  final-law wording.
- `official_non_binding` material may explain or contextualize but must not
  override or fill gaps as if binding.
- `non_binding` material may support technical or interpretive context only.
- `unknown` material cannot support a core claim until reviewed or explicitly
  qualified.

The verifier must apply a claim-type / source-role compatibility matrix before
a claim can enter the approved ledger.

Calibration examples:

- EBW proposal material may support proposal-stage architecture and mandate
  direction, but not final-law obligations.
- Technical specifications and ARF material may support technical object,
  lifecycle, and conformance claims, but not legal authority unless incorporated
  by a binding source.

### 4.5 Corpus incompleteness must be visible

The system must avoid false completeness. If the relevant concept is missing
from the local corpus or the retrieved evidence is only partial, the answer
must expose that as a gap or open issue.

## 5. Conceptual Architecture

```text
User Question
    |
    v
Agent Reasoning Loop
    |
    +--> Knowledge Service
    |       |
    |       +--> Source Catalog
    |       +--> Structured Chunks
    |       +--> Claim Index
    |       +--> Relation Graph
    |       +--> Open Issue Store
    |       +--> Retrieval Indexes
    |
    +--> Source Reader
    |       |
    |       +--> article / section / page lookup
    |       +--> exact passage inspection
    |
    +--> Evidence Verifier
    |       |
    |       +--> source-role and binding-level checks
    |       +--> contradiction / gap checks
    |       +--> provisional-to-approved claim transition
    |
    v
Answer Composer
    |
    v
Reviewable Artifact Bundle
```

## 6. Core Data Layers

### 6.1 Source Catalog

The source catalog is the authority record for all local and accepted web
sources.

Required fields:

- `source_id`
- canonical URL
- local path
- title
- source group
- jurisdiction
- source type
- evidence tier
- binding level
- document status
- publication / version date when known
- hash / digest
- locator strategy

The catalog must preserve legacy IDs as `archive_source_id` or
`legacy_source_ids` while allowing EUBW-Researcher to keep normalized runtime
`source_id`s. Existing runtime `source_id`s must not be renamed unless a
versioned migration maps every artifact, benchmark, and review expectation.
`evidence_tier`, `binding_level`, legacy `group`, and `sha256` / digest are
imported metadata, not replacements for the current `source_role_level`,
`source_kind`, and `document_status` fields.

### 6.2 Structured Chunk Layer

Chunks are not arbitrary text windows. They should be source-structure-aware.

Preferred locators:

- article,
- recital,
- annex point,
- section heading,
- table,
- page,
- paragraph,
- line or extracted text offset where available.

Each chunk should retain:

- `chunk_id`,
- `source_id`,
- locator,
- normalized text,
- original text reference,
- source tier and binding metadata copied or joined from the source catalog.

### 6.3 Claim Layer

Claims are atomic, source-linked statements.

Required fields:

- `claim_id`,
- normalized statement,
- source IDs,
- chunk IDs,
- article / section references,
- topic,
- actor / action / object where useful,
- modality,
- evidence tier,
- binding level,
- status,
- notes / extraction provenance.

Claim status should distinguish at least:

- candidate,
- draft,
- reviewed,
- approved,
- deprecated.

The system may retrieve candidate and draft claims for discovery, but final
answers should clearly distinguish discovered claims from approved or
verification-passed claims.

### 6.4 Relation Graph

The relation graph links claims, chunks, sources, and concepts.

Core relation types:

- `defines`,
- `defined_in`,
- `requires`,
- `implements`,
- `delegates_to`,
- `amends`,
- `refers_to`,
- `narrows`,
- `broadens`,
- `exception_of`,
- `depends_on`,
- `conflicts_with`,
- `supports_interpretation`,
- `same_concept_as`.

Relations may be generated automatically, but relation confidence and review
status must be visible.

Graph completeness must never be assumed. Missing relation edges are not proof
that no relationship exists.

### 6.5 Concept And Terminology Layer

Concepts are stable navigation objects for multilingual, acronym-heavy, and
domain-shifting questions.

Required fields:

- `concept_id`,
- canonical label,
- German and English aliases,
- umlaut / ASCII variants,
- acronyms and false friends,
- source-specific terms,
- related concepts,
- linked claims, chunks, sources, and open issues,
- review status.

The concept layer exists to help an agent move from user language to source
language without requiring a question-specific intent. It should support terms
such as `EUBW`, `EBW`, `Business Wallet`, `European Business Wallet`,
`Mandat`, `Vertretungsrecht`, `delegation`, `LoTE`, `QTSP`, `authentic
source`, and similar variants.

### 6.6 Open Issue Store

Open issues are first-class knowledge objects, not only answer prose.

Required fields:

- `issue_id`,
- issue statement,
- affected concepts / claims / sources,
- affected answer facets,
- reason the issue is open,
- evidence that bounds the issue,
- severity,
- answer impact,
- `blocks_claim_ids`,
- `qualifies_claim_ids`,
- resolution condition,
- review owner,
- status,
- last reviewed date.

Open issues must be answer-governing. If an unresolved issue blocks or
qualifies a claim, verification must attach it and the answer composer must
withhold or qualify the affected claim.

Examples:

- concrete EBW mandate format not yet specified,
- subdelegation depth unresolved,
- old Wallet Unit revocation after migration not settled,
- register correction process context-dependent.

## 7. Retrieval Architecture

### 7.1 Retrieval Must Be Multi-Channel

The knowledge service should expose several retrieval channels:

- lexical source/chunk search,
- lexical claim search,
- semantic claim search,
- semantic chunk search,
- relation expansion,
- concept / terminology lookup,
- source-specific lookup,
- open-issue lookup.

No single retriever is trusted alone. Retrieval results are merged,
deduplicated, ranked, and annotated by evidence policy. In discovery mode,
policy must partition and label results by source role, binding level, document
status, review status, and admissibility rather than silently filtering out
lower-tier, contradictory, proposal-stage, or interpretive material. Hard
filtering belongs to explicit agent filters, source-admissibility controls, or
verification / ledger acceptance.

Semantic search may start as terminology / alias expansion plus full-text
search. Dense embeddings are useful, but they should be evidence-gated and
evaluated before they become a core dependency.

### 7.2 Query-Time Discovery Flow

For an arbitrary question:

1. Normalize terminology, including German/English aliases and ASCII/umlaut
   variants.
2. Retrieve broad claim candidates.
3. Retrieve chunk candidates independently.
4. Bridge chunk candidates back to claims where possible.
5. Expand relations from top claims and sources.
6. Retrieve open issues connected to those claims and concepts.
7. Build provisional evidence clusters.
8. Return clusters to the agent with ranked source and reading suggestions.

### 7.3 Provisional Evidence Clusters

The primary retrieval product should be a set of evidence clusters, not a
single answer.

Cluster fields:

- cluster ID,
- label,
- matched concepts,
- candidate claims,
- supporting chunks,
- source IDs,
- relation edges,
- open issues,
- confidence / sufficiency signals,
- missing evidence signals.

Example cluster labels for a provider-change question:

- `portability and migration object`,
- `device-bound reissuance`,
- `non-device-bound copying`,
- `wallet unit trust re-binding`,
- `transaction log restoration`,
- `mandate and access-control continuity`,
- `open issues`.

## 8. Agent Tool Surface

The agent-facing API should support evidence navigation directly.

Required operations:

- `search_claims(question_or_terms, filters)`
- `search_chunks(question_or_terms, filters)`
- `build_evidence_clusters(question, filters=None)`
- `lookup_source(source_id)`
- `list_source_structure(source_id)`
- `open_passage(source_id, locator, context=None)`
- `open_adjacent_passages(source_id, locator, before=1, after=1)`
- `get_claim_evidence(claim_id)`
- `trace_concept(term_or_concept_id, include_aliases=True,
  include_related=True)`
- `expand_relations(claim_ids_or_source_ids, relation_types, depth)`
- `compare_sources(source_ids_or_claim_ids)`
- `find_counterevidence(claim_or_question, filters=None)`
- `get_open_issues(claim_ids_or_terms)`
- `find_missing_facets(question, evidence_clusters=None)`
- `explain_result(result_id_or_cluster_id)`
- `verify_claims(candidate_claims_or_cluster)`
- `write_reviewable_bundle(question, answer, evidence_selection)`

All retrieval and navigation operations default to `evidence_only=True`. In
evidence-only mode they return IDs, locators, source-role metadata, snippets or
quotable spans, relation edges, sufficiency / gap signals, and reading
suggestions, not final-answer prose.

Public facade boundary:

`ResearchRuntimeFacade` remains the stable package-root API for agents. The
operations above are Knowledge Service operations behind that facade, or future
versioned additions to it. They must be additive to the existing
`answer_question`, `evidence_only`, and `write_reviewable_artifact_bundle` modes
and must not bypass ledger construction, gap recording, corpus coverage, web
governance, or review-bundle writing without an explicit facade contract version
bump.

## 9. Verification And Ledger Model

The verifier turns discovered evidence into reviewable support.

It should distinguish:

- discovered claim,
- candidate support,
- governing support,
- approved claim,
- interpretive claim,
- open claim,
- blocked claim.

Verification checks, each producing pass / fail / qualified status and a stored
decision reason:

- source exists in catalog,
- source admission policy is recorded,
- source hash / version matches the approved catalog entry,
- locator is resolvable,
- claim text is supported by the cited passage,
- claim type is compatible with the source tier and binding level,
- binding level, document status, jurisdiction, and effective-date qualifiers
  are preserved,
- higher-authority candidate sources were considered where required,
- contradiction candidates were checked,
- relevant open issues were attached,
- answer use is allowed only for `approved` or explicitly qualified
  `interpretive` claims,
- blocked claims remain in artifacts but cannot appear as final answer claims.

Per-claim verification records must include `claim_id`, `claim_type`,
verification result, decision reason, source IDs, chunk IDs, locators, source
tier, binding level, document status, attached open issues, contradiction
signals, and answer-use permission.

The ledger should not require all claims to be known before retrieval. It must
support dynamic, question-time provisional claims generated from retrieved
clusters and then verified before answer use.

## 10. Answering Model

The answer composer should be downstream of evidence selection.

Default answer shape:

- Kurzantwort / direct answer,
- Normative evidence,
- Technical / interpretive context,
- Source hierarchy and caveats,
- Open issues,
- optional architecture assumptions.

For questions that are explicitly exploratory or architectural, the answer may
present model proposals, but must label them as proposals when no direct legal
or technical rule exists.

The composer must not invent completeness. If the evidence only supports
building blocks, the answer should say that directly.

The answer composer consumes selected evidence; it is not the retrieval layer.
If it is implemented as a separate component, it must be allowed to organize,
qualify, and phrase the answer, but not to create source support outside the
verified evidence selection.

## 11. Reviewable Artifact Bundle

Every non-trivial answer run should be able to produce:

- `final_answer.txt`,
- `retrieval_plan.json`,
- `ingestion_report.json`,
- `evidence_clusters.json`,
- `selected_evidence.json`,
- `ledger_entries.json`,
- `approved_ledger.json`,
- `claim_verification.json`,
- `pinpoint_evidence.json`,
- `source_hierarchy_report.json`,
- `relation_graph_slice.json`,
- `open_issues.json`,
- `gap_records.json`,
- `web_fetch_records.json`,
- `answer_alignment.json`,
- `blind_validation_report.json`,
- `manual_review.json`,
- `manual_review_report.md`,
- `corpus_coverage_report.json` where applicable.

Existing EUBW-Researcher artifact names are the compatibility floor. The target
may add `evidence_clusters.json`, `selected_evidence.json`,
`claim_verification.json`, `source_hierarchy_report.json`,
`relation_graph_slice.json`, `open_issues.json`, and
`navigation_session_trace.json`, but must not remove or rename the current
review surfaces: `retrieval_plan.json`, `ingestion_report.json`,
`ledger_entries.json`, `approved_ledger.json`, `gap_records.json`,
`web_fetch_records.json`, `pinpoint_evidence.json`,
`answer_alignment.json`, `blind_validation_report.json`,
`manual_review_report.md`, and `corpus_coverage_report.json` where applicable.

`manual_review.json` is an automated prefill surface. `manual_review_report.md`
remains the human-readable review report.

Minimum artifact invariants:

- every substantive final-answer claim has a stable `claim_id`;
- every `claim_id` in the final answer appears in `answer_alignment.json`;
- every approved or interpretive `claim_id` appears in `approved_ledger.json`;
- every ledger entry links to `source_id`, `chunk_id`, locator, source tier,
  binding level, document status, and verification result;
- every blocked, open, or insufficiently supported claim appears in
  `claim_verification.json` or `gap_records.json`;
- any relevant open issue is linked from the affected claim and surfaced in the
  answer caveats;
- fetched or refreshed sources include digest, retrieval timestamp, admission
  policy, and provenance.

## 12. Corpus Baseline For EUBW-Grade Answers

The default EUBW corpus should include at least:

- eIDAS 2 / Regulation (EU) 2024/1183,
- relevant implementing acts,
- EBW Proposal COM(2025)838,
- EBW Annex,
- Council Annex material when used as official non-binding context,
- TS01 wallet trust mark,
- TS02 provider information,
- TS03 wallet unit attestation,
- TS05 / TS06 relying party registration sources,
- TS10 data portability and export,
- ARF main,
- relevant PubEAA / authentic-source implementing act material,
- RP registration / access certificate material,
- trust-list / LoTE material where trust-chain questions are in scope.

Each source must carry its tier and binding semantics. Inclusion in the corpus
does not imply equal authority. Corpus items that are not yet present in
`configs/real_corpus_selection.yaml` or the curated catalog are admission
pending, not silently assumed available.

## 13. Evaluation Model

Evaluation must test generalization, not only benchmark-specific intent
coverage.

Required benchmark classes:

- known regression questions,
- paraphrased questions,
- German/English mixed questions,
- adjacent unseen questions,
- source-conflict questions,
- architecture-bucket questions,
- open-issue questions,
- false-friend questions where a plausible source is not governing,
- missing-source questions.

Key acceptance criteria:

- relevant claim clusters retrieved without question-specific intent,
- decisive sources surfaced,
- agent can reach and re-read decisive passages without broad raw-document
  hunting,
- source-role and binding-level qualifiers preserved,
- open issues visible,
- broad fallback rejected for EUBW-shaped questions,
- answer remains reusable without raw-document reconstruction,
- reviewer can trace answer claims back to passages and claim IDs.

## 14. Migration Strategy At Target Level

This target architecture assumes reuse rather than a greenfield rebuild.

Reuse from legacy EUBW:

- source catalog concepts,
- legacy source-ID metadata through explicit crosswalks,
- chunks,
- claims,
- relations,
- open issues,
- benchmarks,
- answer-audit ideas,
- dense / semantic index lessons.

Reuse from EUBW-Researcher:

- runtime facade,
- reviewable artifact bundles,
- source governance,
- ledger and gap concepts,
- test and evaluation harness,
- answer/evidence alignment checks.

Architectural cut:

- Keep EUBW-Researcher as the target runtime shell.
- Add or replace its internal retrieval core with a claim-first knowledge
  service.
- Preserve specialized intents only as optional presentation and regression
  overlays.

Migration boundary:

Legacy chunks, claims, relations, open issues, benchmarks, and indexes are
import candidates or reference assets, not automatically trusted runtime state.
Imported claims must initially land as `candidate` or `draft` unless they pass
schema validation, source-ID crosswalk validation, locator resolution, and
sample manual review. Imported relations remain supplemental unless both
endpoint claims are verified. The target does not require copying the full
legacy persistent knowledge-base stack; a JSONL / SQLite adapter or derived
in-repo cache is acceptable until evaluation proves a stronger store is needed.

Migration-readiness acceptance gate:

- source crosswalk exists for imported legacy and runtime IDs,
- one representative legacy claim file imports as candidates,
- one relation slice imports as supplemental relation data,
- one arbitrary unseen question runs through the existing facade and emits the
  new evidence-cluster artifact without dropping existing artifacts.

## 15. Non-Goals

This target architecture does not require:

- arbitrary open-web search,
- a full external RAG framework as the core,
- a graph database as the first implementation step,
- fully automatic legal truth adjudication,
- complete graph coverage,
- replacing human review,
- turning every retrieved claim into an accepted answer claim.

Frameworks may be used selectively for indexing, reranking, or graph storage,
but the core contract is the evidence model, not a framework.

## 16. Risks And Controls

### Risk: false completeness from graph retrieval

Control:

- graph slices must include completeness caveats;
- missing edges are not negative evidence;
- open issues and gap records are surfaced.

### Risk: noisy claim retrieval

Control:

- claim status and confidence are visible;
- dynamic claims require verification before answer use;
- source hierarchy filters run after retrieval.

### Risk: proposal-stage drift

Control:

- binding level is preserved as first-class data;
- final wording must distinguish binding law, proposal, official non-binding,
  and technical project material.

### Risk: overfitting to benchmarks

Control:

- acceptance requires adjacent unseen questions;
- new benchmark questions should not automatically imply new hard-coded
  intents.

### Risk: agent over-synthesis

Control:

- answer alignment checks compare final answer claims to selected evidence;
- unsupported claims are blocked or downgraded;
- model proposals must be labeled.

## 17. Definition Of Done For This Target Architecture

The target architecture is acceptable when reviewers agree that it:

- supports arbitrary EUBW/eIDAS questions through claim-first discovery,
- preserves source-role and binding-level semantics,
- gives an agent direct evidence-navigation tools,
- preserves or improves EUBW-Researcher's reviewability,
- reuses the strongest legacy EUBW knowledge assets,
- avoids making specialized intents the primary knowledge gateway,
- states risks and non-goals clearly enough to guide the later implementation
  plan.
