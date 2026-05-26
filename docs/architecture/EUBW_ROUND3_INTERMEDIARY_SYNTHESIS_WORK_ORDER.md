# EUBW-Researcher Round-3 Intermediary Synthesis Work Order

Date: 2026-05-21

## Purpose

This is a handover brief for a fresh Codex instance. Round 3 of the blind
source-holdout showed that EUBW-Researcher still underperforms Legacy-EUBW on
questions that require role separation, user-facing interpretation, and
source-role-safe synthesis.

The immediate trigger was the question:

> Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche
> Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben,
> und wie sollte die Wallet Relying Party, Intermediaer, Zweck und
> Datenschutzinformationen auseinanderhalten?

The fix should be generalized. Do not build a one-off
`rp_intermediary_disclosure` template. The target is a reusable path for
questions that ask:

- which actors must be separated,
- which registry/certificate/request/user-display fields matter,
- which purpose or policy limits apply,
- where legal norms, technical specifications, and interpretation differ.

## Round-3 Diagnosis

Round-3 artifacts:

- `artifacts/tmp/blind_source_holdout_2026-05-20/round-3-rp-intermediary-disclosure/researcher/final_answer.txt`
- `artifacts/tmp/blind_source_holdout_2026-05-20/round-3-rp-intermediary-disclosure/researcher/reading_plan.json`
- `artifacts/tmp/blind_source_holdout_2026-05-20/round-3-rp-intermediary-disclosure/researcher/evidence_synthesis_matrix.json`
- `artifacts/tmp/blind_source_holdout_2026-05-20/round-3-rp-intermediary-disclosure/researcher/knowledge_retrieval_diagnostics.json`
- `docs/research/2026-05-20_blind_source_holdout_eubw_vs_researcher.md`

Blind-review result:

- System A = EUBW-Researcher.
- System B = Legacy-EUBW.
- Both anonymized answers received a hard error because the Answer-Agent
  omitted concrete source anchors in `answer_for_review`.
- Ignoring the hard-error rule, Legacy-EUBW scored higher: both reviewers gave
  Researcher 6/15 and Legacy 9/15.
- The round is diagnostically useful, but not a clean win/loss point.

Important nuance:

The common hard error was partly a protocol problem: both Answer-Agents
produced source-less review prose. But Legacy still scored better because its
answer surface and retrieved material made the actor/purpose/display model
easier to reconstruct.

## Root Causes

### 1. Researcher opened relevant sources, but selected weak passages

`reading_plan.json` included relevant families:

- `ec_ts05_rp_registration_api`
- `ec_ts06_rp_information_set`
- `eudi_discussion_topic_x_rp_registration`
- `celex_32025R0848_fulltext_en`
- `eudi_arf_main_markdown`

However, the opened passages and synthesis rows were not the best answer
building blocks. The first Researcher Kurzantwort used:

- Article 1 subject/scope of CIR 2025/848,
- a TS05 note about EUID / national business register identifiers,
- TS05 Registry API write-method access control.

Those are source-valid, but they do not answer the question's core facets:

- intermediary as technical requester,
- intermediated Wallet-Relying Party as end party,
- intended use / purpose,
- requested attributes,
- privacy policy / DPA or complaint information,
- user display and verification of the intermediary relationship.

### 2. Facet coverage is not driving passage selection

The diagnostics contained useful terms such as `intermediaer`,
`nutzeranzeige`, `zweck`, and `datenschutzinformationen`, but the answer
surface was dominated by generic registration material.

The system currently treats opened evidence and verified claims as broadly
useful once they are source-valid. It does not enforce that the first answer
section covers the requested facets.

### 3. Evidence-synthesis records are still too snippet-like

`evidence_synthesis_matrix.json` contained rows such as:

- a TS05 note about redundant registration numbers,
- a generic registry API write-method statement,
- a raw references-list fragment,
- a broad `RPRC contains attributes` fragment.

The matrix did not reliably turn opened passages into answer-ready propositions
such as:

- "The intermediary authenticates to the Wallet Unit with its own access
  certificate."
- "The request/user display must still identify the intermediated Relying
  Party."
- "The intended use and requested attributes belong to the registered
  Wallet-Relying Party service."
- "If registration-certificate data is missing, the Wallet Unit should query
  the relevant registrar."
- "DPA/contact/privacy-policy treatment is partly specified and partly an open
  issue in TS08/TS05 material."

### 4. The vNext renderer over-trusts source hierarchy

The renderer prefers high-rank or confirmed evidence, but this can promote
generic legal scope statements over more specific technical/context evidence.
For this question, the strongest user answer depends on combining:

- binding RP-registration law,
- TS05/TS06 data model and information-set details,
- ARF intermediary interaction flow,
- DPA/complaints/open-issue material where applicable.

Source hierarchy is necessary, but not sufficient. The answer needs
facet-specific synthesis.

### 5. Automated review accepted a weak answer surface

`manual_review_report.md` accepted Round 3 even though the Kurzantwort was not
directly reusable and did not answer the question's role/purpose/privacy
boundary.

The `answer_usability_surface` check currently catches raw template leakage
better than semantic non-answering. It should fail if a product answer lacks
the question's distinctive facets.

### 6. Legacy performed better for structural reasons

The Legacy run was also imperfect, but it exposed better reconstruction
material:

- more direct claim IDs and citations in the query output,
- source-diverse retrieval over 32 primary matches,
- chunk evidence that included the specific ARF intermediary display/registrar
  passage,
- explicit RPAC/RPRC claims tying authentication to intended use.

This did not make Legacy's final review prose traceable, but it helped the
Answer-Agent produce a clearer conceptual answer.

## Required Work

### Phase 0: Fix the holdout answer protocol

This is not a runtime-code fix, but it is necessary before Round 4.

Update future Answer-Agent prompts so `answer_for_review` must include concise
source anchors without repo paths:

- source ID,
- locator or section/article/page,
- source-role qualifier when relevant.

Example acceptable format:

`(SRC-W-TEC-04, ARF 6.6.5; SRC-W-TEC-30, TS05 WalletRelyingParty.usesIntermediary)`

Do not include:

- repo names,
- file paths,
- artifact names,
- expected review-only source anchors.

Acceptance:

- Reviewers can score Traceability above 0 when the answer is source-grounded.
- Redaction remains minimal because no repo path is present.

### Phase 1: Add a facet model for role-boundary questions

Introduce a small deterministic facet extraction layer for broad domain
questions. It should not be a hardcoded intent. It should classify question
facets such as:

- `actor_boundary`
- `technical_requester`
- `end_relying_party`
- `registry_information`
- `user_display`
- `purpose_or_intended_use`
- `requested_attributes`
- `privacy_policy_or_dpa`
- `certificate_or_trust_anchor`
- `open_issue_or_member_state_choice`

Likely touchpoints:

- `src/eubw_researcher/knowledge/reading.py`
- `src/eubw_researcher/retrieval/*`
- `src/eubw_researcher/answering/composer.py`
- model types if a new artifact is useful.

The facet output should be inspectable in an artifact, for example
`question_facets.json` or as a section in `knowledge_retrieval_diagnostics.json`.

Acceptance:

- For the Round-3 question, detected facets include at least:
  `actor_boundary`, `registry_information`, `user_display`,
  `purpose_or_intended_use`, `requested_attributes`,
  `privacy_policy_or_dpa`.
- The facet model is reusable for non-intermediary role-boundary questions.

### Phase 2: Use facet coverage in retrieval and reading-plan selection

When selecting passages to open, avoid spending the answer budget on generic
registration scope text if facet-specific passages exist.

Required behavior:

- Preserve source hierarchy, but require source/facet diversity.
- Boost passages where distinctive terms co-occur:
  `intermediary` + `user/display/request`,
  `intermediary` + `registration certificate`,
  `intended use` + `attributes`,
  `privacy policy` / `DPA` + `Wallet-Relying Party`.
- Prefer passage windows around facet terms over document-title or references
  snippets.
- Include adjacent context only after at least one passage for each central
  facet is opened, if available.

Acceptance:

- For the Round-3 question, `opened_passages.json` includes ARF intermediary
  interaction/display material and TS05/TS06 intermediary/intended-use material.
- Generic Article 1 / API-write-method / EUID-note passages may remain as
  background but do not occupy the first answer slots.

### Phase 3: Make synthesis rows facet-answer-ready

Extend `EvidenceSynthesisMatrix` generation so each record can carry:

- `answer_role`,
- source IDs and locators,
- `facet_tags`,
- statement quality flags such as `snippet_like`, `references_only`,
  `definition_only`, `answer_ready`.

Improve statement extraction:

- reject references-list fragments for user-facing synthesis,
- reject title-only or table-note fragments unless the question asks for them,
- prefer sentence windows with central facet terms,
- split long snippets into one proposition per row,
- keep source-role caveats separate from the statement.

Acceptance:

- The first answerable Round-3 synthesis rows should resemble:
  - intermediary authenticates / acts technically,
  - end Wallet-Relying Party remains visible,
  - intended use binds purpose and requested attributes,
  - privacy/contact/DPA information belongs to the relevant RP/purpose, with
    open-issue caveat where the source says so.
- No first-section statement starts with references-list, Article title, or
  unrelated table note.

### Phase 4: Render by facets before raw evidence status

Update the vNext composer so the user-facing answer follows the question's
facets before rendering ledger details.

For role-boundary questions, default sections should be:

1. `Kurzantwort`
2. `Registrierung / Zertifikate`
3. `Nutzeranzeige / Request-Kontext`
4. `Zweck, Attribute und Datenschutz`
5. `Grenzen / offene Punkte`
6. `Pruefdetails`

This should be driven by facets and synthesis records, not by a
question-specific template.

Acceptance:

- The Round-3 `final_answer.txt` starts with a short German answer explaining
  the separation of technical requester, end Wallet-Relying Party, intended
  use, requested attributes, and privacy information.
- Each central paragraph has at least one source ID and locator.
- `Pruefdetails` remains available after the usable answer.

### Phase 5: Strengthen review gates for semantic answer coverage

Add review checks that fail or mark `needs_follow_up` when:

- a `Kurzantwort` exists but does not contain the distinctive facets,
- the first user-facing section is dominated by generic registration or legal
  scope text,
- evidence rows marked `background` or `definition_only` drive the main answer,
- no source anchor appears in the user-facing answer before `Pruefdetails`,
- `manual_review_report.md` says `accept` while the answer is not reusable
  without raw artifact reconstruction.

Acceptance:

- The current Round-3 Researcher `final_answer.txt` would not receive final
  `accept`.
- A corrected Round-3 output with facet coverage and anchors can pass.

### Phase 6: Add regression tests

Add focused tests before or with implementation.

Suggested tests:

1. `test_role_boundary_facets_detect_intermediary_question`
   - Input: Round-3 question.
   - Expected facets: actor boundary, registry, user display, intended use,
     requested attributes, privacy/DPA.

2. `test_reading_plan_prefers_intermediary_display_passage`
   - Input: fixture catalog with generic registration scope passage and
     specific intermediary display passage.
   - Expected: specific passage is opened before generic scope.

3. `test_synthesis_matrix_rejects_references_and_table_notes_as_core_answer`
   - Input: records similar to Round-3 snippets.
   - Expected: not rendered in `Kurzantwort` as core claims.

4. `test_vnext_renderer_rp_intermediary_product_answer`
   - Input: synthesis rows for intermediary, end RP, intended use, attributes,
     privacy policy / DPA.
   - Expected: German answer sections, source anchors, no raw snippet opening.

5. `test_manual_review_rejects_round3_semantic_non_answer`
   - Input: current Round-3 style `final_answer.txt`.
   - Expected: usefulness or answer coverage fails.

6. Existing suites remain green:
   - `python3 scripts/run_tests.py`
   - `python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml`
   - `python3 scripts/run_real_question_pack.py --all --pack configs/legacy_gold_holdout_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml`

## Validation Smoke

After implementation, rerun:

```bash
python3 scripts/answer_question.py "Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck und Datenschutzinformationen auseinanderhalten?" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/renderer_vnext_rp_intermediary_smoke
```

Expected smoke outcome:

- `final_answer.txt` begins with a reusable German short answer.
- The first answer section includes source IDs/locators before `Pruefdetails`.
- The answer mentions at least:
  - intermediary as technical requester / own access certificate,
  - intermediated Wallet-Relying Party as end party,
  - intended use / purpose,
  - requested attributes,
  - privacy policy / DPA or complaint-contact handling with caveat.
- `manual_review_report.md` is not `accept` unless these facets are present.

## Non-Goals

- Do not copy Legacy prose into Researcher.
- Do not add a narrow hardcoded `rp_intermediary_disclosure` intent as the main
  fix.
- Do not weaken strict verification, source-role hierarchy, or ledger artifacts.
- Do not hide proposal/specification status for fluency.
- Do not remove detailed `Pruefdetails`; move them behind a usable answer.

## Handover Notes

The problem is not simply missing retrieval. Researcher had enough source
families to be useful, but did not turn them into the right answer surface.
Legacy's advantage came from better claim/chunk affordances and a stronger
role/purpose reconstruction path. The implementation should therefore combine:

- facet-aware evidence navigation,
- answer-ready synthesis records,
- source-anchored product rendering,
- semantic review gates.

If only the prompt for the Answer-Agent is fixed, future blind reviews will be
more traceable, but the underlying vNext answer quality gap will remain.
