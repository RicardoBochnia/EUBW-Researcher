# Option A V2 Plan Review

Status: completed
Reviewer: v2-reviewer-1
Date: 2026-04-01
Review target: [V2_PLAN.md](../V2_PLAN.md)

## 1. Required inputs

- [../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [../PLAN.md](../PLAN.md)
- [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)
- [../HARDENING_NOTES.md](../HARDENING_NOTES.md)
- [../V2_PLAN.md](../V2_PLAN.md)

## 2. Review goal

Assess whether V2_PLAN.md is a strong next-version work order for Option A: whether it advances the research-assistant vision, maintains requirements fit and architecture continuity, and stays scope-disciplined.

## 3. Findings

### P1 / blocker

- None found.

### P2 / important

- **Real-corpus eval pass criteria are undefined.** V2_PLAN.md section 4 states "real-corpus eval passes 5/5 configured scenarios" as a gate condition. But neither V2_PLAN.md nor HARDENING_NOTES.md defines what "passes" means for real-corpus runs. Fixture runs can use deterministic expectations; real-corpus runs cannot. HARDENING_NOTES.md says "real-corpus review readiness means reviewable, uncertainty-aware, source-bound output on the real corpus, not exact textual parity with the fixture corpus." The V2 plan needs to translate this principle into concrete pass/fail criteria for automated real-corpus eval. Without this, the V2 gate condition is procedural rather than testable. Candidates: artifact completeness checks, no-blocked-claims-in-answer checks, or structural quality checks that can be automated.

- **Discovery depth and breadth bounds are not specified.** V2_PLAN.md section 2B says official discovery moves "from the V1 seed-only pattern toward allowlist-governed official discovery." HARDENING_NOTES.md mentions a "depth-limited crawl from configured official entrypoints." The V2 plan does not specify what controls discovery depth, maximum pages per domain, or how crawl scope is bounded within allowed domains. Without explicit bounds, an allowlisted domain with deep link structures could produce unbounded crawl behavior. This needs at least a configurable depth limit and a per-domain page cap as V2 defaults.

- **Query analyzer generalization has no acceptance test.** V2_PLAN.md section 2B says the query intent analyzer "must no longer rely on narrow scenario-like patterning" and "must generalize across" six named use cases. This is the right goal but lacks a falsifiable acceptance criterion. How does a reviewer distinguish a genuinely generalized analyzer from one that pattern-matches six scenarios instead of five? At minimum, V2 should require at least one out-of-distribution query (not matching any named scenario) to pass through the analyzer without failure or degradation.

### P3 / minor

- **Corpus versioning is absent.** V2 introduces `configs/real_corpus_selection.yaml` as "the authoritative and inspectable corpus-definition file" (section 2A). But there is no version-pinning or manifest mechanism that ties a specific corpus state to a specific eval run. If documents are added or updated in the archive, previous eval results become non-reproducible. A lightweight manifest (hash or list of admitted source ids per eval run) stored alongside eval artifacts would close this gap without heavy infrastructure.

- **Ingestion robustness is qualitative.** V2_PLAN.md section 2A says ingestion "must robustly support real long-form archive documents, not only short synthetic markdown." This is a real operational need, but "robustly" is not operationalized. The unit test list in section 4 partially addresses this ("ingestion and normalization for real html, pdf, and xml archive inputs"), but there is no minimum-document-size or minimum-complexity threshold that would distinguish robust from fragile. Consider naming at least one long-form reference document as a required ingestion test anchor.

- **Grouping quality criteria are not specified.** The `provisional_grouping.json` artifact (section 2C) defines structure (label, claim_ids, source_ids, provisional) and the rule that provisional must always be true. But there is no quality criterion for the grouping itself. A trivial grouping (one group per claim, or one group for everything) would satisfy the structural contract. The requirements basis (section 2, primary success scenario) says the outcome should provide "a provisional grouping of findings" that is useful to the researcher. V2 should specify at least a minimal quality signal, such as requiring more than one group when more than one thematic cluster exists in the evidence.

- **Regression policy between V1 and V2 is implicit.** The V2 plan introduces new capabilities (real corpus, discovery, grouping) but does not state whether V1 fixture-corpus behavior must be preserved as a regression baseline. Section 4 says "fixture eval passes 5/5 configured scenarios," which implies backward compatibility. Making this explicit as a regression constraint would prevent accidental V1 breakage during V2 work.

## 4. Summary verdict

- Overall verdict: `ready with revisions`
- Short rationale: The V2 plan is well-structured, scope-disciplined, and faithful to both the requirements basis and the Option A architecture. It makes the right progression from V1 (fixture-based validation toward real-corpus research breadth) without inflating scope or reopening architecture. The three P2 items (real-corpus pass criteria, discovery bounds, analyzer generalization test) are not blockers because they do not change the V2 direction, but they must be resolved before the V2 gate can function as a real quality check rather than a procedural formality.

## 5. What the V2 plan gets right

- **Architecture continuity is explicit and protected.** The "architecture stays fixed" declaration in section 1 is unambiguous: evidence-first, staged, inspectable, source-rank-aware, no graph-first redesign, no multi-agent orchestration, no separate UI. This directly honors PLAN.md and IMPLEMENTATION_PLAN.md section 3 frozen design choices.
- **Real corpus as default is the right V2 progression.** V1 proved the pipeline on fixtures. V2 correctly shifts to real long-form documents as the primary research base, which is where the actual research-assistant value lives.
- **The provisional_grouping.json artifact directly addresses the primary success scenario.** The requirements basis (section 2) says the minimum useful outcome includes "a provisional grouping of findings" that is "provisional rather than the final research result." V2 delivers exactly this, with the disciplined `provisional: true` constraint.
- **Unified review gate across fixture and real corpus.** Same scenario ids, same artifact bundle shape, same review vocabulary. This prevents fixture-only validation from masking real-corpus problems.
- **Scope boundaries are maintained with precision.** Germany remains best-effort (requirements basis section 10). No freshness automation (requirements basis section 5, optional/later). No UI (IMPLEMENTATION_PLAN.md section 8). No broad member-state comparison (requirements basis section 6, first cut under scope pressure). No opinion-piece primary basis (requirements basis section 9).
- **Web expansion stays defensive.** Allowlist-only, gap-gated, same-rank preference before lower-rank. This directly implements the web expansion policy from requirements basis section 9.
- **The priority restatement in section 5 is correct.** "Correctness, traceability, and source-bound synthesis still win over latency and over broader but weaker coverage" preserves the requirements basis section 6 quality hierarchy.
- **Blocked-entry treatment is well-specified.** Visible in ledger and review artifacts, absent from final answer. This satisfies the non-negotiable property (requirements basis section 6) while preserving auditability.
- **The V2 gate criteria in section 4 are concrete and auditable.** Six conditions, each verifiable. This is materially stronger than a subjective "V2 feels ready" gate.

## 6. Missing decisions or ambiguities

- **Real-corpus eval pass/fail definition.** The V2 gate requires 5/5 real-corpus scenarios to pass, but does not define what constitutes a pass. Must be specified before the gate can be used. See P2 finding above.
- **Discovery crawl bounds.** Depth limit, page cap, and timeout defaults for official discovery crawling. Must be specified as V2 defaults in config. See P2 finding above.
- **Analyzer generalization acceptance test.** At least one non-scenario query must be required to demonstrate generalization beyond named scenarios. See P2 finding above.
- **Corpus manifest for eval reproducibility.** A mechanism to tie eval runs to a specific corpus state. See P3 finding above.
- **Grouping quality floor.** A minimal quality signal for provisional_grouping.json beyond structural conformance. See P3 finding above.
- **V1 regression constraint.** Explicit statement that V1 fixture-corpus behavior is a regression baseline for V2 work. See P3 finding above.

## 7. Scope or architecture drift risks

- **Low risk overall.** The V2 plan is notably disciplined about not expanding scope or reopening architecture.
- **Official discovery is the highest-drift-risk area.** Moving from seed-only to depth-limited crawling is a meaningful operational expansion. The V2 plan correctly keeps it allowlist-bounded, but crawl configuration tuning could become a recurring maintenance burden. Mitigation: specify conservative defaults (shallow depth, low page cap) and treat deeper crawling as a future expansion rather than a V2 optimization target.
- **Generalized query analyzer could expand indefinitely.** "Must no longer rely on narrow scenario-like patterning" is a generalization goal. Generalization work has no natural stopping point. Mitigation: define a concrete acceptance test (see P2) and treat anything beyond that as post-V2.
- **No architecture drift detected.** The plan does not reintroduce persistent graphs, multi-agent patterns, broad member-state machinery, freshness automation, or UI. All six IMPLEMENTATION_PLAN.md section 8 non-goals are preserved.

## 8. Recommended changes before approval

1. **Define real-corpus eval pass criteria** (P2). Add a concrete definition of what "passes" means for real-corpus scenario runs, distinguishable from fixture-corpus pass criteria. This can be structural (complete artifact bundle + no blocked claims in answer + manual review signed off) rather than content-identical to fixture expectations.
2. **Specify discovery bounds as V2 defaults** (P2). Add configurable depth limit and per-domain page cap to the V2 discovery contract, with conservative initial values. Reference these in the test plan.
3. **Add an out-of-distribution query to the V2 acceptance gate** (P2). Require at least one query that does not match any of the five named scenarios to pass through the analyzer and produce a reviewable artifact bundle. This makes the generalization claim testable.
4. **Add a corpus manifest to eval artifact bundles** (P3). Store the list of admitted source ids (or a hash of the corpus selection config) alongside each eval run so that results can be tied to a specific corpus state.
5. **State the V1 regression constraint explicitly** (P3). Add one sentence confirming that V1 fixture-corpus eval behavior is a regression baseline for V2.
6. **Add a minimal quality floor for provisional grouping** (P3). Require that grouping-capable runs produce more than one group when the approved ledger contains claims spanning more than one thematic area. This prevents trivially conformant but useless groupings.
