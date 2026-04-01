# Option A V2 Plan Review

Status: completed
Reviewer: v2-reviewer-4
Date: 2026-04-01
Focus: corpus and discovery, source-governance, inspectability
Review target: [V2_PLAN.md](../V2_PLAN.md)

## 1. Findings

### blocker

- **Allowlist-governed discovery is still too domain-wide to be a strong source-governance boundary.** The plan only commits to allowed official domains plus same-rank preference (`V2_PLAN.md:76-84`). The hardening notes keep the same shape: same-domain crawling from configured entrypoints (`HARDENING_NOTES.md:7-11`). The current config and code show why this is not enough: `configs/web_allowlist.yaml:19-32` starts from `https://europa.eu/` and `https://ec.europa.eu/`, `src/eubw_researcher/web/allowlist.py:13-14` validates only the hostname, and `src/eubw_researcher/web/fetch.py:333-354` follows any same-domain link with a token hit. Once fetched, the page inherits the domain policy's `source_kind` and `source_role_level` (`src/eubw_researcher/web/fetch.py:539-550`). That is safer than open web search, but it is still broad official-site crawling plus domain-level kind assignment, not document-level admission. The work order needs path-level or document-class allowlists and an explicit fetched-document admission test before web material can count as `regulation`, `implementing_act`, or `project_artifact`.

- **Approved web evidence is traceable by URL, but not reproducible enough for an inspectability-first system.** The plan requires visible fetch traces and source-bound output (`V2_PLAN.md:76-80`, `V2_PLAN.md:148-154`), but it does not require a frozen fetch snapshot or content hash. Current web ingestion creates a `SourceCatalogEntry` from the URL, title, and policy only (`src/eubw_researcher/web/fetch.py:538-550`); the artifact bundle writes `web_fetch_records.json` but not the fetched document, normalized text, or a capture manifest (`src/eubw_researcher/evaluation/runner.py:279-315`). The core source/citation model also has nowhere to store a response digest or capture id (`src/eubw_researcher/models/types.py:71-82`, `src/eubw_researcher/models/types.py:110-123`). If an official page changes, the approved evidence path is no longer reconstructible. V2 should require either run-local snapshots of admitted fetched sources or a manifest that records stable hashes plus the normalized text that actually entered review.

### important

- **The real-corpus gate proves scenario coverage, not corpus-layer coverage.** Section 2A says the real corpus "must cover at least" the main EU, implementing-act, standards, ARF, and project-artifact layers (`V2_PLAN.md:46-51`). The build path does generate a curated catalog and ingestion report (`scripts/build_real_corpus_catalog.py:42-50`). But the approval gate only requires green tests, scenario evals, and manual review bundles (`V2_PLAN.md:198-204`), and the review bundle does not carry the corpus-definition file or generated catalog (`src/eubw_researcher/evaluation/runner.py:279-315`). That means a selected source can fail ingestion or disappear from the archive without failing approval unless one of the five scenarios happens to exercise it. The work order should add a corpus coverage gate: every required source layer must have at least one successfully normalized, admitted, anchor-audited source in the curated real catalog, and that manifest must travel with each eval run.

- **Project-artifact scope is currently disciplined in config, but the plan does not yet lock that discipline.** The live selection is narrow and medium-rank (`configs/real_corpus_selection.yaml:115-147`), which is the right shape. But the plan's scope phrase "official project and pilot artifacts" is still broad (`V2_PLAN.md:30-35`, `V2_PLAN.md:46-51`), and there is no explicit admission rule tying those artifacts to a scenario, a governing-source dependency, or a cap on how many can join the default corpus. Without that, corpus growth pressure will fall on medium-rank material first, which increases review burden and weakens source governance long before anyone notices. V2 should say that project artifacts remain medium-rank, attributable, scenario-linked, and quantitatively bounded.

### minor

- **The plan should make one more boundary explicit: successful normalization is necessary, not sufficient, for evidence admission.** Section 2A correctly says failed normalization must stay explicit (`V2_PLAN.md:53-61`), and the hardening notes correctly keep malformed fetched documents out of the approved ledger (`HARDENING_NOTES.md:9-17`). What is still implicit is that a successfully normalized discovery result is not automatically an admissible research source. Adding that sentence would keep normalization scope from being mistaken for source-governance scope.

## 2. Summary verdict

Overall verdict: `not ready for approval as written`

Short rationale: the V2 plan closes the meaningful V1 limits around seed-only discovery and markdown-centric corpus handling, and it stays well away from uncontrolled open-web search. But two source-governance controls are still under-specified for an inspectability-first release: what exactly qualifies as an admissible official web document, and how approved fetched evidence remains reproducible under review.

## 3. What the corpus/discovery plan gets right

- It moves the system to a real local corpus by default while keeping fixtures for deterministic regression work (`V2_PLAN.md:39-61`). That is the right V2 progression.
- It keeps the discovery boundary defensive: local-gap triggered, allowlist-only, no arbitrary-site search, and no vendor/blog/commentary basis for core claims (`V2_PLAN.md:76-84`).
- It explicitly broadens normalization to real archive formats that matter in practice: `html`, `pdf`, and `xml`, with explicit failure visibility instead of silent degradation (`V2_PLAN.md:53-61`; `HARDENING_NOTES.md:13-17`).
- It preserves the key source-governance rule that same-rank or higher official material must beat lower-rank web material (`V2_PLAN.md:79`; `HARDENING_NOTES.md:7-10`).
- It keeps the ledger and review artifacts central rather than hiding discovery behavior behind answer text (`V2_PLAN.md:88-119`, `V2_PLAN.md:148-160`).

## 4. Missing controls or unrealistic assumptions

- Domain allowlists are being treated as if they were source-class allowlists. On small standards sites that can be close enough; on `europa.eu` and `ec.europa.eu` it is not.
- The plan assumes trace files are enough for inspectability, but URL-level traces are weaker than evidence capture. For approved web evidence, review needs a stable object, not only a URL plus timestamp.
- Corpus coverage is defined at the selection-file level, not at the successfully ingested catalog level. That is too optimistic for long-form mixed-format archives.
- "Official project and pilot artifacts" is realistic as a bounded aid layer, but unrealistic as an unconstrained category. Without inclusion rules, it will become the easiest place for corpus sprawl.

## 5. Risks of corpus or discovery drift

- Discovery drift inside official domains: the system avoids arbitrary web search but can still wander too broadly inside very large official sites.
- Source-kind drift: landing pages, indexes, or generic official pages can be treated as high-rank governing material if kind assignment stays domain-based rather than document-based.
- Reproducibility drift: approved web citations may stop being auditable once upstream pages change, even when the run-level artifacts still exist.
- Corpus drift toward medium-rank material: once the obvious EU acts and standards are selected, growth pressure will likely accumulate in project artifacts unless the plan explicitly caps and justifies them.

## 6. Recommended changes before approval

1. Add a fetched-document admission contract to V2. Require path-level or document-class allowlists per domain, plus explicit exclusion of homepages, news pages, generic indexes, and navigation pages from the approved evidence path unless a second rule promotes a concrete canonical document.
2. Add reproducible fetch capture to the artifact model. For every approved web source, persist either the fetched file itself in the run directory or a manifest with content hash, content type, canonical URL, discovered-from URL, and the normalized text that entered ingestion.
3. Add a corpus coverage gate. Approval should fail if any required source layer lacks at least one successfully normalized, admitted source in the curated real catalog.
4. Include the selected-corpus manifest in each eval bundle. At minimum: the resolved curated catalog or a hash-addressed export of it, plus the ingestion report used for that run.
5. Tighten project-artifact scope. Require attributable issuer, scenario linkage, medium-rank treatment, and a small default-corpus ceiling unless a new artifact is explicitly justified in review.
6. State directly that successful normalization does not by itself authorize evidence admission; source-governance checks still apply after normalization.
