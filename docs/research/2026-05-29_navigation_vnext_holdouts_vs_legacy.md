# Navigation vNext Holdouts vs. Legacy EUBW

Datum: 2026-05-29

## Ziel

Dieser Checkpoint stabilisiert die Navigation-First-Migration nach den Review-Findings zu Trust-Mark-Rendering, Topic-Drift, WUA/Issuer-Fragen und protokollspezifischen Security-Parametern.

Er bewertet EUBW-Researcher vNext gegen das Legacy-Repo `/mnt/c/Users/Admin/PycharmProjects/EUBW` mit vier neuen, nicht benchmark-spezifischen Holdout-Fragen aus unterschiedlichen Corpus-Bereichen:

- EBW/EUBW und Behoerdenkanal-Grenzen
- eIDAS/Implementing-Act-Zertifizierung
- technische WUA/Issuer-Spezifikation
- OpenID4VP `state`/`nonce`

## Geaenderte Dateien

- `src/eubw_researcher/answering/composer.py`
- `src/eubw_researcher/evaluation/review.py`
- `src/eubw_researcher/evaluation/runner.py`
- `src/eubw_researcher/knowledge/query_expansion.py`
- `src/eubw_researcher/knowledge/question_facets.py`
- `src/eubw_researcher/knowledge/reading.py`
- `src/eubw_researcher/knowledge/service.py`
- `tests/unit/test_agentic_knowledge_migration.py`
- `tests/unit/test_answering_composer.py`
- `tests/unit/test_evaluation_runner.py`

## Implementierte Stabilisierung

- Trust-Mark-Fragen werden nach Meaning, Removal und RP/AP-Scope getrennt behandelt. Generische Meaning-Fragen rendern keine Removal-Prosa mehr.
- Generische Trust-Mark-Kurzantworten bevorzugen nicht mehr `definition_only`-Schemazeilen als Hauptbeleg. `celex_32024R2981_fulltext_en` kann die Meaning-Aussage tragen; `ec_ts01_wallet_trust_mark` bleibt als sichtbarer technischer Kontextanker vor `Pruefdetails:` erhalten.
- Harte Topic-Drift-Konzepte werden nicht mehr aus breiten Query-Expansion-Termen abgeleitet, sondern aus Originalfrage und expliziten Question-Facets.
- `authentifizierung` wird nicht mehr zu `pseudonymous authentication` expandiert.
- WUA/Issuer-Fragen erhalten generalisierbare Query-, Alias-, Reading-Compaction- und Composer-Unterstuetzung fuer Wallet Unit Attestation, Issuer Credential Metadata, `proof_types_supported`, Key Attestation, `x5c`, Trust Anchor und `c_nonce`.
- OpenID4VP `state`/`nonce` wird als eigenes `protocol_security_parameter`-Facet erkannt und auf OpenIDVP/RFC6749-Kontexte begrenzt, damit Member-State-Treffer keine falsche Actor-Boundary-Frage ausloesen.
- Dynamische Evidence-Eintraege ohne praezisen Locator werden nicht mehr in user-facing Kurzantworten gerendert.
- Das Web-Metadata-Gate wertet nur erfolgreiche erlaubte Fetches aus; fehlgeschlagene oder mehrdeutige Fetch-Versuche blockieren nicht mehr als angeblich reviewfaehige Web-Evidenz.

Keine Default-Umschaltung und keine Codex-Skills wurden implementiert.

## Holdout-Vergleich

Researcher-vNext-Artefakte:

- `artifacts/tmp/navigation_holdouts_20260529_v10/researcher/h1_ebw_authority_channels`
- `artifacts/tmp/navigation_holdouts_20260529_v10/researcher/h2_wallet_cert_suspension`
- `artifacts/tmp/navigation_holdouts_20260529_v10/researcher/h3_wallet_unit_attestation_issuer_check`
- `artifacts/tmp/navigation_holdouts_20260529_v10/researcher/h4_openidvp_state_nonce`

Legacy-Antworten:

- `artifacts/tmp/navigation_holdouts_20260529_v8/legacy/h1_ebw_authority_channels.txt`
- `artifacts/tmp/navigation_holdouts_20260529_v8/legacy/h2_wallet_cert_suspension.txt`
- `artifacts/tmp/navigation_holdouts_20260529_v8/legacy/h3_wallet_unit_attestation_issuer_check.txt`
- `artifacts/tmp/navigation_holdouts_20260529_v8/legacy/h4_openidvp_state_nonce.txt`

| Holdout | Ergebnis EUBW-Researcher vNext | Ergebnis Legacy-EUBW | Bewertung |
| --- | --- | --- | --- |
| H1 EBW/Behoerdenkanaele | Review `accept`; findet EBW-Vorschlag und grenzt Wallet-Nutzung gegen bestehende Austausch-/Kommunikationskanaele ab. | Liefert breitere EBW/WUA- und Identitaetsclaims, trifft die Kanalgrenze weniger klar. | Researcher besser; Restschwaeche: `Pruefdetails` enthalten noch breitere eIDAS-/Identity-Kontextzeilen. |
| H2 Wallet-Zertifizierung | Review `accept`; ankert Zertifikat, Aussetzung/Entzug und Funktionsgrenze an CELEX 2024/2981 und 2024/1183. | Bleibt staerker bei allgemeinen Wallet-Obligationen und trifft den Implementing-Act weniger praezise. | Researcher besser; Restschwaeche: Quellenrollen-Details zeigen noch ARF-Kontext neben dem CELEX-Hauptanker. |
| H3 WUA/Issuer-Pruefung | Review `accept`; Source Discovery, Reading Plan und Matrix oeffnen TS03-WUA-Evidenz und synthetisieren Issuer-Pruefungen statt rohe englische Spezifikationsfragmente zu rendern. | Findet OID4VCI-/Wallet-Attestation-Rollen, aber nicht die TS03-WUA-Issuer-Verantwortung mit gleicher Abgrenzung. | Researcher besser nach Fix. |
| H4 OpenID4VP `state`/`nonce` | Review `accept`; rendert eine kompakte deutsche CSRF-/Replay-/Response-Zuordnungsantwort mit OpenIDVP/RFC6749-Ankern. | Findet relevante OpenIDVP-Sicherheitsclaims. | Researcher mindestens vergleichbar und traceability-staerker. |

Alle vier Researcher-Holdouts enden mit `Final accept / reject: accept`.

## Navigation-Bundle-Qualitaet

Gegenueber Legacy-Prosa ist die vNext-Qualitaet in diesem Checkpoint besser reviewbar, weil die Antwort nicht allein die Bewertungsflaeche ist. Fuer die Researcher-Runs liegen mindestens diese Bundle-Flaechen vor:

- `reading_plan.json`
- `opened_passages.json`
- `evidence_synthesis_matrix.json`
- `claim_verification.json`
- `source_hierarchy_report.json`
- `manual_review_report.md`

Damit sind Source Discovery, geplantes Oeffnen, Passage-Auswahl, Matrix-Synthese, Claim-Verifikation, Source-Governance und Review-Urteil getrennt pruefbar. Legacy liefert fuer die verglichenen Runs keine gleichwertige Navigations- und Governance-Bundle-Struktur.

## Ausgefuehrte Validierung

Fokussierte Regressionen:

```bash
env PYTHONPATH=src python3 -m unittest \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_wua_issuer_question_compacts_transport_and_scope_rows \
  tests.unit.test_answering_composer.ComposerTests.test_vnext_wua_pid_question_uses_matrix_instead_of_student_binding_template \
  tests.unit.test_answering_composer.ComposerTests.test_vnext_renderer_generic_trust_mark_keeps_schema_context_secondary \
  tests.unit.test_answering_composer.ComposerTests.test_vnext_openidvp_state_nonce_answer_uses_protocol_parameter_records \
  tests.unit.test_answering_composer.ComposerTests.test_vnext_dynamic_entries_without_precise_locator_are_not_rendered \
  tests.unit.test_evaluation_runner.EvaluationRunnerTests.test_manual_review_accepts_secondary_context_anchor_for_top_source_candidate \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_openidvp_state_nonce_reading_plan_prefers_openidvp_source \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_protocol_state_nonce_question_does_not_trigger_actor_boundary_facet \
  tests.unit.test_evaluation_runner.EvaluationRunnerTests.test_central_concepts_include_explicit_protocol_security_parameters
```

Ergebnis: 9 Tests OK.

Standardvalidierung nach Abschnitt 11:

```bash
python3 scripts/build_real_corpus_catalog.py
python3 scripts/build_source_crosswalk.py
python3 scripts/run_tests.py
python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_legacy_parity.py
```

Ergebnisse:

- `python3 scripts/run_tests.py`: 412 Tests OK
- `python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`: alle 6 Szenarien PASS
- `python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml`: exit 0, Run `artifacts/real_question_pack_runs/20260529T141624Z`
- `python3 scripts/run_legacy_parity.py`: Overall hard gate `true`, 20/20 Legacy-Parity-Fragen hard-gate true, Locator Coverage 1.00, Traceability true
- Generic Trust-Mark-Smoke `/tmp/eubw_review_trust_mark_generic_final_check`: `Final accept / reject: accept`
- H1/H2/H3/H4-Holdouts in `artifacts/tmp/navigation_holdouts_20260529_v10/researcher`: jeweils `Final accept / reject: accept`

## Offene Restschwaechen

- H1 ist akzeptiert und besser als Legacy, aber die `Pruefdetails` enthalten noch einige breite eIDAS-/Identity-Kontextzeilen neben der eigentlichen EBW-Kanalgrenze.
- H2 ist akzeptiert und besser als Legacy, aber die Quellenrollen-Details koennen ARF-Kontext neben dem CELEX-Hauptanker anzeigen.
- H3 meldet in der manuellen Review `Discovery / gap-handling verdict: not_exercised`, weil kein Web-Gap-Rescue benoetigt wurde; das ist kein Blocker fuer den akzeptierten Lauf.

Keine offenen Blocker fuer diesen Checkpoint.
