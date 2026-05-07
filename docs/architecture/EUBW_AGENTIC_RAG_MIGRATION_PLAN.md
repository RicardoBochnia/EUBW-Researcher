# EUBW Agentic RAG Migration And Implementation Plan

Status: reviewer-validated migration draft
Date: 2026-05-06
Scope: implementation plan for the reviewer-validated target architecture, not
the implementation itself
Target basis:
`docs/architecture/EUBW_AGENTIC_RAG_TARGET_ARCHITECTURE.md`
Review validation: completed on 2026-05-06; implementation-feasibility,
evidence-governance / verification, and evaluation / rollout reviewers reported
satisfied with no remaining blockers.

## 1. Purpose

This document turns the agentic RAG target architecture into an incremental
migration plan for EUBW-Researcher.

The plan assumes that EUBW-Researcher remains the target runtime shell and that
the legacy EUBW repository remains a source of reusable knowledge assets, not a
runtime to copy wholesale.

The implementation should improve arbitrary eIDAS / EUBW question answering
without making every strong benchmark answer depend on a new specialized intent
or hard-coded claim target.

## 2. Migration Strategy

Use a strangler migration inside EUBW-Researcher.

Do not replace the current runtime in one move. Add the agentic knowledge layer
behind the existing `ResearchRuntimeFacade`, run it in evidence-only and
artifact-producing modes first, compare it against the current path, then let it
take over discovery and answer support once gates pass.

Primary migration rule:

- retrieval may become broader and more flexible early;
- final-answer admission must remain strict at every step.

## 3. Non-Negotiable Boundaries

- `ResearchRuntimeFacade` remains the public package-root contract until an
  explicit version bump is approved.
- Existing facade modes remain supported:
  `answer_question`, `evidence_only`, and
  `write_reviewable_artifact_bundle`.
- Existing artifact names remain the compatibility floor:
  `retrieval_plan.json`, `ingestion_report.json`, `ledger_entries.json`,
  `approved_ledger.json`, `gap_records.json`, `web_fetch_records.json`,
  `pinpoint_evidence.json`, `answer_alignment.json`,
  `blind_validation_report.json`, `manual_review.json`,
  `manual_review_report.md`, and `corpus_coverage_report.json` where
  applicable.
- Legacy EUBW chunks, claims, relations, open issues, and benchmarks enter as
  candidate/reference assets until validated.
- Knowledge Service and Source Reader operations must remain evidence-only by
  default and must not generate final-answer prose.
- Source governance must preserve source role, source kind, document status,
  evidence tier, binding level, jurisdiction, and locator.
- Broad fallback answers must stay rejected for EUBW-shaped questions.

## 4. Current-State Assessment

EUBW-Researcher already has strong pieces to preserve:

- `src/eubw_researcher/runtime_facade.py` defines the stable agent-facing
  facade.
- `src/eubw_researcher/pipeline.py` coordinates query analysis, retrieval,
  ledger construction, gap records, web governance, answer composition, and
  blind validation.
- `src/eubw_researcher/models/types.py` defines most current runtime payloads.
- `src/eubw_researcher/evidence/ledger.py` enforces hierarchy, directness,
  contradiction, and document-status caps.
- `src/eubw_researcher/evaluation/runner.py` writes the current artifact
  bundle and evaluates scenario gates.
- `configs/real_corpus_selection.yaml`, `configs/source_hierarchy.yaml`,
  `configs/terminology.yaml`, `configs/retrieval_usefulness_cases.yaml`, and
  the real-question-pack configs already provide operational test surfaces.

The legacy EUBW repo has strong reusable assets:

- source/chunk/claim JSONL layers under `knowledge/`;
- A/B/C and binding-level source semantics;
- claim and relation candidates;
- open issues and benchmark sets;
- stable agent-tool lessons around `evidence_only`;
- hybrid retrieval experience with FTS, relation expansion, and optional
  semantic/reranking layers.

The gap is not one missing intent. The gap is that EUBW-Researcher still treats
intent-specific claim targets as the main knowledge gateway. The new layer must
let an agent discover claim clusters, read passages, inspect source hierarchy,
and verify selected evidence even when no specialized intent exists.

## 5. Target Implementation Shape

Add a new internal package:

- `src/eubw_researcher/knowledge/`

Recommended modules:

- `models.py`: candidate claims, structured chunks, concepts, relations, open
  issues, evidence clusters, verification records.
- `source_crosswalk.py`: runtime source IDs, legacy source IDs, archive IDs,
  digest and locator validation.
- `legacy_import.py`: import candidates from legacy EUBW JSONL / CSV assets.
- `concepts.py`: terminology and alias graph over current and imported corpus.
- `indexes.py`: FTS-backed claim and chunk indexes plus in-memory fallback.
- `source_reader.py`: source structure, passage lookup, adjacent passage lookup.
- `service.py`: evidence-only Knowledge Service operations.
- `clusterer.py`: provisional evidence-cluster construction.
- `verifier.py`: source-governance and claim-verification policy.

The package is internal at first. It is reached through the existing pipeline
and facade, not by making a new public API surface on day one.

## 6. Phase 0: Baseline And Guardrails

Goal:

- freeze the observable baseline before changing retrieval behavior.

Implementation tasks:

- Add a dated benchmark note that records current A1 vs legacy EUBW gaps for
  Q1-Q8 and selected adjacent unseen questions.
- Re-run or document the current commands:
  - `python3 scripts/build_real_corpus_catalog.py`
  - `python3 scripts/run_unit_tests.py`
  - `python3 scripts/run_real_question_pack.py --all`
  - `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Store the baseline artifact paths and catalog/runtime digests in a migration
  readiness note or manifest.
- Mark Q6-Q8 as generalization benchmarks, not as prompts that automatically
  justify new specialized intents, claim targets, source-family rules, facets,
  aliases, allowlist entries, or rendering special cases.
- Freeze the migration benchmark and holdout packs before implementation of the
  Knowledge Service starts.

Acceptance gate:

- the current baseline is reproducible enough to compare later phases;
- no implementation work starts without knowing which artifact surfaces and
  frozen questions will be compared.

Generalization anti-overfit gate:

- no new benchmark-specific intent, claim target, source allowlist, facet,
  hard-coded source family, alias, or rendering special case may be added for
  Q6-Q8 or holdout questions;
- terminology additions are allowed only when they are corpus-derived,
  source-language-backed, and applied globally rather than to a single question;
- if a new target or facet is proposed, it must be justified by a reusable
  domain concept and tested on at least one holdout outside the question family
  that motivated it;
- migration acceptance must report whether any benchmark-specific code or
  config was added after the pack was frozen.

## 7. Phase 1: Data Contracts And Source Governance

Goal:

- introduce the target evidence model without changing answer behavior.

Implementation tasks:

- Extend or add dataclasses for:
  - `EvidenceTier`;
  - `BindingLevel`;
  - source aliases / legacy IDs;
  - publication date, version date, effective date, and successor / predecessor
    metadata where known;
  - candidate claim status;
  - structured chunk locator metadata;
  - concept records;
  - relation records;
  - open issue records with `issue_id`, `issue_statement`, affected concepts /
    claims / sources, affected answer facets, `reason_open`,
    `bounded_by_evidence`, severity, answer impact, `blocks_claim_ids`,
    `qualifies_claim_ids`, resolution condition, review owner, status, and last
    reviewed date;
  - evidence clusters;
  - claim verification records.
- Extend `SourceCatalogEntry` and `ArchiveSourceSelection` carefully with
  optional fields rather than breaking existing catalog loading.
- Update `src/eubw_researcher/corpus/catalog.py`, archive config loading,
  corpus-state digest generation, ingestion-cache invalidation, and catalog
  writing so optional governance fields are preserved rather than silently
  dropped.
- Add a source-ID crosswalk artifact, for example
  `artifacts/real_corpus/source_crosswalk.json`, generated from the curated
  catalog and imported legacy metadata.
- Add a source-governance policy config, for example
  `configs/source_governance.yaml`, containing the claim-type / source-role /
  binding-level compatibility matrix and effective-date handling rules.
- Add serialization tests for all new public or artifact-bound structures.

Acceptance gate:

- all existing tests pass unchanged;
- existing catalogs still load;
- catalog read/write round-trips preserve `evidence_tier`, `binding_level`,
  legacy IDs, version / effective-date fields, digest metadata, and locator
  strategy when present;
- corpus-state IDs and ingestion caches change when governance-relevant catalog
  metadata changes;
- artifact writers can serialize the new optional fields when present;
- source-governance fields survive catalog, ingestion, artifact, and facade
  serialization;
- no existing `source_id` is renamed.

## 8. Phase 2: Legacy Knowledge Import As Candidates

Goal:

- make legacy EUBW knowledge discoverable without making it authoritative.

Implementation tasks:

- Add a guarded importer script:
  - `scripts/import_legacy_knowledge.py`
- External full-import input root is optional and configurable:
  - default developer convenience path:
    `/mnt/c/Users/Admin/PycharmProjects/EUBW/knowledge`
  - tests must not require that path.
- Add small in-repo legacy import fixtures under `tests/fixtures/legacy_knowledge/`
  covering at least one source, chunk, claim, relation, open issue, and benchmark
  record.
- Default output root:
  - `artifacts/knowledge/imported_legacy/`
- Import in this order:
  1. source metadata and source-ID aliases,
  2. chunks,
  3. draft claims / claim candidates,
  4. relation candidates,
  5. open issues,
  6. benchmark questions.
- Validate every imported record against schema.
- Validate source IDs through the crosswalk.
- Validate locators for every imported claim that is eligible to leave
  `candidate` / `draft` status. Bulk import may keep unresolved-locator claims
  as candidates, but unresolved locators block promotion.
- Assign imported claims `candidate` or `draft` status unless explicitly
  reviewed in the new repo.
- Require schema validation, source-ID crosswalk validation, locator
  resolution, source digest match, and sample manual review before any imported
  claim can be promoted beyond `candidate` / `draft`.
- Assign imported relations supplemental status unless both endpoint claims are
  verified.
- Emit an import report with counts, rejects, unresolved sources, unresolved
  locators, and review samples.

Acceptance gate:

- fixture import passes without the external legacy repo present;
- one representative legacy claim file imports as candidates;
- one relation slice imports as supplemental relation data;
- unresolved source IDs and locators are visible, not silently dropped;
- promoted imported claims have per-claim promotion evidence;
- imported data cannot appear in `approved_ledger.json` without verification.

## 9. Phase 3: Knowledge Service V0

Goal:

- expose evidence-navigation primitives behind the current runtime boundary.

Implementation tasks:

- Implement `KnowledgeService` operations internally:
  - `search_claims(question_or_terms, filters)`;
  - `search_chunks(question_or_terms, filters)`;
  - `build_evidence_clusters(question, filters=None)`;
  - `lookup_source(source_id)`;
  - `list_source_structure(source_id)`;
  - `open_passage(source_id, locator, context=None)`;
  - `open_adjacent_passages(source_id, locator, before=1, after=1)`;
  - `get_claim_evidence(claim_id)`;
  - `trace_concept(term_or_concept_id, include_aliases=True, include_related=True)`;
  - `expand_relations(claim_ids_or_source_ids, relation_types, depth)`;
  - `compare_sources(source_ids_or_claim_ids)`;
  - `find_counterevidence(claim_or_question, filters=None)`;
  - `get_open_issues(claim_ids_or_terms)`;
  - `find_missing_facets(question, evidence_clusters=None)`;
  - `explain_result(result_id_or_cluster_id)`.
- Keep all operations evidence-only. They return IDs, locators, snippets,
  source metadata, relation edges, confidence signals, and reading suggestions.
- Implement FTS indexes over imported claims and chunks. Keep scan fallback for
  deterministic tests and cache failures.
- Extend compatibility plumbing before claiming artifact emission:
  - `AnswerResult` gets optional evidence-cluster and navigation fields;
  - `AgentRuntimeResult` exposes them only as additive optional fields or through
    an explicit result-schema bump;
  - `write_artifact_bundle` writes the new artifacts;
  - real-question-pack artifact expectations include the new optional artifacts;
  - facade tests prove old callers still work when fields are absent.
- Add `navigation_session_trace.json` and `evidence_clusters.json` as optional
  artifacts in review bundles.

Measurable acceptance gate:

- an arbitrary unseen EUBW question returns evidence clusters without a
  specialized intent;
- each accepted cluster includes at least one decisive source candidate, source
  role, binding level, document status, claim/chunk IDs, and a locator;
- the agent can jump from a cluster to source structure, exact passage, and
  adjacent passages;
- open issues and missing facets are visible when applicable;
- broad fallback clusters are rejected or marked insufficient for EUBW-shaped
  questions;
- no final answer prose is generated by the Knowledge Service.

## 10. Phase 4: Parallel Discovery Path In The Pipeline

Goal:

- run agentic discovery next to the current intent-target path.

Implementation tasks:

- Add a feature flag in `configs/runtime.yaml`, for example:
  - `knowledge_service.enabled`;
  - `knowledge_service.emit_clusters`;
  - `knowledge_service.discovery_mode`;
  - `knowledge_service.strict_verification_required`.
- In `ResearchPipeline.answer_question`, call the Knowledge Service after query
  analysis and before ledger construction.
- Do not use evidence policy as a discovery-time hard filter. Partition and
  annotate by source role, binding level, document status, review status, and
  admissibility.
- Keep the current `ClaimTarget` path as the authoritative answer path until
  verification gates for dynamic claims pass.
- Add artifacts:
  - `evidence_clusters.json`;
  - `selected_evidence.json` if the current run selects cluster evidence;
  - `navigation_session_trace.json`;
  - `source_hierarchy_report.json` if not already represented well enough;
  - `claim_verification.json`;
  - `relation_graph_slice.json`;
  - `open_issues.json`.
- Preserve the current review surfaces, including `final_answer.txt`,
  `retrieval_plan.json`, `ingestion_report.json`, `ledger_entries.json`,
  `approved_ledger.json`, `gap_records.json`, `web_fetch_records.json`,
  `pinpoint_evidence.json`, `answer_alignment.json`,
  `blind_validation_report.json`, `manual_review.json`,
  `manual_review_report.md`, and `corpus_coverage_report.json` where
  applicable.

Acceptance gate:

- all existing eval and question-pack checks still pass;
- new artifacts are additive;
- Q6-Q8 surface the decisive legacy-style source families as clusters even if
  final answer behavior has not changed yet.

## 11. Phase 5: Verification And Ledger VNext

Goal:

- allow dynamic discovered claims to become answer-eligible through explicit
  verification, without weakening the ledger.

Implementation tasks:

- Implement `ClaimVerificationRecord` with:
  - `claim_id`;
  - `claim_type`;
  - verification result: `approved`, `interpretive`, `open`, `blocked`;
  - decision reason;
  - source IDs, chunk IDs, locators;
  - evidence tier, binding level, source role, document status, jurisdiction,
    publication date, version date, and effective date where known;
  - source digest / catalog version / corpus state ID;
  - support directness;
  - contradiction candidates;
  - higher-authority candidates considered;
  - attached open issues;
  - answer-use permission.
- Add per-check verification decisions. Each check emits
  `pass`, `fail`, or `qualified` plus a stored reason:
  - source exists in catalog;
  - source admission policy is recorded;
  - source hash / version matches the approved catalog entry;
  - locator is resolvable;
  - claim text is supported by the cited passage;
  - claim type is compatible with source tier and binding level;
  - jurisdiction, document status, publication / version / effective-date
    qualifiers are preserved;
  - higher-authority candidate sources were considered where required;
  - contradiction candidates were checked;
  - relevant open issues were attached;
  - answer use is allowed only for `approved` or explicitly qualified
    `interpretive` claims;
  - blocked claims remain in artifacts but cannot appear as final answer
    claims.
- Extend `build_ledger` or add a wrapper that can consume:
  - current `ClaimTarget` entries;
  - selected dynamic claims from evidence clusters.
- Apply the source-governance compatibility matrix before approval.
- Make open issues answer-governing: blocked issues prevent claim approval;
  qualifying issues force interpretive or caveated answer use.
- Store open issue links from affected claims and surface relevant issues in
  answer caveats.
- Preserve current `LedgerEntry` fields and artifact shape unless a versioned
  schema bump is explicitly chosen.

Acceptance gate:

- every final-answer claim can be traced through
  `answer_alignment.json`, `approved_ledger.json`, and
  `claim_verification.json`;
- blocked claims remain visible in artifacts but not as final answer claims;
- proposal-stage sources cannot support final-law wording;
- current-law claims preserve effective-date and document-status qualifiers;
- source-conflict questions expose higher-authority reasoning and gaps.

## 12. Phase 6: Answer Composer Integration

Goal:

- let answers benefit from evidence clusters while keeping the composer
  downstream of selected, verified evidence.

Implementation tasks:

- Add a composer input model for selected evidence clusters and verified
  dynamic claims.
- Keep specialized intents as layout and regression aids, not as the knowledge
  gateway.
- Add generic answer patterns for:
  - normative source hierarchy;
  - technical / operational architecture explanation;
  - conflict / precedence analysis;
  - lifecycle / process analysis;
  - open-issue heavy analysis.
- Render source-role and binding-level qualifiers in a stable way.
- Ensure broad fallback answers cannot be auto-accepted when relevant clusters
  or gaps exist.

Acceptance gate:

- Q1-Q8 answers contain substantive, source-backed claims rather than fallback
  meta-claims;
- Q6-Q8 improve without adding benchmark-specific intents, claim targets,
  facets, aliases, hard-coded source families, allowlist entries, or rendering
  special cases;
- Q5-style architecture-bucket answers remain possible;
- answer prose remains secondary to artifact traceability.

## 13. Phase 7: Evaluation, Parity, And Release Gates

Goal:

- prove that the new path is more flexible without losing review discipline.

Implementation tasks:

- Add a migration benchmark pack that includes:
  - Q1-Q5 parity questions;
  - Q6-Q8 generalization questions;
  - paraphrases in German, English, and mixed language;
  - false-friend questions;
  - source-conflict questions;
  - missing-source questions;
  - open-issue-heavy questions.
- Import useful legacy benchmark questions as reference cases, not as mandatory
  answer wording.
- Freeze the adjacent-unseen pack before Phase 4. The pack must cover at least
  these classes: paraphrase, mixed language, source conflict, architecture
  bucket, open issue, false friend, missing source, and adjacent unseen
  operational question.
- Add retrieval-usefulness checks for clusters, not only final sources.
- Add artifact-invariant tests:
  - every substantive final-answer claim has a stable `claim_id`;
  - every final-answer `claim_id` appears in `answer_alignment.json`;
  - every approved or interpretive `claim_id` appears in
    `approved_ledger.json`;
  - every ledger entry links to `source_id`, `chunk_id`, locator, source tier,
    binding level, document status, jurisdiction, effective-date qualifier when
    applicable, and verification result;
  - blocked claims do not render as accepted answer claims;
  - blocked, open, or insufficient claims appear in `claim_verification.json` or
    `gap_records.json`;
  - relevant open issues are linked from affected claims and surfaced in answer
    caveats;
  - cluster evidence can be opened as passages;
  - fetched or refreshed sources include digest, retrieval timestamp, admission
    policy, and provenance;
  - source-governance fields survive serialization.
- Keep the standard validation commands:
  - `python3 scripts/build_real_corpus_catalog.py`
  - `python3 scripts/run_unit_tests.py`
  - `python3 scripts/run_integration_tests.py`
  - `python3 scripts/run_real_question_pack.py --all`
  - `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`
- Add one migration-specific comparison command only if the existing harnesses
  cannot express the comparison cleanly.

Acceptance gate:

- no regression in existing fixture and real-corpus evals;
- Q1-Q8 pass migration acceptance criteria;
- at least eight frozen holdout questions, one per class listed above, retrieve
  and verify useful evidence without benchmark-specific code or config;
- reviewer can inspect the answer without broad raw-document hunting.

Frozen Q1-Q8 migration benchmark table:

| ID | Class | Required cluster / source checks | Prohibited fallback | Required artifacts |
| --- | --- | --- | --- | --- |
| Q1 role boundaries | role / responsibility analysis | clusters for wallet provider, issuer, verifier / relying party, register operator, QTSP; source role and binding level preserved | `broad_regulatory_answer` or generic wallet-only answer | clusters, verification, ledger, alignment, open issues |
| Q2 lifecycle | lifecycle / status-change analysis | clusters for register updates, suspension / deletion, retention, mandate and revocation controls | lifecycle answer without status / revocation evidence | clusters, verification, ledger, gaps, open issues |
| Q3 audit trails | audit / data minimization analysis | clusters for minimal transaction, counterparty, policy, status, revocation traces plus full-logging boundary | audit answer that implies full protocol logging | clusters, verification, pinpoint evidence, open issues |
| Q4 identity vs authority | natural/legal person separation | clusters separating natural-person identity, legal entity, mandate / representation, wallet-unit trust, relying-party checks | merged identity-authority answer | clusters, verification, alignment, source hierarchy |
| Q5 architecture buckets | architecture-source classification | three buckets: directly derivable, delegated, plausible assumption; each bucket source-qualified | unbucketed architecture answer | grouping/bucket artifact, ledger, open issues |
| Q6 provider change | portability / migration generalization | clusters for TS10 migration object / transaction log, device-bound reissuance or rebinding, non-device-bound copying, mandate continuity, trust re-anchoring, audit continuity | answer requiring a Q6-specific intent or target | clusters, passage navigation, verification, alignment |
| Q7 delegation chain | delegation modeling generalization | clusters for EBW mandate / access control, subject attestations, scope / validity / constraints, revocation, auditability, RP scope checks; open issues for legal subdelegation and schema gaps | flat-role answer without chain verification | clusters, relation slice, open issues, verification |
| Q8 source conflict | source-precedence conflict | clusters for authentic source / official register, registrar validation, EAA / status / revocation, wallet-held derivative evidence, conflict escalation gap | "wallet beats register" or "reality beats source" without authority caveat | clusters, higher-authority check, gaps, alignment |

Machine-checkable cluster pass conditions:

- decisive source or source family surfaced in top cluster set;
- exact passage openable by `source_id` and locator;
- adjacent passage openable for context;
- source role, binding level, document status, jurisdiction, and effective-date
  qualifier preserved;
- relevant open issue or missing facet surfaced when evidence is incomplete;
- final answer claim IDs align with selected verified evidence;
- broad fallback rejected.

## 14. Phase 8: Rollout And Decommissioning

Goal:

- make the agentic path the default only after it earns that role.

Rollout sequence:

1. `knowledge_service.enabled=false`, import and schema tests only.
2. `knowledge_service.enabled=true`, cluster artifacts emitted, current answer
   path unchanged.
3. Shadow / dual-run mode compares current path and agentic path on Q1-Q8,
   frozen holdouts, and real-corpus eval samples.
4. Dynamic verification enabled for selected clusters, still behind runtime
   config.
5. Composer consumes verified dynamic claims for migration benchmark questions.
6. Rollback drill proves that the previous runtime config can restore the
   current answer path and artifact bundle.
7. Agentic path becomes default for real-corpus runs after parity,
   generalization, artifact-compatibility, manual high-risk review, and rollback
   gates pass.

Decommissioning rules:

- Do not delete specialized intents immediately. Reclassify them as regression
  and presentation overlays.
- Remove an intent-specific target only after an equivalent generic cluster /
  verification path passes the same frozen benchmarks and holdouts in dual-run
  mode without benchmark-specific code or config.
- Keep a rollback runtime config for at least one release cycle.

## 15. Workstream Ownership

Suggested implementation slices:

- Contracts and schema:
  - `src/eubw_researcher/models/types.py`;
  - `src/eubw_researcher/config/loader.py`;
  - new `src/eubw_researcher/knowledge/models.py`;
  - unit tests under `tests/unit/`.
- Legacy import:
  - new `src/eubw_researcher/knowledge/legacy_import.py`;
  - new `src/eubw_researcher/knowledge/source_crosswalk.py`;
  - new `scripts/import_legacy_knowledge.py`;
  - import fixtures under `tests/fixtures/`.
- Knowledge Service:
  - new `src/eubw_researcher/knowledge/service.py`;
  - new `indexes.py`, `concepts.py`, `source_reader.py`, `clusterer.py`;
  - retrieval tests under `tests/unit/` and `tests/integration/`.
- Pipeline and artifacts:
  - `src/eubw_researcher/pipeline.py`;
  - `src/eubw_researcher/runtime_facade.py` only for additive result fields or
    versioned contract changes;
  - `src/eubw_researcher/evaluation/runner.py`;
  - `tests/unit/test_runtime_facade.py`;
  - artifact invariant tests.
- Verification and composer:
  - `src/eubw_researcher/evidence/ledger.py`;
  - new `src/eubw_researcher/knowledge/verifier.py`;
  - `src/eubw_researcher/answering/composer.py`;
  - review/eval tests.
- Evaluation:
  - `configs/real_question_pack.yaml`;
  - `configs/retrieval_usefulness_cases.yaml`;
  - new migration benchmark config if needed;
  - `src/eubw_researcher/evaluation/`.

## 16. Review And Quality Gates By Phase

Every phase must keep these checks green unless the phase explicitly updates
the expected artifact contract:

- unit tests;
- runtime facade tests;
- artifact serialization tests;
- existing real-corpus eval smoke path;
- source-governance / document-status tests;
- no destructive source-ID renames.

Reviewers should reject a phase if:

- a lower-tier source can silently become governing support;
- imported legacy claims appear as approved without verification;
- an artifact is removed or renamed without contract migration;
- the Knowledge Service returns final answer prose;
- Q6-Q8 improve only because new specialized intents, claim targets, facets,
  aliases, hard-coded source families, allowlist entries, or rendering special
  cases were added;
- answer text improves while artifact traceability worsens.

## 17. Risks And Controls

### Risk: scope balloon from importing the full legacy KB

Control:

- import representative slices first;
- keep rejected and unresolved records visible;
- do not require copying the full legacy persistent store.

### Risk: facade contract churn

Control:

- keep new operations internal until stable;
- add optional result fields before considering a version bump;
- document every public schema change.

### Risk: high recall creates noisy answers

Control:

- discover broadly, verify strictly;
- partition discovery results by authority and status;
- let the agent read sources before answer synthesis.

### Risk: overfitting continues under a new name

Control:

- treat Q6-Q8 as generalization cases;
- require eight frozen holdout questions across the migration benchmark classes;
- require cluster retrieval without benchmark-specific intents, claim targets,
  facets, aliases, source-family rules, allowlist entries, or rendering special
  cases.

### Risk: source-role mixing

Control:

- implement the compatibility matrix before dynamic claim approval;
- make binding level and document status mandatory in verification records.

## 18. Final Migration Definition Of Done

The migration is complete when:

- EUBW-Researcher can answer Q1-Q8 with source-backed substantive claims and
  reviewer-useful artifacts;
- at least eight frozen holdout questions across the migration benchmark
  classes work without benchmark-specific code or config;
- agents can navigate from question to evidence cluster to exact passage and
  adjacent passage;
- dynamic claims can become answer-eligible only through verification records;
- legacy knowledge assets are reused through validated import/crosswalks, not
  blind trust;
- existing facade and artifact compatibility are preserved or explicitly
  versioned;
- the default real-corpus eval and migration benchmarks pass;
- reviewer inspection no longer requires reconstructing the answer from raw
  documents.
