# V2 Plan Review: Verification Quality

Reviewer: reviewer-3
Focus: verification model strength, falsifiability, proof of progress beyond V1
Date: 2026-04-01

---

## 1. Findings

### F1. The V2 gate is necessary-but-not-sufficient: it proves infrastructure, not research quality

**Severity: blocker**

The V2 gate (`V2_PLAN.md` section 4) defines six conditions for acceptance. Five of six are binary infrastructure checks (tests green, fixture eval 5/5, real-corpus eval 5/5, hardening notes updated, manual review bundle exists). The remaining condition ("at least one manual review bundle ... has been fully reviewed") is the only condition that touches research quality, and it has no defined acceptance criterion.

What "fully reviewed" means is never specified. A reviewer could check every box in `MANUAL_REVIEW_CHECKLIST.md`, find all answers weak, and the gate would still pass. The gate is a completeness gate, not a quality gate.

This matters because the V2 objective explicitly says it should "move beyond the V1 reviewable slice toward real research breadth." The gate does not measure breadth, depth, or correctness of the research output itself.

**Concrete gap:** No V2 acceptance criterion requires that an answer on the real corpus is *substantively correct* or *usefully informative* for the stated primary research question. The gate could pass with five scenarios producing technically well-formed but factually empty or misleading answers.

### F2. Automated scenario checks are structural, not semantic

**Severity: important**

The evaluation runner (`src/eubw_researcher/evaluation/runner.py`) checks:
- ledger entry counts (`min_ledger_entries`)
- presence of required claim states
- absence of forbidden states
- required/forbidden source ids in citations
- substring presence/absence in rendered answers
- gap record counts and reasons
- retrieval prefix ordering
- web metadata completeness
- document-only confirmed audit notes

These are well-designed structural checks. But none of them verify that the claim text is accurate, that the answer actually responds to the question asked, or that the evidence cited actually supports the claim it is attached to. The `required_answer_substrings` check in `configs/evaluation_scenarios.yaml` is the closest proxy, and it checks for the presence of a single short phrase (e.g., `"Member States may define national registration procedures"` for scenario B).

A system that returns the right substring inside an otherwise incorrect or incoherent answer would pass. This is a real risk because the pipeline is deterministic over fixtures and the checks were likely co-developed with the implementation.

### F3. Fixture and real-corpus eval use separate scenario configs, but only fixture expectations are visible

**Severity: important**

`runner.py:_scenario_config_path` silently switches to `configs/evaluation_scenarios_real_corpus.yaml` when a real-corpus catalog is detected. The fixture scenario config is committed and inspectable (`configs/evaluation_scenarios.yaml`). The real-corpus scenario config may have weaker or different expectations, and the V2 plan does not require that real-corpus expectations are reviewed or compared against fixture expectations.

This means "real-corpus eval passes 5/5" could be a weaker statement than "fixture eval passes 5/5" without anyone noticing, unless the reviewer independently inspects the real-corpus config file.

### F4. Manual review artifact is auto-filled, not human-filled

**Severity: important**

`MANUAL_REVIEW_CHECKLIST.md` describes a human review process. But `review.py:build_manual_review_artifact` auto-generates `manual_review.json` with six automated checks and a `filled: true` flag. The V2 gate requires "a filled manual review artifact, not only a checklist template" (`V2_PLAN.md` section 2D). The auto-generated artifact satisfies this condition without any human judgment.

The naming creates a false signal: `manual_review.json` with `filled: true` looks like a human reviewed it. In practice, it is a second automated check layer with no human in the loop.

### F5. No regression proof between V1 and V2

**Severity: important**

The V2 plan defines V2 as "the next complete research version" after V1. But neither the V2 gate nor any artifact captures what V1 produced for the same questions, making it impossible to verify that V2 actually improved over V1. A V2 answer could regress on a scenario that V1 handled correctly, and the gate would not detect it because it only checks V2 outputs in isolation.

### F6. The "real research breadth" claim has no measurable definition

**Severity: important**

The V2 objective says V2 should "move beyond the V1 reviewable slice toward real research breadth." This is the core V2 value proposition. But neither the V2 gate nor any acceptance criterion defines what "real research breadth" means in measurable terms. The only real-corpus-specific proof is that the same five scenarios pass on a larger corpus. This could be true even if the system ignores most of the real corpus.

### F7. Provisional grouping has no quality check beyond existence

**Severity: minor**

The V2 gate checks that `provisional_grouping.json` exists for the primary success scenario. The scenario config checks `require_provisional_grouping: true`. Neither the automated eval nor the manual review checklist verifies that the grouping labels are meaningful, that claim/source id references resolve, or that the grouping is non-trivial (e.g., not a single catch-all group).

### F8. No negative-case scenario tests a fundamentally wrong answer path

**Severity: minor**

The high-risk failure pattern scenario tests false elevation (ARF over governing standard). The missed-governing-source integration test (`test_missed_governing_source_creates_gap_record_and_visible_blocked_state`) tests a missing-source path. Both are good. But no scenario tests the case where the system produces a confidently wrong answer from correctly ranked sources --- e.g., misattributing a claim to a source that does not actually say what the claim says. This is the hardest failure mode for a research assistant and the one most likely to erode user trust.

---

## 2. Summary verdict

The V2 verification model is **well-designed for structural correctness** and significantly better than typical research-prototype evaluation. The artifact bundle, the scenario runner, the integration tests for web expansion, and the claim-state controller tests are all strong.

However, the model has a **critical gap at the semantic layer**: nothing in the V2 gate proves that the system produces *correct, useful research output*. The gate proves the pipeline is wired correctly, claim states are assigned by the rules, sources are ranked properly, and artifacts are written. It does not prove the answers are right.

For a V2 research version, this is a **conditional blocker**. The gate should be augmented before the V2 label implies research-grade confidence.

---

## 3. What the verification model gets right

- **Claim-state controller is thoroughly unit-tested.** `tests/unit/test_ledger_controller.py` covers confirmed, interpretive, blocked, open, document-only degradation, audited confirmation, cross-rank conflict handling, and precedence-aware tie-breaking. This is the strongest part of the verification model.
- **Integration tests exercise real failure modes.** The missed-governing-source test, the open-claim contradiction test, the web expansion tests (seed, discovery, rank preference, PDF normalization, malformed PDF rejection, XML normalization) are all scenario-grounded and falsifiable.
- **Artifact bundle is comprehensive and inspectable.** Every run produces a full trace from retrieval plan through gap records, ingestion report, ledger, approved ledger, web fetch records, and final answer. This makes manual review possible even if the automated gate misses something.
- **Web expansion verification is defense-in-depth.** The runner checks allowlist compliance, metadata completeness, gap-gating, and rejected-source exclusion from the approved ledger. The integration tests verify this end-to-end with real HTTP servers.
- **Scenario config is declarative and extensible.** Adding a new scenario with new expectations is config-only work, which keeps the verification model maintainable.

---

## 4. Weak or missing proof points

| Gap | What it means | Where to fix |
|-----|---------------|--------------|
| No semantic correctness check | Answers can be structurally valid but factually wrong | V2 gate needs at least one human-judged correctness assertion per scenario |
| "Fully reviewed" is undefined | Manual review gate is unfalsifiable | V2 gate must define minimum review evidence (e.g., reviewer sign-off artifact with explicit correctness judgment) |
| Real-corpus scenario config is invisible | Real-corpus gate strength is unverifiable without extra inspection | Require real-corpus scenario config to be committed and reviewed alongside fixture config |
| No V1-to-V2 regression baseline | Cannot prove V2 improved over V1 | Store V1 artifact snapshots and require V2 to match or exceed on the same questions |
| "Research breadth" is unmeasured | The core V2 value claim is not falsifiable | Define a minimum real-corpus coverage metric (e.g., number of distinct source documents actually cited across all five scenarios) |
| Provisional grouping is existence-only | Grouping quality is untested | Add at least: min group count > 1, all claim_ids resolve to ledger entries, all source_ids resolve to catalog entries |

---

## 5. Risks of false confidence

1. **The fixture eval is self-confirming.** Fixtures, scenario configs, and pipeline logic were co-developed. Passing 5/5 on fixtures proves internal consistency, not external validity. The real-corpus eval is the only independent signal, and its expectations are less visible.

2. **`manual_review.json` with `filled: true` creates an audit illusion.** A future reviewer seeing this artifact may assume a human reviewed the output. The auto-fill is useful as a preflight, but it should not carry the `filled` flag without actual human input.

3. **Substring checks reward template stability, not answer quality.** If the answer renderer always emits "Confirmed:" when a confirmed entry exists, the substring check always passes. It tests the renderer, not the research.

4. **The gate can pass with no real-corpus archive present.** Real-corpus integration tests are `skipUnless` the archive directory exists. If the archive is absent (e.g., in CI), the gate silently degrades to fixture-only. The V2 plan says real-corpus eval is required, but the test infrastructure does not enforce this.

5. **No adversarial or boundary-push scenario.** All five scenarios are "happy path with controlled difficulty." None tests a genuinely ambiguous question where the correct answer is "this is not answerable from the available sources." An `open`-only or `blocked`-only correct outcome is never the expected result of a passing scenario.

---

## 6. Recommended changes before approval

### Must-fix (blocker)

1. **Define a semantic acceptance criterion for the V2 gate.** At minimum: for the primary success scenario and one regulation-heavy scenario on the real corpus, a named human reviewer must produce a signed-off artifact that includes an explicit correctness judgment (not just a checklist pass). This artifact must be distinct from the auto-generated `manual_review.json`. Suggested path: add a `human_review.md` or `human_review.json` template that the reviewer fills manually, and require its presence (with non-template content) as a gate condition.

### Should-fix (important)

2. **Commit the real-corpus scenario config** (`configs/evaluation_scenarios_real_corpus.yaml`) and require it to be reviewed alongside the fixture config. If it intentionally differs from the fixture config, those differences must be documented in `HARDENING_NOTES.md`.

3. **Rename or restructure the auto-generated review artifact** so it cannot be confused with human review. Either rename it to `automated_review_prefill.json` and set `filled: false`, or add an explicit `human_reviewed: false` field that must be flipped by a human.

4. **Add a V1 baseline snapshot requirement.** Before V2 acceptance, store the V1 fixture-eval artifact bundles as reference. The V2 review must include at least a qualitative comparison showing V2 did not regress on any scenario V1 handled.

5. **Require the real-corpus archive to be present for V2 gate passage.** Either make the real-corpus integration tests non-skippable in the V2 acceptance context, or add a separate V2-specific gate script that fails if the archive is absent.

### Nice-to-have (minor)

6. **Add a minimal grouping quality check:** require `len(provisional_grouping) > 1`, require all `claim_ids` to resolve against the ledger, and require all `source_ids` to resolve against the catalog.

7. **Add one adversarial scenario** where the correct outcome is `blocked` or all-`open`, to prove the system can correctly say "I cannot answer this from available sources."
