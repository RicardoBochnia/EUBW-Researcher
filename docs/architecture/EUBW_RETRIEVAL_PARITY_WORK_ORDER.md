# EUBW-Researcher Retrieval-Parity Work Order

Date: 2026-05-20

## Purpose

This document is a handover brief for a fresh Codex instance. Its task is to improve EUBW-Researcher retrieval so the new Agentic-RAG path can reliably surface the right source and passage for unfamiliar eIDAS/EUBW questions without adding one-off intents for each benchmark question.

The immediate trigger was Blind Source Holdout Round 2:

> Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?

The correct core source was present in both repos:

- EUBW-Researcher: `ec_ts01_wallet_trust_mark`, archive id `SRC-W-TEC-26`
- Legacy EUBW: `sources/reference_web/technical_and_standards/SRC-W-TEC-26_ec_ts01_wallet_trust_mark.md`

EUBW-Researcher did not surface it in `reading_plan.json`; Legacy produced the stronger reviewed answer because the answer agent could recover the source through direct repo reading and then cite it explicitly. This should be treated as a general retrieval and evidence-navigation problem, not as a `wallet_trust_mark` special case.

## Current Failure Pattern

In Round 2, the vNext run wrote artifacts under:

`artifacts/tmp/blind_source_holdout_2026-05-20/round-2-trust-mark-boundary/researcher`

Observed behavior:

- `curated_catalog.json` contained `ec_ts01_wallet_trust_mark`.
- `KnowledgeService._terms(question)` produced mostly surface tokens:
  `wallet-provider`, `wallet`, `provider`, `sichtbares`, `wallet-vertrauenszeichen`, `vertrauenszeichen`, `entfernen`, `relying`, `parties`, `attestation`, etc.
- There was no expansion from `vertrauenszeichen` to `trust mark`, from `entfernen` to `remove/cancellation/revoke`, or from `sichtbares` to `visible`.
- The specific Trust-Mark source did match weakly, but its best chunk ranked only around `#121` before the current `top100` cutoff:
  `ec_ts01_wallet_trust_mark::...1-2-scope-for-the-trust-mark-requirements-and-design`
- The top 100 were dominated by high-rank generic eIDAS/implementing-act chunks matching broad terms like `wallet`, `provider`, `relying`, `parties`, `attestation`.
- `reading_plan.json` opened eIDAS 2024/1183, eIDAS 2014/910, WRP registration, wallet-breach rules, ARF, RP-registration discussion, and OpenID4VCI, but not `ec_ts01_wallet_trust_mark`.
- `final_answer.txt` drifted toward Wallet-Relying-Party Access Certificates and was still accepted by `manual_review_report.md`.

Important nuance:

- The Legacy command also did not directly retrieve the Trust-Mark core source in its primary output for this question. Its output centered on WRP access certificates and generic wallet/relying-party claims.
- Legacy still outperformed in the blind answer because the answer agent used direct local source discovery and produced concrete `SRC-W-TEC-26, Sections 1.1/1.2` citations.
- Therefore the goal is not "copy Legacy exactly"; it is to combine Legacy's robust traceability/source ergonomics with EUBW-Researcher's stricter artifact and verification model.

## Legacy Comparison

Legacy retrieval is stronger in several ways that matter for agent use:

1. Multi-channel retrieval:
   - lexical claim scoring over draft claims
   - SQLite FTS over claims
   - SQLite FTS chunk bridge from chunks back to claims
   - optional semantic claim index
   - optional dense/cross-encoder paths in some profiles
   - relation expansion

2. Profile-driven broad recall:
   - `analysis_hybrid_semantic_global_tuned` uses global search with topic hints rather than hard topic filters.
   - It has high candidate budgets: `top_k=32`, `fts_top_n=220`, `fts_chunk_top_n=260`, `semantic_top_n=180`.
   - It keeps `semantic_include_semantic_only=true` and `fts_include_fts_only=true`.

3. Source and citation ergonomics:
   - Query output always includes claim IDs, source IDs, locators, evidence tier, binding level, hit terms, relation context, and supplemental raw chunk evidence.
   - Even when retrieval is imperfect, the output is useful for an agent to continue searching and reading.

4. Tunable source priorities:
   - `knowledge/config/source_priorities.json` can boost/deprioritize source families for topic profiles.
   - This is not perfect, but it gives the system a controlled way to prefer known high-signal sources without hardcoding full answers.

EUBW-Researcher currently has better artifact discipline, verification, source-governance fields and reading-loop artifacts, but its Knowledge Service retrieval is too shallow:

- `_rank_chunks` is simple term-overlap with small role/citation bonuses.
- Query expansion is a small hardcoded alias table in `src/eubw_researcher/knowledge/service.py`.
- There is no source-catalog/title retrieval lane.
- There is no multi-channel fusion for Knowledge Service clusters.
- There is no recall rescue when a highly title-relevant source is outside the top 100.
- Reading artifacts open `clusters[:max_clusters]`, so an early ranking miss becomes an answer miss.

## Root Cause Hypothesis

The systemic problem is that EUBW-Researcher currently ranks passages as if every matched token were equally meaningful. In legal/technical corpora, broad role terms such as `wallet`, `provider`, `relying party`, and `attestation` appear everywhere. A question-specific source can lose if the distinctive concept is:

- German while the corpus is English,
- expressed in a document title rather than body text,
- present as a source-level concept rather than as repeated chunk terms,
- in a medium-rank project/spec source while broad high-rank legal sources match many generic terms,
- outside the first-pass cluster budget.

The fix should introduce source-discovery and retrieval-fusion capabilities, then make the reading loop verify topical coverage before composing.

## Implementation Objective

Build a general-purpose "agentic recall layer" for the Knowledge Service:

- It should discover likely sources before passage selection.
- It should fuse multiple evidence signals instead of relying on one term-overlap score.
- It should preserve source-governance and verification gates.
- It should improve unfamiliar-question retrieval without adding benchmark-specific intents.
- It should expose enough diagnostics for an agent to understand why a source was or was not opened.

## Required Work

### 1. Add source-catalog retrieval as a first-class lane

Implement a source-level retrieval stage over:

- `source_id`
- `archive_source_id`
- `legacy_source_ids`
- title
- publication status
- source kind
- source family
- local path basename
- canonical URL tokens
- optional governance metadata / aliases if present

Expected effect:

- A query containing a distinctive concept should find a source whose title/path contains that concept, even if individual chunks rank lower.
- The source lane must not directly decide the answer. It should nominate sources for passage opening.

Suggested files:

- `src/eubw_researcher/knowledge/service.py`
- possibly a new module: `src/eubw_researcher/knowledge/source_retrieval.py`
- tests in `tests/unit/test_agentic_knowledge_migration.py` or a new retrieval-focused test file

Acceptance example:

- For the Trust-Mark question, `ec_ts01_wallet_trust_mark` must appear in source candidates and at least one passage from Section 1.1 or 1.2 must be opened.

### 2. Replace ad-hoc aliases with reusable query expansion

The Knowledge Service should not maintain a tiny parallel alias table while Legacy has an ontology mechanism. Options:

- Import/adapt Legacy's ontology expansion concept into EUBW-Researcher.
- Or extend `configs/terminology.yaml` / `configs/research_profiles.yaml` into a real retrieval-expansion source.

The expansion should support:

- German-to-English domain aliases,
- phrase aliases,
- source-title phrase expansion,
- controlled anti-synonyms where needed,
- trace output showing which expansion fired.

Do not solve this by adding only:

- `vertrauenszeichen -> trust mark`

That exact alias can be a regression fixture, but the implementation must be general.

Acceptance examples:

- `Vertrauenszeichen` expands to `trust mark`.
- `entfernen` can match `remove`, `cancellation`, `withdrawal`, or equivalent lifecycle terms depending on context.
- `Richtige Immabescheinigung` expands toward `selection`, `scope`, `intended use`, `student/enrolment attestation`.

### 3. Add multi-channel fusion for Knowledge Service ranking

Knowledge Service cluster ranking should combine at least:

- exact title/source-id/path match,
- chunk lexical overlap,
- phrase match,
- source-kind/source-role signal,
- citation/anchor quality,
- imported legacy candidate claim signal where available,
- optional SQLite FTS or existing local retrieval backend results,
- optional semantic/hash or dense signal if already available and cheap.

Do not let a single channel dominate silently. Emit per-channel scores in trace artifacts.

Suggested artifact extension:

- Add a retrieval diagnosis JSON, e.g. `knowledge_retrieval_diagnostics.json`, or enrich `navigation_session_trace.json`.
- Include top source candidates, top chunk candidates, terms/expansions, dropped-but-close candidates, and final fusion reason.

Acceptance examples:

- For the Trust-Mark question, the specific Trust-Mark source must not be pushed below generic WRP/eIDAS chunks merely because `wallet/provider/relying/attestation` match more often.
- For existing legacy parity questions Q1-Q8, expected `required_cluster_source_ids` should continue to surface.

### 4. Add recall rescue before reading-plan truncation

Before `build_reading_artifacts` opens `clusters[:max_clusters]`, check whether high-confidence source candidates or required concept candidates are absent from the chosen clusters.

General rescue rules:

- If a source-title/source-id lane has a strong unique match, force one passage from that source into the reading plan.
- If a source appears in imported candidate claims or relation/open-issue material for the question but not in clusters, keep one passage candidate unless clearly off-topic.
- If all top clusters come from generic high-rank legal sources and a medium-rank source has a much stronger title/concept match, preserve the medium-rank source as interpretive/spec context.

This is source discovery, not answer generation; final answer use remains gated by verification.

### 5. Improve topical drift checks

`manual_review_report.md` accepted a final answer that did not answer the Trust-Mark question. Add a check that compares:

- normalized question terms and expansions,
- source candidates,
- opened passages,
- final answer surface,
- evidence synthesis records.

A run should be `needs_follow_up` or `reject` when:

- a high-confidence source candidate was discovered but not opened,
- the final answer lacks the distinctive question concept,
- the answer is dominated by adjacent but wrong topic families,
- the evidence synthesis matrix does not contain the key source or key concept.

Acceptance example:

- Round-2-style output centered on WRP access certificates must not receive final `accept`.

### 6. Improve `evidence_synthesis_matrix`

Current rows often contain truncated raw snippets. Convert them into compact, citable synthesis statements:

- `statement`: concise proposition derived from the passage, not arbitrary snippet text.
- `source_ids`, `chunk_ids`, `locators`: keep exact traceability.
- `answer_role`: distinguish `core_answer_support`, `scope_boundary`, `source_role_context`, `open_issue`, `background`.
- `caveats`: include source-role and binding limitations.

This can start deterministic/simple; it does not need to be generative.

### 7. Keep the agentic model

Do not reintroduce one intent per question. The target behavior is:

1. classify enough to know source-role expectations,
2. discover candidate sources,
3. open likely passages,
4. expose relationships and gaps,
5. compose only from verified, opened evidence.

Specialized profiles are allowed only as broad research profiles, not benchmark-answer templates.

## Regression Tests To Add

Add tests that fail on the current behavior:

1. `trust_mark_boundary_retrieval`
   - Question: `Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?`
   - Expected: source candidate and reading plan include `ec_ts01_wallet_trust_mark`.
   - Expected locators include Section 1.1 or 1.2 if available.

2. `source_title_beats_generic_role_terms`
   - Synthetic fixture with a medium-rank source whose title exactly matches the distinctive question phrase and high-rank generic sources matching many broad role terms.
   - Expected: the title-matching source survives into clusters/reading plan.

3. `german_english_domain_expansion`
   - Synthetic or real fixture proving German domain terms expand into English source-title terms.

4. `manual_review_rejects_topic_drift`
   - Fixture answer about WRP access certificates for a Trust-Mark question.
   - Expected: review is not `accept`.

5. Legacy parity guard:
   - Run `python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml`.
   - Existing Q1-Q8 gates must not regress.

## Suggested Validation Commands

Run after implementation:

```bash
python3 scripts/build_real_corpus_catalog.py
python3 scripts/run_tests.py
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_gold_holdout_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json
```

Then rerun at least Blind Holdout Round 2 manually:

```bash
python3 scripts/answer_question.py "Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/retrieval_parity_trust_mark_smoke
```

Expected smoke outcome:

- `reading_plan.json` includes `ec_ts01_wallet_trust_mark`.
- `opened_passages.json` includes Section 1.1 or 1.2.
- `evidence_synthesis_matrix.json` contains a source-backed statement about when the visible trust mark must be removed.
- `final_answer.txt` answers the Trust-Mark question and names the scope boundary for Relying Parties / Attestation Providers.
- `manual_review_report.md` does not accept off-topic WRP-access-certificate-only answers.

## Non-Goals

- Do not hardcode the Trust-Mark answer.
- Do not add a narrow `trust_mark_boundary` intent as the main fix.
- Do not weaken verification gates to improve answer fluency.
- Do not copy Legacy's free-form answer style at the expense of EUBW-Researcher's artifact traceability.
- Do not make all medium-rank project artifacts outrank governing law globally; use source/title/concept signal and source-role caveats.

## Definition Of Done

The task is done when:

- the Trust-Mark source is found by the general retrieval machinery, not by a bespoke intent;
- diagnostics explain why it was selected;
- the answer path opens the relevant passage before composition;
- topic-drift review catches the previous failure mode;
- legacy parity and gold holdout packs do not regress;
- the implementation keeps source governance and verification as first-class review surfaces.
