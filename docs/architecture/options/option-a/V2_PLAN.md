# Option A V2 Plan

Status: revised after V2 review wave 1
Selected architecture basis: [PLAN.md](./PLAN.md)
V1 reference points:
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
- [HARDENING_NOTES.md](./HARDENING_NOTES.md)
- [REVIEW_GUIDE.md](./REVIEW_GUIDE.md)
Purpose: define the next complete research version of Option A as an explicit delta from the accepted V1 slice

## 1. V2 objective

Option A V2 is not a production-hardening-only release.
It is the next complete research version of the evidence-first architecture, intended to move beyond the V1 reviewable slice toward real research breadth.

V2 should:
- use the local real corpus as the default research base
- support stronger official-source discovery and cross-layer research
- preserve the Option A evidence-first and source-rank-aware control model
- improve the primary research use case of extracting and provisionally structuring Business Wallet requirements

The architecture stays fixed:
- evidence-first
- staged and inspectable
- source-rank-aware
- no graph-first redesign
- no multi-agent orchestration
- no separate UI

Primary source scope for V2:
- EU regulation and directly relevant implementing acts
- referenced technical standards
- official project and pilot artifacts

Germany and wider national material remain controlled best-effort scope, not primary V2 scope.

## 1.1 V2 as a delta from the accepted V1 baseline

The current accepted V1 baseline already provides:
- an inspectable Option A pipeline
- fixture and real-corpus review gates
- reviewable artifact bundles
- allowlist-bounded web expansion
- visible claim-state handling

V2 is not a clean-sheet rewrite.
It is the next work order on top of that baseline.

Already landed baseline capabilities must be preserved as regression guarantees:
- the V1 fixture scenario suite remains green
- the current artifact bundle remains stable
- the existing V1 review limits from [HARDENING_NOTES.md](./HARDENING_NOTES.md) remain explicit until V2 replaces them

The primary V2 deltas are:
- move from scenario-near query routing to generalized research-question analysis
- move from seed-only official fetch to governed official discovery and stricter document admission
- move from reviewable real-corpus output to a stronger real-corpus quality gate
- add a source-bound provisional grouping artifact for the primary Business Wallet requirements path

## 1.2 Ordered migration sequence

The V2 work order must be implemented in this order:

1. Generalize the analyzer and retrieval-target selection away from scenario-bound routing and hand-authored claim-target assumptions, together with the paired test/config transition that binds expected intent routing into eval scenarios and regression checks.
2. Tighten official discovery governance and fetched-document admission before expanding corpus breadth.
3. Expand real-corpus normalization and catalog coverage for the V2 source families.
4. Strengthen the layered ledger and add provisional grouping for the primary success scenario.
5. Close the unified V2 verification gate on both fixture and real-corpus paths.

This sequence is mandatory.
The analyzer migration is not one workstream among many; it is the enabling refactor for the rest of V2.
This migration is only complete when the paired scenario config, eval wiring, and regression tests have been updated so analyzer drift becomes a gate failure rather than a late discovery.

## 2. V2 workstreams

### A. Real corpus as the primary base

The local real corpus under `artifacts/real_corpus/archive` remains the standard path for V2.
Fixtures remain in place for unit tests, thin-slice tests, and deterministic regressions.

`configs/real_corpus_selection.yaml` becomes the authoritative and inspectable corpus-definition file for V2.

The V2 real corpus must cover at least:
- core EU EUBW / eIDAS regulation material
- directly relevant implementing acts and annex material
- current published OpenID4VCI and OpenID4VP standards
- ARF
- official EUDI / EC project artifacts relevant to relying party registration and information

V2 ingestion and normalization must robustly support real long-form archive documents, not only short synthetic markdown.
For local archive inputs, the supported normalization targets must include:
- markdown
- html
- pdf
- xml

If a source format cannot be normalized safely, the failure must stay explicit in ingest reports and review artifacts.
No silently degraded source may enter the approved evidence path.

V2 must also introduce a corpus coverage gate at the catalog level.
The selected real corpus is only acceptable if it contains admitted coverage for all of these families:
- at least one governing EU regulation source
- at least one directly relevant implementing-act or annex source
- at least two current technical standards when the scenario set depends on protocol comparison
- at least one ARF source
- at least two official project or pilot artifacts for relying party registration / information

V2 execution must reuse built catalog and normalized corpus artifacts across runs.
Full archive rebuild per scenario is not acceptable as the normal V2 verification path.

The corpus coverage gate must emit an inspectable artifact:
- `corpus_coverage_report.json`

This report must be tied to the selected corpus state and contain at least:
- corpus selection id or catalog path
- generation timestamp
- admitted source counts by source family
- admitted source ids per required family
- missing coverage flags if any required family is not satisfied

### B. Retrieval and official discovery at V2 level

The query intent and scope analyzer must no longer rely on narrow scenario-like patterning.
It must generalize across:
- the primary success scenario
- Scenario A
- Scenario B
- Scenario C
- the high-risk failure pattern
- the Business Wallet requirements extraction use case

Retrieval must follow the configured hierarchy and precedence model strictly, not only coarse role levels.

Web expansion moves from the V1 seed-only pattern toward allowlist-governed official discovery:
- discovery only on explicitly allowed official domains, standards bodies, or attributable official project sources
- discovery only after a documented local gap
- same-rank or higher relevant official material must be preferred before lower-rank web material
- every discovery and fetch step must remain visible in gap records and fetch artifacts

V2 remains defensive:
- no open web search across arbitrary sites
- no vendor, blog, or commentary material as the main basis for core claims

V2 official discovery defaults:
- maximum discovery depth: one link hop from an allowlisted seed or listing page
- maximum admitted fetched documents per domain per run: `10`
- maximum admitted fetched documents per full run: `25`
- per-document fetch timeout: `10s`
- only same-domain documents or explicitly configured canonical cross-domain standards/project links may be followed
- navigational, marketing, or news pages are not admissible evidence targets unless they are explicitly configured as official project documentation

These discovery defaults must be implemented as visible config-driven values, not hardcoded behavior.

V2 fetched-document admission contract:
- an allowlisted domain match alone is not sufficient
- every fetched document must have, before it becomes admissible evidence:
  - canonical URL
  - source domain
  - source kind
  - source role level
  - jurisdiction
  - content type
  - normalization status
  - content digest or stable archived snapshot reference
  - provenance record showing how the document was discovered
- if any of these fields is missing, the fetched document may appear in fetch artifacts but must not become approved evidence

V2 discovery must also preserve unresolved-layer discipline:
- discovery is allowed only for the unresolved target layer named in the gap record
- same-rank official material must be exhausted before lower-rank web material is admissible
- discovered project artifacts remain medium-rank even when hosted on official domains

### C. Stronger evidence ledger and primary research path

The ledger remains the central Option A artifact.
V2 must preserve:
- multiple supporting citations
- governing evidence
- contradictory evidence
- claim state
- citation quality
- source-role and precedence context

It must not collapse to a single winning citation when the research question depends on layered or conflicting evidence.

Final answers must be composed only from approved entries.
`blocked` entries remain visible in the full ledger and review artifacts, but not in the final user-facing answer.

For the primary question:
"What requirements apply to the Business Wallet, and how can they be provisionally structured?"

V2 must additionally emit a structured research artifact:
- `provisional_grouping.json`

This artifact is stored in the run directory and must minimally contain grouped requirement output with:
- `label`
- `claim_ids`
- `source_ids`
- `provisional`

Rules:
- `provisional` must always be `true` in V2
- this grouping is explicitly a research aid, not a final taxonomy
- grouping must stay source-bound and traceable back to claim and source ids

The answer layer must continue to make `confirmed`, `interpretive`, and `open` visible where mixed support exists.

The provisional grouping output must meet a minimal quality floor:
- at least two groups for the primary success scenario unless fewer than two supported requirement families exist
- every `claim_id` in the grouping must resolve to an actual ledger claim
- every `source_id` in the grouping must resolve to an admitted source used by those claims
- no empty groups are allowed

### D. Unified V2 review and acceptance gate

Fixture and real-corpus evaluation must use:
- the same scenario ids
- the same baseline artifact bundle shape
- the same review vocabulary

V2 must carry all five core scenarios on both fixture and real corpus:
- primary success scenario
- Scenario A
- Scenario B
- Scenario C
- high-risk failure pattern

The binding V2 entrypoint for evaluation is:
- `scripts/run_eval.py --all --catalog ...`

Direct runs through `scripts/answer_question.py` must emit the same reviewable artifact bundle as eval runs.
If the run is a primary-success or clustering-capable path, the bundle must also include:
- `provisional_grouping.json`

V2 acceptance additionally requires a filled manual review artifact, not only a checklist template.

The mandatory manual review artifact for V2 is:
- `manual_review_report.md`

This report must live in the run directory and contain at least:
- scenario id
- corpus selection id or catalog path
- reviewer name/date
- correctness verdict
- usefulness verdict
- source-role / hierarchy verdict
- uncertainty-handling verdict
- discovery / gap-handling verdict if web expansion was exercised
- reviewer-visible approved fetched-source evidence for any approved web citation, including digest or stable snapshot reference plus provenance
- open follow-ups
- final accept / reject judgment for that reviewed run

## 3. Expected V2 artifacts and interfaces

### Required runtime and review artifacts

Every reviewable V2 run must be able to produce the baseline artifact bundle:
- `retrieval_plan.json`
- `gap_records.json`
- `ledger_entries.json`
- `approved_ledger.json`
- `web_fetch_records.json`
- `final_answer.txt`

Eval runs must additionally produce:
- `verdict.json`

Conditional extended artifacts:
- corpus-backed build or review gates must additionally produce `corpus_coverage_report.json`
- grouping-capable runs must additionally produce `provisional_grouping.json`
- formal manual review samples must additionally produce `manual_review_report.md`

Grouping-capable runs must additionally produce:
- `provisional_grouping.json`
- `manual_review_report.md` when the run is used as a formal V2 review sample

### Public interface expectations

No UI is introduced in V2.
The public operator surface remains:
- config-driven corpus selection
- scripts and CLI entrypoints
- reviewable artifact directories

The main operator entrypoints remain:
- corpus build / selection
- evaluation gate
- direct question answering

Any new interface added in V2 must remain backend- and agent-facing.

## 4. Test and acceptance plan

### Unit focus

V2 unit coverage must explicitly include:
- ingestion and normalization for real `html`, `pdf`, and `xml` archive inputs
- generalized query analysis for the primary scenario and Scenarios A/B/C/high-risk
- hierarchy and precedence handling, including same-rank tie-breaks
- document-only and anchor-degradation behavior, including the audited confirmable path
- official discovery, allowlist admission, and gap-gating rules

### Integration focus

V2 integration coverage must include:
- complete five-scenario run on fixture corpus
- complete five-scenario run on real corpus
- at least one regulation-heavy case that actually exercises web expansion
- primary success scenario producing both a reviewable answer and `provisional_grouping.json`
- at least one out-of-distribution research question that is not hard-coded to the current scenario wording but should still map into the same source families and answer discipline

### V2 gate

V2 is only accepted if all of the following are true:
- the full testsuite is green
- fixture eval passes 5/5 configured scenarios
- real-corpus eval passes 5/5 configured scenarios
- the V1 fixture suite remains green as an explicit regression baseline
- the real corpus coverage gate passes before scenario verdicts are interpreted
- `corpus_coverage_report.json` exists and proves admitted coverage for every required source family
- at least one manual review bundle for the primary success scenario has been fully reviewed
- at least one manual review bundle for a regulation-heavy case with discovery/gap handling has been fully reviewed
- both mandatory manual review bundles end in `accept`
- known residual limits are recorded in updated hardening notes

For V2, a real-corpus scenario counts as `pass` only if all of the following are true:
- the scenario verdict passes
- the answer is reviewable and source-bound
- no unsupported `blocked` claim appears in `final_answer.txt`
- mixed-support answers preserve `confirmed`, `interpretive`, and `open` visibly where applicable
- governing support is either present at the correct precedence layer or its absence is explicitly explained through gap records
- any approved fetched source satisfies the fetched-document admission contract

For V2, a manual review bundle counts as `fully reviewed` only if:
- `manual_review_report.md` exists
- the report records explicit judgments for correctness and usefulness
- the report records whether hierarchy and uncertainty handling were acceptable
- the report records any reasons the answer would not yet be reusable for research notes or team work
- the report records final accept / reject judgment explicitly

## 5. Assumptions and defaults

- V2 stays backend- and agent-facing.
- Germany remains best-effort scope; no broad member-state comparison engine is introduced.
- The architecture remains Option A.
- The real corpus remains inside the repo path but outside git under `artifacts/real_corpus/archive`.
- Freshness automation is still out of scope for V2; corpus refresh remains controlled through selection and manifest-like config files.
- If a tradeoff appears, correctness, traceability, and source-bound synthesis still win over latency and over broader but weaker coverage.
