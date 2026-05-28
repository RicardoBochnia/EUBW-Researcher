# EUBW Agentic RAG Navigation Migration

Status: architecture migration decision draft
Date: 2026-05-26
Scope: migration from answer-first RAG behavior to agent-navigation-first RAG
within EUBW-Researcher

This is a delta document. It does not replace:

- `docs/architecture/EUBW_AGENTIC_RAG_TARGET_ARCHITECTURE.md`;
- `docs/architecture/EUBW_AGENTIC_RAG_MIGRATION_PLAN.md`;
- `docs/architecture/EUBW_RAG_LEGACY_PARITY_AND_PHASE8_PLAN.md`;
- `docs/architecture/EUBW_RETRIEVAL_PARITY_WORK_ORDER.md`.

Where this document repeats a principle from those documents, it does so only to
make the navigation-first migration decision operational.

## 1. Decision

EUBW-Researcher should migrate from an answer-first RAG shape to an
agent-navigation-first RAG shape.

The RAG layer should not be optimized primarily to pre-compose the best possible
answer text. It should instead become the agent-facing evidence navigation
substrate:

- where sources live;
- which claims, chunks, relations and open issues are relevant;
- which source roles, binding levels and document statuses apply;
- which passages should be opened next;
- which claims can be verified, rejected, or only treated as contextual;
- where the corpus is incomplete or ambiguous.

The agent owns final synthesis. The RAG layer provides the map, trail markers,
source-governance checks and evidence handles. `final_answer.txt` remains a
useful product surface, but it is no longer the primary quality source. The
primary review surface becomes the Navigation Bundle.

This is not a greenfield rewrite. The migration happens inside the existing
EUBW-Researcher architecture and reuses:

- Researcher verification, ledger, artifact and review gates;
- Legacy EUBW claim-first retrieval, source ergonomics and research-profile
  lessons;
- existing runtime configs for shadow, assistive and vNext modes;
- existing legacy-parity and holdout evaluation packs.

## 2. Boundary Clarification

The existing target architecture already states the most important boundary:
Knowledge Service and Source Reader are upstream evidence tools, not final
answer writers.

This migration sharpens that boundary:

| Layer | Responsibility | Not responsible for |
| --- | --- | --- |
| Knowledge Service | discover sources, claims, chunks, concepts, relations, gaps and candidate evidence | final answer prose |
| Source Reader | open exact passages and adjacent passages with locators | deciding legal conclusions |
| Verification / Ledger gate | existing verifier and ledger logic applies source-role, binding-level, document-status and traceability gates | acting as a new agent-facing reasoning layer |
| Answer Composer | package selected verified evidence into a user-facing answer | discovering missing evidence or hiding gaps |
| Agent | decompose the question, choose reads, synthesize, qualify, decide what to cite | blindly trusting raw snippets |

The Composer may remain useful for CLI and batch runs. But in the target shape it
must consume explicit selected evidence and expose its evidence basis. It should
not compensate for weak navigation by inventing fluent prose.

## 3. Current Evidence

### Holdout Round 2: Trust Mark Boundary

The correct source existed in both repositories:

- Researcher: `ec_ts01_wallet_trust_mark`, archive id `SRC-W-TEC-26`;
- Legacy: `SRC-W-TEC-26_ec_ts01_wallet_trust_mark.md`.

Researcher did not surface the source strongly enough in the reading plan. The
answer drifted toward Wallet-Relying-Party Access Certificates. The Review Gate
still accepted a weak answer. This shows a generic navigation failure:

- source-title/source-id retrieval was too weak;
- distinctive concept rescue was missing;
- the final answer could pass despite topic drift;
- `final_answer.txt` was a poor proxy for whether the agent had the right map.

### Holdout Round 3: Relying Party Intermediary

Researcher opened several relevant source families, but the final answer surface
started with raw or adjacent registration material rather than the actual role
boundary: Wallet-Relying Party, Intermediary, Intended Use, requested data,
privacy/DPA information and user display.

Both anonymized review answers lost traceability because the protocol did not
force visible source locators. The underlying finding remains: answer quality
depends on whether the agent can navigate the right facets and retain source
handles through synthesis.

### Holdout Round 4: Pseudonym Account Binding

Researcher won the blind review under the agentic usage model. The answer agent
used Researcher artifacts and then read the bundled sources directly. The
automatic `final_answer.txt` remained weak and register-/notification-heavy.

Round 4 is the strongest evidence for this migration:

- the Navigation Bundle plus direct reading enabled a strong answer;
- the raw renderer did not;
- the agent needed source and passage navigation more than prewritten prose;
- the remaining gap is to make the navigation layer precise enough that the
  agent needs less manual rescue.

## 4. Target Runtime Shape

The target runtime exposes Knowledge Service operations as agent tools. These
can be CLI-internal first and do not require a public package API break.

Minimum tool-shaped operations:

| Operation | Purpose | Primary artifact |
| --- | --- | --- |
| `discover_sources(question)` | find likely source families by title, source id, archive id, path, metadata and distinctive terms | `source_candidates` / `knowledge_retrieval_diagnostics.json` |
| `search_claims(question, profiles)` | retrieve candidate claims with source-role and binding metadata | `selected_evidence.json` / `claim_verification.json` |
| `search_chunks(question, profiles)` | retrieve source chunks and adjacent candidates | `evidence_clusters.json` |
| `open_passage(source_id, locator_or_chunk_id)` | inspect exact source text with locator | `opened_passages.json` |
| `expand_neighbors(passage_id)` | open adjacent article, recital, section, table or annex context | `opened_passages.json` |
| `follow_relations(claim_or_source_id)` | inspect relation graph, conflicts, exceptions, definitions and delegation links | `relation_graph_slice.json` |
| `verify_claims(candidate_claim_ids)` | apply source-governance, directness and traceability gates | `claim_verification.json` / `approved_ledger.json` |
| `report_gaps(question, evidence)` | expose missing source families, unresolved issues and unsupported assertions | `gap_records.json` / `open_issues.json` |

The runtime can continue to write a bundled answer for batch usage, but the
Navigation Bundle is the authoritative review surface:

- `source_candidates`;
- `research_profile_trace.json`;
- `retrieval_plan.json`;
- `navigation_session_trace.json`;
- `evidence_clusters.json`;
- `reading_plan.json`;
- `opened_passages.json`;
- `evidence_synthesis_matrix.json`;
- `claim_verification.json`;
- `source_hierarchy_report.json`;
- `relation_graph_slice.json`;
- `open_issues.json`;
- `gap_records.json`;
- `answer_alignment.json`;
- `final_answer.txt`.

`final_answer.txt` is deliberately last in this list. It is the product surface,
not the evidence authority.

## 5. Existing Code Levers

The migration should be implemented by reshaping existing code paths rather than
introducing an unrelated runtime.

Primary orchestration levers:

- `src/eubw_researcher/runtime_facade.py`: stable facade and future agent-tool
  entrypoint surface;
- `src/eubw_researcher/pipeline.py`: orchestration of retrieval, knowledge
  service, verification, composer and artifacts.

Navigation levers:

- `src/eubw_researcher/knowledge/service.py`: evidence clusters, claim/chunk
  search and diagnostics;
- `src/eubw_researcher/knowledge/source_retrieval.py`: source-level retrieval
  and source rescue;
- `src/eubw_researcher/knowledge/query_expansion.py`: reusable expansion and
  traceable aliases;
- `src/eubw_researcher/knowledge/profiles.py`: research profile activation;
- `src/eubw_researcher/knowledge/reading.py`: reading plan, opened passages and
  synthesis matrix.

Presentation lever:

- `src/eubw_researcher/answering/composer.py`: downstream packaging of selected
  evidence into an answer.

Config levers:

- `configs/runtime.knowledge_shadow.yaml`: evidence-only shadow behavior;
- `configs/runtime.knowledge_assistive.yaml`: assistive dynamic evidence;
- `configs/runtime.knowledge_composer_vnext.yaml`: vNext composition and reading
  artifacts;
- `configs/research_profiles.yaml`: reusable broad research profiles.

## 6. Migration Workstreams

### 6.1 Source Discovery First

Add or harden source-level retrieval as a first-class lane before chunk ranking.
The source lane must consider:

- normalized `source_id`;
- archive and legacy source IDs;
- title and document heading;
- path basename and source family;
- canonical URL tokens;
- source kind, document status and governance metadata;
- corpus-derived aliases.

Acceptance examples:

- Trust-Mark questions surface `ec_ts01_wallet_trust_mark` before composition.
- Pseudonym questions surface ARF pseudonym sections, EUDI/eIDAS pseudonym
  articles and OpenID4VP linkability/selection material.
- Source-title matches can rescue medium-rank technical material from generic
  high-rank legal noise.

### 6.2 Query Expansion As Shared Knowledge, Not Patch Table

Move from ad hoc aliases toward reusable terminology and profile-driven
expansion.

Required behavior:

- German-to-English domain aliases;
- phrase-level aliases;
- lifecycle and status terms;
- source-title phrase expansion;
- trace output explaining which expansion fired;
- negative controls to avoid broad false friends.

Do not solve holdouts by adding only single-question aliases. A new expansion
must represent a reusable corpus concept and be tested against at least one
adjacent holdout.

### 6.3 Reading Loop As Agent Navigation

The reading loop must not only open the top `n` clusters. It should check
whether distinctive concepts and high-confidence source candidates are covered.

Required behavior:

- build a reading plan per facet or evidence need;
- force a passage from a strong source-level match if chunk ranking misses it;
- open adjacent passages when article/section/table context matters;
- mark why a passage was opened: source-title match, claim match, relation,
  profile, gap check, higher-authority check;
- expose budget exhaustion and skipped-but-close candidates.

### 6.4 Evidence Synthesis Matrix As Agent Input

`evidence_synthesis_matrix.json` should contain compact, citable propositions,
not truncated raw snippets.

Each row should include:

- concise statement;
- source IDs;
- chunk IDs;
- locators;
- source role / evidence tier;
- binding level and document status when available;
- answer role such as `core_answer_support`, `scope_boundary`,
  `technical_context`, `source_role_context`, `open_issue`, `background`;
- caveats;
- verification state.

The matrix is an agent planning surface. It should help an agent decide what to
cite, what to read further, and what to treat only as context.

### 6.5 Topic Drift And Distinctive Concept Gates

A run must not receive `accept` when the distinctive question concepts were
found but not opened, or opened but not reflected in the answer/evidence matrix.

Minimum reject / follow-up triggers:

- high-confidence source candidate not opened;
- final answer lacks the distinctive concept asked by the user;
- answer is dominated by adjacent source families;
- evidence matrix has no row for the central facet;
- answer cites a source family but misses the specific source-role boundary;
- normative wording is based only on proposal or technical context.

### 6.6 Agent-Facing Facade Without Breaking Existing Users

Keep `ResearchRuntimeFacade` stable, but add a navigation-oriented internal mode
behind the existing runtime configs.

Near-term shape:

- existing `answer_question` continues to work;
- `evidence_only` and artifact bundle modes become the preferred agent path;
- Navigation Bundle artifacts are always written when Knowledge Service is
  enabled;
- future tool wrappers can call internal operations without requiring a new
  public API on day one.

### 6.7 Composer Deprioritization

The Composer should be treated as downstream packaging.

Required behavior:

- consume explicit verified evidence and synthesis rows;
- preserve source locators in answer text or alignment artifacts;
- never hide gaps with fluent prose;
- never upgrade technical or proposal material into final legal authority;
- produce a useful `final_answer.txt`, but not be the main gate for whether the
  run is evidence-sound.

## 7. Legacy And Researcher Strengths To Preserve

Legacy strengths to reuse:

- claim-first discovery;
- visible `CLM-*`, `SRC-*`, `CH-*` handles;
- source priorities and research profiles;
- broad candidate budgets;
- relation expansion;
- supplemental raw chunk evidence;
- output that helps an agent continue reading.

Researcher strengths to preserve:

- strict source governance;
- ledger and verification gates;
- reviewable artifact bundles;
- corpus coverage reports;
- answer alignment and blind validation;
- rollbackable runtime configs;
- explicit handling of gaps and open issues.

Migration rule:

Legacy assets may improve recall and navigation, but they do not become
answer-governing until Researcher verification admits them.

## 8. Planned Codex Skills

Codex skills are planned as operational review aids, not as domain-truth
containers. They should standardize how an agent checks artifacts and runs
benchmarks. They should not encode EUBW legal conclusions.

### 8.1 `eubw-retrieval-smoke`

Purpose:

- check whether source discovery, reading plan and opened passages match the
  distinctive concepts of a question.

Typical inputs:

- question text;
- artifact directory;
- expected source family or concept when available from a benchmark.

Expected output:

- pass/fail summary;
- missing source candidates;
- opened passage coverage;
- close-but-dropped candidates;
- suggested next diagnostic command.

Contract:

- must inspect `knowledge_retrieval_diagnostics.json`, `reading_plan.json` and
  `opened_passages.json`;
- fails if a benchmark-required or high-confidence source candidate is absent
  from the reading plan without a recorded rejection reason.

### 8.2 `eubw-artifact-review`

Purpose:

- review traceability, topic drift, source-role separation and gap visibility.

Typical inputs:

- Navigation Bundle;
- `final_answer.txt`;
- optional benchmark review focus.

Expected output:

- hard-error list;
- traceability score;
- topic-drift finding;
- source-role violations;
- gap/open-issue preservation findings.

Contract:

- must inspect `final_answer.txt`, `evidence_synthesis_matrix.json`,
  `claim_verification.json`, `source_hierarchy_report.json`,
  `gap_records.json` and `answer_alignment.json`;
- fails if a substantive final-answer claim cannot be traced to an approved or
  explicitly contextual evidence record.

### 8.3 `eubw-corpus-governance`

Purpose:

- review catalog, crosswalk, legacy import and source metadata quality.

Typical inputs:

- curated catalog;
- source crosswalk;
- imported legacy asset report;
- changed source files or corpus selection configs.

Expected output:

- missing source governance fields;
- unresolved legacy IDs;
- digest or locator gaps;
- candidate-vs-approved status findings.

Contract:

- must inspect the curated catalog, source crosswalk and legacy import reports;
- fails if imported legacy material can become answer-governing without a
  candidate/reference status and Researcher verification path.

### 8.4 `eubw-parity-rollback`

Purpose:

- run or review Legacy-Parity, Gold-Holdout and rollback checks as a repeatable
  process.

Typical inputs:

- runtime config;
- catalog;
- question pack;
- previous parity report.

Expected output:

- regression summary;
- gate status;
- dirty-git / digest provenance;
- rollback readiness note.

Contract:

- must run or review Legacy-Parity, Gold-Holdout and rollback-smoke artifacts;
- fails if a default-switch proposal lacks a passing rollback path and
  provenance for catalog, runtime config and question pack.

Skill implementation is a later task. This migration document only reserves the
roles and acceptance expectations.

## 9. Acceptance Gates

### 9.0 Gate Vocabulary And Verdicts

Allowed verdicts:

- `accept`: navigation, verification, answer alignment and source-role checks
  are all sufficient for the asked question;
- `needs_follow_up`: relevant material was found but not opened, not aligned,
  not sufficiently located, or not synthesized into an answer-ready evidence
  row;
- `reject`: the answer is unsupported, source-role-incorrect, topic-drifted, or
  missing the central answer boundary.

Operational definitions:

- `central question concept`: a benchmark-defined expected concept when present;
  otherwise a distinctive phrase/facet from query expansion, source-title match,
  research-profile activation, or repeated high-scoring claim/source evidence.
- `high-confidence source candidate`: a source candidate marked high confidence
  by exact source-id/title/path match, strong phrase match, legacy candidate
  claim support, profile-required source family, or source-rescue rule.
- `stable locator`: article, recital, annex point, section, table, page, or
  chunk id with source id. Document-level-only locators are insufficient for
  narrow core claims unless no finer locator exists and the limitation is
  recorded.
- `adjacent source family`: a source family sharing broad terms such as
  `wallet`, `provider`, `relying party` or `attestation` while missing the
  distinctive concept that drove the question.
- `substantive final-answer claim`: any sentence that states a legal,
  technical, architectural, lifecycle or responsibility conclusion rather than
  pure framing or transition text.

Hard answer/bundle consistency rule:

- every substantive final-answer claim must trace to `approved_ledger.json`,
  `claim_verification.json`, or `evidence_synthesis_matrix.json` with a source
  and locator;
- if a final-answer claim contradicts or outruns the Navigation Bundle, the run
  cannot be `accept`;
- if the unsupported claim is central to the question, the run is `reject`;
- if the unsupported claim is peripheral but material, the run is
  `needs_follow_up`.

### 9.1 Navigation Bundle Gate

A Knowledge-Service run passes only if:

- high-confidence source candidates are visible;
- central source candidates are either opened or explicitly rejected with a
  reason;
- opened passages have stable locators;
- evidence synthesis rows are proposition-like and cite source/chunk/locator;
- claim verification explains admitted, rejected and contextual evidence.

Minimum artifact contract:

- `knowledge_retrieval_diagnostics.json` lists source candidates with confidence
  and channel reason;
- `reading_plan.json` records why each selected passage was opened;
- `opened_passages.json` records source, chunk/passage id and locator;
- `evidence_synthesis_matrix.json` has at least one row for each central facet;
- `claim_verification.json` separates approved, rejected and contextual claims.

### 9.2 Distinctive Concept Gate

A run cannot be `accept` if:

- the central question concept is absent from source candidates;
- it is present in candidates but absent from the reading plan;
- it is present in opened passages but absent from final answer and alignment;
- the final answer answers an adjacent question instead.

### 9.3 Source-Governance Gate

A run cannot be `accept` if:

- proposal material is rendered as final law;
- technical specifications are rendered as binding legal authority;
- source role or binding level is missing for a core normative claim;
- legacy candidate claims become answer-governing without Researcher
  verification.

### 9.4 Legacy-Parity And Holdout Gate

The migration is successful only when:

- Legacy-Parity Pack does not regress;
- Gold Holdouts do not regress;
- blind-source holdouts show Researcher is at least not worse under the
  agentic usage model;
- failures produce actionable categories: source discovery, reading plan,
  synthesis matrix, composer, source governance, gap handling.

### 9.5 Rollback Gate

Default changes require:

- a documented rollback runtime config;
- a successful rollback smoke run;
- preserved compatibility for existing artifact consumers;
- no removal of specialized intents until generic profile/navigation behavior
  covers their regression cases.

## 10. Required Acceptance Scenarios

### Round-2 Trust-Mark Scenario

Question:

> Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?

Required behavior:

- `ec_ts01_wallet_trust_mark` appears as source candidate;
- `reading_plan.json` opens Section 1.1 or 1.2, or a clearly equivalent
  Trust-Mark scope/removal passage;
- `evidence_synthesis_matrix.json` contains a Trust-Mark removal/scope
  statement;
- topic drift toward WRP access certificates is rejected or marked
  `needs_follow_up`.

### Round-3 Intermediary Scenario

Question:

> Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck und Datenschutzinformationen auseinanderhalten?

Required behavior:

- facets include end relying party, intermediary, intended use, requested
  attributes, privacy/DPA and user display;
- reading plan opens RP registration / intermediary material and user display
  material;
- evidence matrix contains separate rows for actor boundary, purpose, data
  scope and privacy information;
- final answer or alignment keeps locators.

### Round-4 Pseudonym Scenario

Question:

> Wann kann ein Wallet-Use-Case pseudonyme Authentifizierung statt Offenlegung der Identitaet nutzen, und welche Grenzen entstehen bei Account-Bindung, Attributpraesentation und linkbaren Pseudonymen?

Required behavior:

- reading plan surfaces ARF pseudonym sections, eIDAS/EUDI pseudonym provisions
  and OpenID4VP selective-disclosure/linkability material;
- evidence matrix separates legal permission, account-binding limit, attribute
  presentation limit and linkability risk;
- answer alignment preserves source roles and locators;
- raw renderer is not accepted if it drifts toward registration or notification
  material.

### Failure Scenario: No Viable Source Candidate

Trigger:

- the question contains a distinctive concept, but retrieval finds only broad
  generic sources.

Required behavior:

- verdict is `needs_follow_up`, not `accept`;
- `gap_records.json` or `open_issues.json` records missing source coverage;
- final answer, if produced, says the local corpus did not surface sufficient
  evidence for the central concept.

### Failure Scenario: Source-Role Conflict

Trigger:

- binding law, proposal-stage material and technical specifications all mention
  the topic but support different strengths of conclusion.

Required behavior:

- source hierarchy is visible in `source_hierarchy_report.json`;
- evidence matrix separates legal basis, proposal context, technical context
  and interpretation;
- final answer does not flatten proposal/spec material into final law;
- source-role violation is `reject`.

### Failure Scenario: Locator Gap

Trigger:

- the right source is found, but only document-level or title-only evidence is
  available for a narrow claim.

Required behavior:

- verdict is `needs_follow_up` unless the answer explicitly marks the limitation;
- `evidence_synthesis_matrix.json` row carries a locator caveat;
- review does not treat the claim as fully verified.

### Failure Scenario: False-Friend Expansion

Trigger:

- a German/English alias or broad profile term pulls in a lexically similar but
  semantically wrong source family.

Required behavior:

- negative-control trace shows why the source was rejected or deprioritized;
- answer does not cite the false-friend source for the central claim;
- if false-friend material dominates the final answer, verdict is `reject`.

## 11. Standard Validation

Run before rollout gates:

```bash
python3 scripts/build_real_corpus_catalog.py
python3 scripts/build_source_crosswalk.py
python3 scripts/run_tests.py
python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_legacy_parity.py
```

Focused navigation smoke before rollout gates:

- run the Round-2, Round-3 and Round-4 required scenarios with
  `configs/runtime.knowledge_composer_vnext.yaml`;
- inspect Navigation Bundle completeness before judging `final_answer.txt`;
- run at least one negative-control / false-friend case;
- run at least one source-role conflict case;
- run at least one locator-gap case;
- compare behavior across shadow, assistive and vNext configs when changing
  default behavior;
- record whether failures are categorized as source discovery, query expansion,
  reading plan, synthesis matrix, composer, source governance or gap handling.

For focused debugging:

```bash
python3 scripts/answer_question.py "$QUESTION" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/navigation_migration_probe/<case-id>
```

Review the Navigation Bundle before judging the answer text.

## 12. Non-Goals

- No greenfield rewrite.
- No return to a pure Legacy runtime.
- No benchmark-specific intent or target for every failing holdout.
- No unverified Legacy claim admission.
- No default switch before parity, holdout and rollback gates.
- No Codex skill that embeds domain truth or hidden expected answers.
- Missing Codex skills do not block the architecture decision itself; they block
  only a later claim that artifact review has been fully operationalized.

## 13. Implementation Order

1. Harden source discovery and diagnostics.
2. Promote query expansion into shared corpus/profile knowledge.
3. Add reading-plan rescue for distinctive concepts and source-title matches.
4. Convert synthesis matrix rows into answer-ready evidence propositions.
5. Add topic-drift and distinctive-concept gates.
6. Expose Navigation Bundle as the preferred agent-facing review surface.
7. Keep Composer VNext as downstream packaging and improve it only after
   navigation gates are reliable.
8. Design and then implement Codex skills for repeatable artifact review.
9. Run parity, holdout and rollback gates before any default switch.

## 14. Definition Of Done

This migration is done when:

- an agent can answer unfamiliar eIDAS/EUBW questions primarily from Navigation
  Bundle artifacts plus direct source reading;
- `final_answer.txt` quality improves without becoming the sole quality gate;
- distinctive source/concept misses are caught before `accept`;
- each substantive answer claim has a Source/Locator/Verification path;
- Legacy-Parity and Gold-Holdout reports are stable;
- rollback remains documented and tested;
- planned Codex skills are either implemented as follow-up review aids or
  explicitly tracked outside the runtime core.
