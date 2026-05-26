# EUBW-Researcher vNext Renderer Fix Work Order

Date: 2026-05-21

## Purpose

This is a handover brief for a fresh Codex instance. The retrieval-parity work improved source recall, but the vNext renderer still does not consistently produce a usable fachliche Antwort. The next implementation should fix answer composition without weakening ledger, verification, source-governance, or traceability gates.

## Trigger

After the retrieval fix, the Trust-Mark smoke run at:

`artifacts/tmp/retrieval_parity_trust_mark_smoke`

showed that retrieval now opens the right source:

- `reading_plan.json` includes `ec_ts01_wallet_trust_mark`
- opened locator includes `Specification of EUDI Wallet Trust Mark > 1 Introduction and Overview > 1.2 Scope for the Trust Mark Requirements and Design`
- `knowledge_retrieval_diagnostics.json` contains useful query expansion and source-candidate diagnostics

But `final_answer.txt` is still weak:

- It starts with English template text like `Passage supports: ...` although the user question is German.
- It mixes a useful Trust-Mark bullet with less relevant secondary evidence.
- It then renders a long `Pruefdetails` section dominated by generic WRP / access-certificate claims.
- It exposes internal claim-verification mechanics before giving the user a polished answer.
- `manual_review_report.md` still accepts the run even though the rendered answer is not directly reusable.

This means retrieval is no longer the only blocker. The renderer now needs to convert opened evidence into a product-oriented answer while keeping traceability available after the answer.

## Goal

Build a product-oriented `vnext` synthesis renderer that:

- answers the actual question first,
- uses the user's language where practical,
- cites concrete source IDs and locators inline or immediately after claims,
- separates governing law, technical specs, interpretation, and open issues,
- moves raw ledger / verification detail behind the usable answer,
- avoids snippet dumps and internal phrases such as `Passage supports`,
- does not rely on one-off benchmark answer templates.

## Non-Goals

- Do not hardcode a `trust_mark_boundary` renderer.
- Do not remove detailed artifacts from the bundle.
- Do not downgrade source-role or verification safeguards.
- Do not turn the final answer into Legacy-style free prose without traceability.
- Do not hide uncertainty or source-role limitations for fluency.

## Current Architecture Notes

Relevant files likely include:

- `src/eubw_researcher/answering/composer.py`
- `src/eubw_researcher/knowledge/reading.py`
- `src/eubw_researcher/evaluation/review.py`
- `src/eubw_researcher/evaluation/runner.py`
- `tests/unit/test_answering_composer.py`
- `tests/unit/test_evaluation_runner.py`
- `tests/unit/test_agentic_knowledge_migration.py`

Current vNext composition appears to use:

- `_product_summary_lines(...)`
- `_render_bullets_vnext(...)`
- `EvidenceSynthesisMatrix`
- approved ledger entries / bullets

The current implementation has many question-specific summary branches. Some are useful as transitional support, but the target should become more generic: derive answer sections from evidence roles and question facets, not from a growing list of hand-authored benchmark patterns.

## Required Work

### 1. Add a generic evidence-to-answer synthesis layer

Create a renderer step that groups opened/synthesized evidence into answer roles:

- `core_answer`
- `scope_boundary`
- `normative_basis`
- `technical_spec_context`
- `interpretation`
- `open_issue`
- `audit_or_trace_detail`
- `background`

This can be deterministic at first. It should use:

- `EvidenceSynthesisRecord.answer_role`
- source kind / source role / document status
- locators
- question terms and expanded terms
- high-confidence source candidates from `knowledge_retrieval_diagnostics`
- verification status

Acceptance:

- The first section contains a direct German answer, not raw snippet phrasing.
- A user can read the first 5-10 lines without understanding ledger internals.

### 2. Make `EvidenceSynthesisMatrix.statement` answer-ready

Current statements can be truncated raw snippets. Improve them so they are short, citable propositions.

Minimum deterministic approach:

- strip boilerplate source titles,
- keep full sentence when possible,
- prefer sentence windows around distinctive query terms,
- add source-role caveat separately rather than inside statement,
- classify statement role using simple heuristics.

Acceptance:

- No `Passage supports:` prefix in `final_answer.txt`.
- No arbitrary mid-word snippet starts as the primary answer text.
- Statements carry `source_ids`, `chunk_ids`, `locators`, and caveats.

### 3. Render `Kurzantwort` before `Pruefdetails`

The vNext answer should default to:

1. `Kurzantwort`
2. `Belege / Quellenrolle`
3. `Einordnung / Grenzen`
4. `Offene Punkte`
5. `Pruefdetails` only after the usable answer

For highly technical protocol questions, section names may differ, but the principle remains: useful answer first, artifact detail second.

Acceptance:

- For the Trust-Mark question, the first section says essentially:
  - remove visible trust mark when certification/recognition basis no longer applies and cancellation occurs;
  - scope is the Wallet solution / visible EUDI Wallet Trust Mark;
  - it is not a quality mark for Relying Party services or Attestation Provider qualifications.
- It includes `ec_ts01_wallet_trust_mark` and a Section 1.2 locator.

### 4. Demote off-topic verified claims

A verified claim can be source-valid but answer-irrelevant. The renderer must not let generic high-rank claims dominate the final answer when opened evidence provides a more specific answer.

Use relevance signals:

- overlap with distinctive question terms / expansions,
- source-candidate confidence,
- opened-passage role,
- evidence synthesis role,
- whether claim source appears in the top source candidates,
- whether claim addresses the requested actor/action boundary.

Acceptance:

- In the Trust-Mark smoke, WRP access-certificate claims may appear in `Pruefdetails` if needed, but they must not define the answer.
- The answer must not imply the question is primarily about WRP access certificates.

### 5. Improve review gates for answer usability

`manual_review_report.md` should not accept answers that are technically source-bound but not reusable.

Add or tighten checks for:

- final answer language and template leakage,
- `Passage supports` / raw snippet dump markers,
- distinctive source candidate absent from user-facing answer,
- answer dominated by off-topic verified claims,
- `Kurzantwort` missing or too artifact-like.

Acceptance:

- A renderer output that starts with raw snippet/template prose fails usefulness or needs follow-up.
- A Trust-Mark output without user-facing `ec_ts01_wallet_trust_mark` evidence fails or needs follow-up.

### 6. Preserve artifact detail

The fix should not delete ledger detail. Instead:

- keep `approved_ledger.json`, `claim_verification.json`, `evidence_synthesis_matrix.json`, `knowledge_retrieval_diagnostics.json`,
- render concise traceability in `final_answer.txt`,
- leave deep claim verification in `Pruefdetails` or separate artifacts.

## Regression Tests To Add

1. `vnext_renderer_trust_mark_product_answer`
   - Input: Trust-Mark question with synthesis matrix containing `ec_ts01_wallet_trust_mark`.
   - Expected: German `Kurzantwort`, no `Passage supports`, source locator visible, RP/AP scope boundary present.

2. `vnext_renderer_demotes_off_topic_verified_claims`
   - Input: one specific medium-rank source plus several generic high-rank WRP claims.
   - Expected: specific source drives the answer; generic claims appear only as background or details.

3. `manual_review_rejects_template_or_snippet_dump`
   - Input: final answer beginning with `Passage supports`.
   - Expected: review is not final `accept`.

4. `evidence_synthesis_matrix_statement_is_answer_ready`
   - Ensure generated statements are compact sentence-like propositions with locators and caveats.

5. Existing packs:
   - `configs/legacy_parity_question_pack.yaml`
   - `configs/legacy_gold_holdout_question_pack.yaml`
   must not regress.

## Validation Commands

```bash
python3 scripts/run_tests.py
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_gold_holdout_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/answer_question.py "Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/renderer_vnext_trust_mark_smoke
```

Expected smoke outcome:

- `final_answer.txt` starts with a reusable German short answer.
- The Trust-Mark Section 1.2 source is cited in the user-facing answer.
- Generic WRP access-certificate claims do not dominate the answer.
- No `Passage supports` text appears.
- `manual_review_report.md` accepts only if the answer is actually reusable.

## Definition Of Done

The task is complete when:

- vNext final answers are usable as Fachantworten without reading raw artifacts first;
- source IDs and locators remain visible;
- source-role caveats remain explicit;
- off-topic verified claims are demoted;
- previous retrieval-smoke improvement is preserved;
- legacy parity and gold holdout tests stay green.
