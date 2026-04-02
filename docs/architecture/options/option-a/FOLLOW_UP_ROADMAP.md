# Option A Follow-Up Roadmap

Status: post-V2.2 follow-up ordering note
Scope basis:
- [SCENARIO_D_PLAN.md](./SCENARIO_D_PLAN.md)
- [LEGACY_EUBW_ARCHITECTURE_REVIEW.md](./LEGACY_EUBW_ARCHITECTURE_REVIEW.md)

Purpose: define a practical implementation order for the remaining tracked follow-up issues without turning them into a new large masterplan

## 1. Recommended planning posture

Do not create another large masterplan for the current follow-up set.

The current open items are better handled as:
- a small ordered roadmap
- with one active work item or one small wave at a time
- while GitHub Issues remain the canonical backlog

Use this file for:
- sequencing
- dependency logic
- what should be tackled together
- what should wait for evidence

Use GitHub Issues for:
- the actual work queue
- scope and acceptance details
- prioritization changes over time

## 2. Recommended order

### Wave 0: close current Option A scope

Goal:
- finish the currently accepted Option A closeout before broadening the surface further

Items:
- execute [SCENARIO_D_PLAN.md](./SCENARIO_D_PLAN.md)

Why first:
- this locks the current architecture state
- it avoids mixing closeout work with new extension work

### Wave 0.5: verification hardening

Goal:
- make future changes fail earlier in tests and gates instead of being discovered late in review

Items:
- [#17](https://github.com/RicardoBochnia/EUBW-Researcher/issues/17) unify the default test runner and include closeout gate coverage
- [#16](https://github.com/RicardoBochnia/EUBW-Researcher/issues/16) add non-skippable gate regressions and real-corpus backstops
- [#15](https://github.com/RicardoBochnia/EUBW-Researcher/issues/15) expand analyzer, discovery, and cross-artifact contract regression tests

Why here:
- these items strengthen the safety net before the next wave of feature and workflow changes
- they reduce the risk that roadmap work lands with weak regression protection
- they are more valuable early than after several new extensions have already been added

Recommended order inside the wave:
1. `#17`
2. `#16`
3. `#15`

Rationale:
- first make the canonical green test command truthful
- then harden the non-skippable gate and real-corpus-adjacent failure paths
- then broaden the regression matrix around analyzer, discovery, answer forms, and artifact contracts

### Wave 1: strengthen the operating surface

Goal:
- make the current system easier to use, reason about, and review before adding more retrieval power

Items:
- [#6](https://github.com/RicardoBochnia/EUBW-Researcher/issues/6) stable agent-facing runtime facade
- [#7](https://github.com/RicardoBochnia/EUBW-Researcher/issues/7) corpus selection, coverage, and current-state reporting
- [#8](https://github.com/RicardoBochnia/EUBW-Researcher/issues/8) curated real-question manual-review regression pack

Why this wave comes next:
- these items improve operational clarity and reviewability
- they reduce the risk of making later retrieval changes without a strong validation surface
- they are the best-value lessons from the legacy `EUBW` repo

Recommended order inside the wave:
1. `#6`
2. `#7`
3. `#8`

Rationale:
- first stabilize how agents and users enter the system
- then make corpus/state visibility explicit
- then anchor ongoing regression on real questions

### Wave 1.5: strengthen high-risk validation

Goal:
- extend the current trust surface with a reusable second-pass validation gate without turning the product into a multi-agent system

Items:
- [#14](https://github.com/RicardoBochnia/EUBW-Researcher/issues/14) generalize the Codex spawned validator into an optional high-risk and release gate

Why here:
- the spawned-validator pattern is already proven in Scenario D closeout
- it is most useful after Wave 1 has made runtime entry, corpus visibility, and real-question review more stable
- it should land before broader retrieval/discovery expansion, so those later changes have a stronger independent gate

### Wave 2: small recall and wording improvements

Goal:
- improve the current system conservatively without changing its shape

Items:
- [#5](https://github.com/RicardoBochnia/EUBW-Researcher/issues/5) small terminology and synonym layer
- [#2](https://github.com/RicardoBochnia/EUBW-Researcher/issues/2) freshness automation
- [#3](https://github.com/RicardoBochnia/EUBW-Researcher/issues/3) Germany beyond best effort

Why this is Wave 2:
- these improvements are useful, but they depend on having a more stable runtime and review surface first
- freshness and Germany support should land on top of a clearer corpus/state/reporting layer

Recommended order inside the wave:
1. `#5`
2. `#2`
3. `#3`

Rationale:
- terminology is the lightest, safest uplift
- freshness then makes corpus maintenance less manual
- Germany expansion should come after corpus management is more disciplined

### Wave 3: broader discovery extensions

Goal:
- widen source-finding power without collapsing governance

Items:
- [#4](https://github.com/RicardoBochnia/EUBW-Researcher/issues/4) broader official web discovery
- [#10](https://github.com/RicardoBochnia/EUBW-Researcher/issues/10) lightweight local lexical index
- [#9](https://github.com/RicardoBochnia/EUBW-Researcher/issues/9) narrow relation hints

Why this is later:
- broader discovery should not be added before runtime, review, and corpus accounting are stronger
- relation hints and local indexing are only useful if real question review shows repeatable retrieval pain

Recommended order inside the wave:
1. `#4`
2. `#10`
3. `#9`

Rationale:
- first improve bounded official discovery
- only then decide whether local indexing is still needed
- relation hints should be last and only for repeated cross-reference cases

## 3. Explicit evidence-gated items

These should not be scheduled proactively as near-term default work.
They should only move forward if the earlier waves show a concrete, repeated need.

Items:
- [#11](https://github.com/RicardoBochnia/EUBW-Researcher/issues/11) minimal explicit answer profiles
- [#12](https://github.com/RicardoBochnia/EUBW-Researcher/issues/12) semantic or dense retrieval
- [#13](https://github.com/RicardoBochnia/EUBW-Researcher/issues/13) targeted multi-pass analysis

Rule:
- do not start these just because they are available
- start them only if Wave 1 through Wave 3 evidence shows that the simpler path is not enough

## 4. Existing technical debt

This remains separate from the roadmap above:

- [#1](https://github.com/RicardoBochnia/EUBW-Researcher/issues/1) refactor V2.2 answer composer to reduce topology-specific complexity

Handling recommendation:
- treat `#1` as opportunistic technical debt
- do not let it block the roadmap unless the current code structure starts slowing down or destabilizing nearby work

## 5. Practical rule for execution

Recommended operating rule:
- at most one active wave at a time
- at most one or two active issues within a wave
- after each completed issue, reassess whether the next issue still belongs in the same position

This keeps the roadmap useful without freezing prioritization too early.

## 6. Bottom line

The right shape is:
- GitHub Issues as the real backlog
- this file as the ordering note
- no new giant masterplan

If the roadmap grows materially or starts spanning several quarters, then it should be replaced by a more explicit versioned planning document.
