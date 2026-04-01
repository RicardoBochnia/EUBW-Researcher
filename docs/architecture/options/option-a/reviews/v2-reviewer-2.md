# Option A V2 Plan Review

Status: completed
Reviewer: v2-reviewer-2
Date: 2026-04-01
Review target: [V2_PLAN.md](../V2_PLAN.md)
Review focus: implementation realism from the current V1 code baseline

## 1. Findings

### blocker

- **The work order does not front-load the real migration point: replacing the current scenario-bound query-to-claim-target contract.** `V2_PLAN.md:65-80` says the analyzer must stop relying on narrow scenario-like patterning, but the current pipeline is built around hand-authored `ClaimTarget` sets and string-pattern routing in [`src/eubw_researcher/retrieval/planner.py:22-533`](../../../../../src/eubw_researcher/retrieval/planner.py), static grouping labels in [`src/eubw_researcher/answering/grouping.py:19-47`](../../../../../src/eubw_researcher/answering/grouping.py), and tests that lock specific intent classes into place in [`tests/unit/test_retrieval.py:24-97`](../../../../../tests/unit/test_retrieval.py) and [`tests/integration/test_pipeline_and_eval.py:768-809`](../../../../../tests/integration/test_pipeline_and_eval.py). As written, the V2 plan treats analyzer generalization as one workstream among several, but from the current baseline it is the prerequisite refactor for the primary Business Wallet path, corpus broadening, and grouping realism. Without making that migration explicit and early, the plan understates the largest code change in the whole V2 step.

### important

- **The plan blurs already-landed baseline behavior with real V2 delta, which will create rework and sequencing noise.** `V2_PLAN.md` presents real-corpus-default operation (`:16-20`), allowlist-governed official discovery (`:76-80`), `provisional_grouping.json` (`:105-117`), and the unified fixture/real-corpus artifact bundle (`:123-160`) as V2 work. But those behaviors are already described as implemented in [`docs/architecture/options/option-a/HARDENING_NOTES.md:7-10`](../HARDENING_NOTES.md), [`docs/architecture/options/option-a/HARDENING_NOTES.md:28-30`](../HARDENING_NOTES.md), [`README.md:22-30`](../../../../../README.md), [`src/eubw_researcher/pipeline.py:361-377`](../../../../../src/eubw_researcher/pipeline.py), and [`src/eubw_researcher/evaluation/runner.py:270-320`](../../../../../src/eubw_researcher/evaluation/runner.py). A reviewer can still infer the intended direction, but an implementer now has to guess which parts are already accepted baseline and which parts are the actual next-version delta.

- **No corpus-cache or shared-ingestion groundwork is planned, even though the current real-corpus gate is already expensive at today’s tiny curated slice.** The current scripts ingest the full catalog on every direct run in [`scripts/answer_question.py:37-45`](../../../../../scripts/answer_question.py), the eval runner ingests it again in [`src/eubw_researcher/evaluation/runner.py:254-267`](../../../../../src/eubw_researcher/evaluation/runner.py), and `run_all_scenarios` rebuilds that pipeline once per scenario in [`src/eubw_researcher/evaluation/runner.py:343-360`](../../../../../src/eubw_researcher/evaluation/runner.py). Observed locally on the current repository: `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json` took `81.13s` while operating on only 13 selected real-corpus sources. V2 wants broader real-corpus use, so a prebuilt normalized/chunked corpus bundle or at least one-ingestion-per-eval reuse is missing groundwork, not a later optimization.

- **The current retrieval loop short-circuits too early for the cross-layer research behavior V2 claims.** In [`src/eubw_researcher/pipeline.py:141-166`](../../../../../src/eubw_researcher/pipeline.py), each target is marked `resolved` as soon as one direct admissible support path is found, and later source layers are skipped for that target. That works for thin-slice confirmation, but it conflicts with `V2_PLAN.md:88-100`, which says the ledger must preserve multiple supporting citations, governing evidence, contradictory evidence, and layered context rather than collapsing to one winning citation. From the current baseline, that means V2 needs an explicit second-pass or "keep gathering corroborating/lower-layer evidence" rule; otherwise the main cross-layer promise stays weaker than the work order suggests.

- **The real-corpus scope assumption is still a hand-curated slice, not a broad default base, and the work order does not say how that expands.** The local archive is large enough to matter: [`artifacts/real_corpus/archive/README.md:13-23`](../../../../../artifacts/real_corpus/archive/README.md) describes a 104-file CELEX full-text mirror plus wider reference material, and the current archive catalog has 271 rows. The active V1/V2 runtime, however, is driven by the manually enumerated selection in [`configs/real_corpus_selection.yaml:1-149`](../../../../../configs/real_corpus_selection.yaml), which currently resolves to 13 sources in `artifacts/real_corpus/curated_catalog.json`. That is a sensible V1 baseline, but V2's "real research breadth" will mostly be a corpus-curation and gate-maintenance problem unless the plan names the next expansion batch, the admission rules, and how scenario expectations change when the selected source set changes.

### minor

- **The retrieval threshold is observability-only today, which becomes a larger trap as the corpus widens.** [`src/eubw_researcher/retrieval/local.py:81-98`](../../../../../src/eubw_researcher/retrieval/local.py) records `meets_threshold`, but candidates are still returned and consumed regardless of that flag, and the only direct assertion on the field is in [`tests/unit/test_retrieval.py:67-81`](../../../../../tests/unit/test_retrieval.py). On the current 13-source slice this is manageable; on a broader real corpus it increases the risk that wider retrieval simply feeds more weak candidates into claim classification without any actual admission gate.

## 2. Summary verdict

- Verdict: `not ready as a work order without revisions`
- Short rationale: V2 is still implementable from the current Option A baseline and does not require reopening the architecture, but the plan is not yet written as a realistic migration order. It mixes already-delivered capabilities with future delta, leaves the main query/claim-target refactor implicit, and omits the runtime/corpus groundwork needed before a broader real-corpus gate is practical.

## 3. What is realistically buildable from the current baseline

- The existing Option A backend is a usable starting point: format normalization, source hierarchy config, allowlisted official discovery, ledger construction, answer composition, grouping artifacts, and the fixture/real-corpus eval surfaces all already exist.
- It is realistic to evolve, not replace, the current repository shape. The current `QueryIntent -> retrieval plan -> ledger -> answer/artifact bundle` flow in [`src/eubw_researcher/pipeline.py:299-377`](../../../../../src/eubw_researcher/pipeline.py) can survive V2 if the query-analysis contract is generalized carefully rather than bypassed.
- It is realistic to expand the real corpus through the current selection/build path in [`scripts/build_real_corpus_catalog.py:29-55`](../../../../../scripts/build_real_corpus_catalog.py) and [`src/eubw_researcher/corpus/archive.py:24-58`](../../../../../src/eubw_researcher/corpus/archive.py), provided the next source batch is bounded and the gate is updated deliberately.
- It is realistic to strengthen review and evaluation on top of the existing artifact bundle rather than invent a new one. The current output shape in [`src/eubw_researcher/evaluation/runner.py:270-320`](../../../../../src/eubw_researcher/evaluation/runner.py) is already close to what V2 needs.

## 4. Hidden prerequisites or missing groundwork

- A dedicated migration phase for generalized query analysis and dynamic claim-target construction.
- A matching test-plan refactor, because the current suite encodes scenario-specific intents and target counts.
- A shared-ingestion or cached normalized-corpus path before the real-corpus gate broadens beyond the current 13-source curated slice.
- A bounded corpus-expansion plan: which additional source families move into the selected set first, and what the acceptance gate should expect after each increment.
- A real candidate-admission policy for retrieval, not just a recorded score flag.

## 5. Risks in sequencing or execution

- If the team expands the corpus before changing the query/claim-target contract, V2 will mostly become "more documents behind the same hand-written scenario router."
- If the team rewrites the analyzer before adjusting the tests and acceptance vocabulary, the current suite will push implementation back toward brittle pattern matching.
- If the team keeps rebuilding the corpus once per scenario, the V2 gate will become slow enough that people stop running it regularly.
- If the retrieval loop still stops after the first admissible support, cross-layer answers and grouping will look artificially shallow even when better supporting material exists in the selected corpus.
- If scenario configs keep pinning exact source ids while the selected real corpus evolves, normal corpus-maintenance work will read as regressions.

## 6. Recommended changes before approval

1. Rewrite `V2_PLAN.md` as a delta-from-current-baseline work order. Mark what is already delivered and isolate the actual next-step work.
2. Add an explicit first implementation phase for replacing the current scenario-pattern router with a generalized query-to-claim-target contract, including the required test migration.
3. Add corpus-runtime groundwork before any breadth push: either a prebuilt normalized/chunked bundle or one-ingestion-per-eval reuse, and make that part of the V2 execution plan rather than a later optimization.
4. Add a bounded corpus-expansion phase that names the first source-family increments beyond the current selected slice and updates the real-corpus gate accordingly.
5. Add an explicit retrieval-policy change for layered questions: keep gathering governing, corroborating, and contradicting evidence after the first direct support instead of treating the target as fully resolved.
6. Turn retrieval thresholds into a real admission rule or replace them with a different explicit candidate-selection contract before broader-corpus tuning starts.
