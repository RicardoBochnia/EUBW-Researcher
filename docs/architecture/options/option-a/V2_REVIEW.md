# Option A V2 Review

Status: consolidated final review of the V2 review wave
Review target: [V2_PLAN.md](./V2_PLAN.md)

## 1. Reviewed inputs

- Requirements basis: [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Architecture basis: [./PLAN.md](./PLAN.md)
- Implementation baseline: [./IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
- Hardening baseline: [./HARDENING_NOTES.md](./HARDENING_NOTES.md)
- V2 work order under review: [./V2_PLAN.md](./V2_PLAN.md)
- Reviewer inputs:
  - [./reviews/v2-reviewer-1.md](./reviews/v2-reviewer-1.md)
  - [./reviews/v2-reviewer-2.md](./reviews/v2-reviewer-2.md)
  - [./reviews/v2-reviewer-3.md](./reviews/v2-reviewer-3.md)
  - [./reviews/v2-reviewer-4.md](./reviews/v2-reviewer-4.md)

## 2. Findings

### blocker

- **Repeated reviewer convergence: the V2 acceptance gate is not yet a real quality gate.** Multiple reviewers converged that [V2_PLAN.md](./V2_PLAN.md) defines infrastructure completion more clearly than research-quality acceptance. The plan requires green tests, scenario passes, artifact bundles, and a reviewed bundle, but it does not define what a successful real-corpus pass means or what "fully reviewed" must establish. This is materially inconsistent with the requirements basis in [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md), which makes useful, source-bound synthesis the primary objective and unsupported claims the non-negotiable failure mode. Before approval, the gate needs explicit real-corpus pass criteria and at least one human judgment artifact that records substantive correctness and usefulness, not only structural completeness.

- **Repeated reviewer convergence: the V2 plan understates the main migration point from the current baseline.** Reviewer convergence was weaker here than on the gate, but the core point is still strong: the plan treats analyzer generalization as one workstream among several even though, from the current baseline, replacing scenario-bound query routing and hand-authored claim-target assumptions is the prerequisite refactor for broader corpus use, more realistic grouping, and less brittle retrieval behavior. As written, [V2_PLAN.md](./V2_PLAN.md) reads too much like a clean-sheet work order and not enough like a delta from the current Option A baseline captured in [./IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) and [./HARDENING_NOTES.md](./HARDENING_NOTES.md). This is a work-order blocker because sequencing is part of the review target.

- **Single-reviewer concern, accepted as a blocker: official discovery governance is still too coarse for an inspectability-first release.** [V2_PLAN.md](./V2_PLAN.md) keeps discovery allowlist-only and gap-gated, which is directionally right, but the review wave surfaced a stronger governance problem: domain-level allowlisting is not yet the same thing as document-level admission. For very broad official domains, V2 needs tighter fetched-document admission rules before discovered material can count as governing or otherwise admissible evidence. Without that, the plan leaves too much room for source-kind drift under the label of "official" discovery.

### important risk

- **Repeated reviewer convergence: real-corpus evaluation is not yet operationally defined enough to be reproducible or reviewable.** Reviewers independently flagged the lack of concrete real-corpus pass criteria, the absence of an explicit corpus manifest or corpus-state tie to each run, and the risk that real-corpus expectations may drift away from fixture expectations without clear review. This does not reopen Option A, but it does mean the V2 gate can otherwise become procedural rather than decision-grade.

- **Repeated reviewer convergence: discovery bounds need explicit defaults.** The move from seed-only expansion to allowlist-governed official discovery is the right V2 step, but the work order should specify depth, page, and timeout bounds in config rather than leaving crawl scope implicit. This is both a source-governance issue and a runtime-discipline issue.

- **Repeated reviewer convergence: the ledger and retrieval path still need a stronger layered-evidence contract.** The V2 plan says the ledger must preserve governing, supporting, and contradictory evidence across layers, but the review wave raised a credible implementation risk that the current retrieval flow resolves too early after the first direct support. The work order should explicitly require continued evidence gathering for layered questions instead of allowing a first-hit path to appear V2-complete.

- **Single-reviewer concern, but material: broader real-corpus use likely needs shared-ingestion or cached corpus reuse.** This is an execution realism risk rather than an architecture problem. If V2 broadens the selected corpus while still rebuilding ingestion repeatedly per run or per scenario, the gate will become expensive enough to discourage regular use.

- **Single-reviewer concern, but material: approved fetched evidence is traceable by URL but not yet reproducible enough.** For approved web evidence, visible fetch traces alone are weaker than inspectable captures or stable content digests. A reproducibility contract for admitted fetched sources would strengthen reviewability without changing the architecture.

### improvement

- **Repeated reviewer convergence: provisional grouping needs a minimal quality floor.** The work order correctly adds `provisional_grouping.json`, and that is well aligned with the primary success scenario in [../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md). But the current contract is mostly structural. V2 should require at least non-trivial grouping and resolvable `claim_ids` and `source_ids`.

- **Repeated reviewer convergence: V1 regression expectations should be made explicit.** The plan already implies fixture continuity, but it should say plainly that V1 fixture behavior remains a regression baseline for V2.

- **Single-reviewer concern: add at least one out-of-distribution query to prove analyzer generalization.** This is a good tightening move for the generalization claim in [V2_PLAN.md](./V2_PLAN.md).

- **Single-reviewer concern: add a corpus coverage gate, not only scenario coverage.** If V2 says the real corpus must cover core regulation, implementing acts, standards, ARF, and official project artifacts, the gate should verify successful admitted coverage at the catalog level, not only scenario-level exercise.

- **Single-reviewer concern: keep project-artifact growth explicitly bounded.** The requirements basis allows project artifacts as medium-rank support, but V2 should keep their inclusion attributable, scenario-linked, and quantitatively controlled.

## 3. Consolidated verdict

The V2 plan is directionally strong and remains faithful to Option A. The review wave does **not** reveal a reason to reopen the architecture choice in [./PLAN.md](./PLAN.md). The main problem is different: as a work order, [V2_PLAN.md](./V2_PLAN.md) is not yet sharp enough about the migration sequence, the quality gate, and the discovery-governance boundary.

In short, the architecture remains sound; the work order needs revision before it is approval-ready.

## 4. What the V2 plan gets right

- It keeps Option A fixed as an evidence-first, staged, inspectable, source-rank-aware architecture and does not drift toward graph-first redesign, multi-agent orchestration, or UI expansion.
- It makes the real corpus the primary research base while preserving fixtures for deterministic regression work.
- It keeps official web expansion defensive: gap-gated, allowlist-bounded, and explicitly not open-web search.
- It directly supports the primary success scenario by requiring `provisional_grouping.json` as a traceable, explicitly provisional research artifact.
- It preserves the right V1-to-V2 priorities from the requirements basis: correctness, traceability, and source-bound synthesis over latency or broader but weaker coverage.

## 5. What must change before approval

- Define what a real-corpus scenario pass means in V2, and separate that from fixture-style deterministic checks.
- Add a real human review artifact and acceptance rule for at least the primary success scenario and one regulation-heavy scenario. Auto-generated review metadata is not enough.
- Rewrite the plan as a delta-from-current-baseline work order. Mark already-landed baseline behavior versus real V2 delta.
- Front-load the migration away from scenario-bound query routing and hand-authored claim-target assumptions.
- Add explicit discovery bounds and a fetched-document admission contract so official-domain discovery does not become domain-wide evidence admission.

## 6. What can stay open for V2

- Exact grouping logic can remain provisional if the output stays traceable and non-trivial.
- Stronger corpus caching strategy can be scoped as a pragmatic V2 execution step rather than a reopened architecture choice.
- Corpus-manifest, fetch-capture, and broader reproducibility improvements can stay lightweight as long as each approved run is reviewable and tied to a concrete corpus state.
- Wider national coverage, freshness automation, and broader member-state comparison can remain outside the V2 approval path.

## 7. Gate recommendation

`not ready`
