# EUBW RAG Benchmark Root Cause Notes

Date: 2026-05-06

## Purpose

This note captures the current findings from comparing `EUBW-Researcher`
answers against the legacy EUBW repository under
`C:\Users\Admin\PycharmProjects\EUBW`.

It is intended as input for a later architecture decision. It is not yet a
final architecture recommendation.

## Current Observation

The current repository can produce strong answers when a question lands in a
specialized intent with suitable claim targets. The Q1-Q5 EUBW parity work
confirmed that: once explicit EUBW intents, facets, forbidden fallback claims,
and corpus additions were introduced, the new stack became much more useful.

The newer benchmark questions Q6-Q8 show a remaining architectural weakness:
the current pipeline still depends too heavily on hand-authored question
families. When the question is adjacent to an existing family but not actually
covered by it, the system produces answers that are plausible but thinner than
the legacy repo.

## Benchmark Delta

### Q6: Wallet-provider change and portability

Question:

`Was passiert bei einem Wechsel des Wallet-Providers mit Nachweisen, Mandaten, Vertrauenskette und Auditspur, wenn echte Portabilitaet gefordert wird?`

Observed current behavior:

- The current run routes the question into `eubw_audit_trail_analysis`.
- The selected targets focus on dispute retention, transaction logging,
  authorisation-event proofs, and log retention boundaries.
- This misses the main portability object model: migration object, list of
  credentials, non-device-bound attestations, device-bound re-issuance, and
  restored transaction log.

Legacy behavior:

- The legacy answer uses `SRC-W-TEC-35` / TS10 data portability and export.
- That source directly states that Wallet Units keep a transaction log and a
  migration object for backup, recovery, and migration.
- It also describes the migration process: create migration object, include
  credential list, include non-device-bound credentials and transaction log,
  import into the new Wallet Unit, re-issue PID and device-bound attestations,
  copy non-device-bound attestations, and restore the transaction log.

Likely cause:

- The current intent library has no provider-change / portability / migration
  intent.
- `SRC-W-TEC-35` is present in the archive catalog but not in the curated
  default corpus selection.
- The target-driven retrieval model cannot discover the missing portability
  structure unless a target asks for it.

### Q7: Multi-stage delegation chain

Question:

`Wie koennte eine mehrstufige Delegationskette technisch modelliert werden, etwa Geschaeftsfuehrer -> Bereichsleiter -> Mitarbeiter, ohne dass Nachvollziehbarkeit und Pruefbarkeit verloren gehen?`

Observed current behavior:

- The direct artifact routes the question to `broad_regulation_question`.
- The only approved claim is `broad_regulatory_answer`.
- The automated review still accepts the run because the generic acceptance
  gates only require approved, cited evidence and do not enforce delegation
  facets for this question.

Legacy behavior:

- The legacy answer does not need a dedicated "GF -> Bereichsleiter ->
  Mitarbeiter" rule.
- It retrieves reusable building blocks:
  - EBW aims to manage representation rights and mandates.
  - Users may act on behalf of the owner.
  - Access-control decisions can depend on attestations of the acting subject.
  - Authorisation outcomes should be fine-grained and auditable.
  - Formats, interoperability, policy language, constraint enforcement,
    logging, timestamping, and auditability are delegated to later
    specifications.
- The answer correctly marks the chain model as an automatic model proposal,
  not as a directly settled legal rule.

Likely cause:

- Current intent detection recognizes some mandate and authority questions,
  but not modeling questions about delegation chains, subdelegation, parent
  mandates, monotonic scope narrowing, or chain proofs.
- The current review gate treats fallback failure as an EUBW parity problem
  only for a narrow signal set. `Delegationskette` is outside that set.
- The old repo is claim-centered: it can retrieve relevant building-block
  claims without first matching a specific answer pattern.

### Q8: Source priority in conflict cases

Question:

`Welche Quelle sollte im Konfliktfall Vorrang haben, wenn Registerdaten, Wallet-gehaltene Nachweise und die aktuelle Unternehmensrealitaet auseinanderfallen?`

Observed current behavior:

- The current run routes the question into `eubw_lifecycle_analysis`.
- The answer retrieves register update, suspension/cancellation, retention,
  and mandate revocation controls.
- The conclusion is directionally right, but the evidence taxonomy is thin.

Legacy behavior:

- The legacy answer centers the rule around `authentic source`.
- It cites:
  - the definition of `authentic source`,
  - registrar verification against evidence/authentic sources/official
    electronic registers,
  - electronic verification mechanisms against authentic sources,
  - legal effect of attestations from public-sector authentic sources,
  - status and revocation management,
  - EBW owner-identification data as recorded in a register or official record.

Likely cause:

- The current lifecycle targets are operational lifecycle controls, not a
  source-precedence model.
- Several old-repo claims used in A2 exist in the broader archive/legacy KB
  but are not represented as current targets for this intent.
- `SRC-L-41` and the old claim index around PubEAA/authentic-source semantics
  are not part of the current curated default response path.

## Architecture-Level Finding

The current system is rigorous but brittle:

- It proves preselected claim targets well.
- It produces good artifacts once the question has a known intent.
- It gives reviewable ledgers, gap records, corpus coverage, and source-role
  qualifiers.
- But it is not naturally exploratory. If no target asks for the decisive
  concept, that concept usually does not surface.

The legacy EUBW system appears more flexible at question time:

- It has a larger precomputed claim base.
- It indexes claims semantically and densely.
- It stores `CLM-*` claims, `CH-*` chunks, source IDs, evidence tiers, and
  binding levels.
- It can answer unseen or adjacent questions by composing from existing
  domain claims rather than from a manually selected target list.
- It often exposes open issues because those uncertainties are part of the
  claim/source model, not only a composer behavior.

However, the legacy flexibility is not free:

- It depends on the breadth and quality of the precomputed claim inventory.
- Its answers are more naturally fluent and domain-rich, but the artifact
  discipline is weaker than the current repo's runtime ledger model.
- It can still miss issues if the claim corpus has no relevant claim or if
  claim quality is poor.

The likely architectural tension is therefore not "old flexible vs new good",
but:

- current repo: target-first, verification-first, lower flexibility;
- legacy repo: claim-first, retrieval-first, higher flexibility;
- desired repo: claim-first discovery plus verification-first acceptance.

## Why Adding More Specialized Intents Is A Smell

Adding Q6-Q8 intents would probably improve the immediate benchmark, but it
would repeat the same pattern as Q1-Q5:

1. Benchmark exposes gap.
2. Add question-specific intent and targets.
3. Answer improves for that family.
4. Next adjacent question exposes another gap.

That loop suggests the current architecture is overfitted to known question
families. For a research assistant, the system should instead discover likely
claim clusters from the corpus and then ask the verification layer to approve,
reject, qualify, or mark gaps.

Specialized intents are still useful for:

- answer rendering,
- acceptance gates,
- regression coverage,
- high-risk domains where exact facets are required.

But they should not be the primary mechanism by which the system discovers
the relevant knowledge.

## Evidence From Current Artifacts

Current repo:

- Q6 routes to `eubw_audit_trail_analysis` and only targets audit/retention
  claims.
- Q7 routes to `broad_regulation_question` and approves only
  `broad_regulatory_answer`.
- Q8 routes to `eubw_lifecycle_analysis`, which is adjacent but not the same
  as source precedence.
- The curated catalog currently includes 19 sources and omits TS10
  (`SRC-W-TEC-35`), Council Annex (`SRC-L-EBW-COUNCIL-01`), ARF main
  (`SRC-W-TEC-04`), and `SRC-L-41`.

Legacy repo:

- Claim schema has `binding_level` values: `binding`, `proposed`,
  `official_non_binding`, `non_binding`, `unknown`.
- Claim schema has `evidence_tier` values: `A`, `B`, `C`.
- Dense claim index contains 1464 indexed claims.
- The old corpus includes TS10 (`SRC-W-TEC-35`), Council Annex, ARF main,
  and additional legal fulltext sources used by A2.

## Candidate Architecture Directions

### Option 1: Keep target-first and add more intents

Description:

Continue adding specialized intents, targets, facets, and review gates for
each benchmark cluster.

Pros:

- Fast local improvements.
- Strong deterministic regression coverage.
- Fits current runtime facade and artifact model.

Cons:

- Scales poorly with new research questions.
- Encourages benchmark overfitting.
- Discovery remains weak.

### Option 2: Move toward claim-first retrieval

Description:

Import or rebuild a legacy-style claim index and make claim retrieval the
primary first pass. Intent detection would become secondary.

Pros:

- More flexible for unseen questions.
- Reuses domain claims across answer shapes.
- Better at surfacing adjacent but relevant concepts.

Cons:

- Requires claim generation, review, indexing, and refresh lifecycle.
- Needs quality controls so weak or stale claims do not dominate.
- May weaken the current ledger discipline unless integrated carefully.

### Option 3: Hybrid claim-discovery plus target-verification

Description:

Use broad claim retrieval to discover candidate concepts and source clusters,
then convert the discovered cluster into provisional targets for the existing
ledger/review pipeline.

Pros:

- Preserves the current repo's audit artifacts.
- Reduces dependence on pre-authored intents.
- Allows specialized intents to improve rendering and regression checks
  without being the only discovery path.
- Better fit for architecture-ready research assistance.

Cons:

- More complex controller design.
- Needs safeguards against noisy claim clusters.
- Requires a clear status model for discovered claims versus approved claims.

## Working Hypothesis

The old EUBW approach is more flexible at retrieval time because it is
claim-centered and has a broader claim/source universe. The current approach
is safer and more reviewable once the right targets exist, but too rigid as a
general research assistant.

The most promising architecture direction is likely a hybrid:

1. Retrieve candidate claims/chunks broadly from a claim-centered index.
2. Cluster them into provisional answer facets.
3. Run the current ledger/hierarchy/review machinery against those facets.
4. Use specialized intents only for high-confidence rendering and regression
   gates, not as the main discovery mechanism.

## Open Questions For Architecture Decision

- Should the legacy `CLM-*` claim corpus be imported, regenerated, or treated
  only as a benchmark/reference set?
- Should the runtime support dynamic claim-target creation from retrieved
  claim clusters?
- How should discovered claims be separated from approved ledger claims in the
  artifacts?
- What review threshold should prevent a broad fallback from being accepted
  for any EUBW-shaped question, not only the Q1-Q5 parity set?
- Should source-role modeling be expanded from `high/medium/low` to preserve
  `A/B/C` and `binding/proposed/official_non_binding/non_binding` explicitly?
- Which corpus sources are mandatory for EUBW-grade answers: TS10, Council
  Annex, ARF main, `SRC-L-41`, RP registration specs, LoTE/trusted-list
  sources, and EBW Proposal/Annex?

## Provisional Decision Criterion

An improved architecture should be judged by whether it can answer a new,
plausible EUBW question without adding a question-specific intent first.

Minimum acceptance signal:

- It retrieves relevant claim clusters from the corpus.
- It marks open legal/technical issues explicitly.
- It separates binding law, proposals, official non-binding material, and
  technical/project artifacts.
- It produces a reviewable ledger or equivalent artifact surface.
- It rejects broad fallback answers for EUBW-shaped questions.
