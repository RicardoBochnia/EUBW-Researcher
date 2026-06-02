# Navigation Relevance Gates Checkpoint

Datum: 2026-06-02

## Ziel und Baseline

Dieser Checkpoint baut auf Commit `804578d` auf. Er schaerft die Navigation-First-Migration so nach, dass passende Kernquellen nicht nur gefunden, sondern themenfremde Evidenz vor Reading Plan, Evidence Synthesis Matrix, Ledger, Renderer, Review und Web-Gap-Expansion konsequent ausgesondert wird.

Die vier Ausgangsfindings waren:

- H1 akzeptierte eine Identity-Matching-Durchfuehrungsverordnung als sichtbaren Quellenanker fuer die EBW-Kommunikationskanal-Grenze.
- H2 und H3 enthielten in Detailflaechen deutliches Topic Drift.
- `high-rank` und `binding` wurden im Renderer sprachlich vermischt.
- Web-Gap-Queries konnten themenfremde Snippet-Texte weiterreichen.

Keine Runtime-Config wurde umgestellt. Es gibt keine Default-Umschaltung und keine Codex-Skills.

## Checkpoints

### Checkpoint 1: Relevanzsubstrat

Geaenderte Dateien:

- `src/eubw_researcher/knowledge/relevance.py`
- `src/eubw_researcher/knowledge/query_expansion.py`
- `src/eubw_researcher/knowledge/service.py`
- `src/eubw_researcher/knowledge/dynamic.py`
- `src/eubw_researcher/knowledge/reading.py`
- `src/eubw_researcher/evidence/ledger.py`
- `src/eubw_researcher/pipeline.py`
- `src/eubw_researcher/models/types.py`

Umgesetzt:

- Gemeinsame Relevanzentscheidungen filtern Source Candidates, Cluster Records, dynamische Targets, Reading Plan, geoeffnete Passagen, Matrixzeilen und Ledger-Eintraege.
- Profile grenzen Trust Mark, Wallet-Zertifizierung, OpenID4VP-Security-Parameter, WUA/Issuer, Portabilitaet, Pseudonyme, Identity Matching, Trusted Lists, TS11, Delegationsketten, EBW-Entwurfsstatus, EBW-Behoerdenkanaele, Audit Logs und Authentic-Source-Prioritaet ab.
- Profilfreie Evidenz benoetigt Originalfragen-Overlap, eine stabile Mehrwort-Kollokation wie `transaction log` oder `authentic source`, oder mindestens zwei nicht-triviale semantische Treffer.
- Kleine oder degradierte Kataloge bleiben navigierbar, wenn kein profilkompatibler Source-Eintrag existiert. Dieser Sonderpfad wird als `catalog_has_no_profile_compatible_source_relevance_fallback` im Trace und in den Sufficiency Signals sichtbar markiert.
- Web-Gap-Queries werden nur noch aus Originalfrage, expliziten Facets, echter Gap-Beschreibung und sicheren Target Terms aufgebaut. Retrieval-Snippets werden nicht wiederverwendet.

Ausgefuehrte fokussierte Tests:

```bash
env PYTHONPATH=src python3 -m unittest -v \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_knowledge_service_returns_evidence_only_clusters_with_navigation \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_reading_loop_builds_plan_opened_passages_and_synthesis_matrix \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_audit_log_profile_rejects_credential_false_friend \
  tests.unit.test_agentic_knowledge_migration.AgenticKnowledgeMigrationTests.test_authentic_source_priority_profile_rejects_registration_false_friend
```

Ergebnis: 4 Tests OK.

Offene Blocker: keine.

### Checkpoint 2: Source Semantics und PDF-Locators

Geaenderte Dateien:

- `src/eubw_researcher/answering/composer.py`
- `src/eubw_researcher/evaluation/review.py`
- `src/eubw_researcher/corpus/normalize.py`
- `src/eubw_researcher/corpus/ingest.py`
- `src/eubw_researcher/corpus/runtime.py`

Umgesetzt:

- Renderer und Review trennen `Rang`, `Bindungswirkung` und `Dokumentstatus`.
- Technische Standards werden als `technischer_standard_keine_eu_rechtsnorm` dargestellt, nicht als bindende EU-Rechtsnorm.
- Proposal-Quellen werden als `entwurfsstand_nicht_bindend` dargestellt.
- PDF-Normalisierung erhaelt Seitenanker. Proposal und Annex werden als seitensegmentierte, `anchor_grounded` Chunks aufgenommen.
- Die Cache-Schema-Version wurde auf `normalized_bundle.v3` erhoeht, damit alte PDF-Chunks ohne Seitenanker nicht weiterverwendet werden.
- Der vNext-Renderer verwirft abgeschnittene PDF-Seitenkopf-Fragmente und faellt auf eine sichere Quellenanker-Aussage zurueck.

Cache-Pruefung:

```text
ebw_proposal_com_2025_0838 chunks=93 locator=Page 1 quality=anchor_grounded
ebw_annex_com_2025_0838 chunks=8 locator=Page 1 quality=anchor_grounded
```

Offene Blocker: keine.

### Checkpoint 3: Adversariale Regressionen

Geaenderte Dateien:

- `tests/unit/test_agentic_knowledge_migration.py`
- `tests/unit/test_answering_composer.py`
- `tests/unit/test_archive_corpus.py`
- `tests/unit/test_evaluation_runner.py`

Abgesichert sind unter anderem:

- Generic Trust-Mark gegen Removal-Fehltrigger und `definition_only`-Hauptanker
- Generic Authentication gegen Pseudonym-Expansion
- Identity Matching gegen WUA-False-Friend
- TS11 gegen RP-Registration-False-Friend
- Delegationsketten gegen OpenID-Scope-False-Friend
- EBW-Entwurfsstatus gegen allgemeine eIDAS-False-Friends
- Audit Logs gegen Credential-Acknowledgement-False-Friend
- Authentic-Source-Prioritaet gegen OAuth-Registration-Metadaten
- Web-Gap-Expansion gegen Retrieval-Snippet-Reuse
- technische Standards gegen falsche Binding-Sprache
- PDF-Seitenanker und PDF-Seitenkopf-Fallback

Fokussierter Lauf:

```text
8 Tests OK
```

Offene Blocker: keine.

## Holdout-Ergebnisse

Frische CLI-Artefakte liegen unter `/tmp/eubw_relevance_holdouts_20260602_final`.

| Holdout | Review | Reading Plan und Matrix |
| --- | --- | --- |
| H1 EBW/Behoerdenkanaele | `accept` | nur `ebw_proposal_com_2025_0838`, `ebw_annex_com_2025_0838` |
| H2 Wallet-Zertifizierung | `accept` | CELEX 2024/2981, CELEX 2024/1183, CELEX 2025/849, TS01 |
| H3 WUA/Issuer-Pruefung | `accept` | nur TS03 und ARF |
| H4 OpenID4VP `state`/`nonce` | `accept` | nur OpenID4VP, RFC 6749 und ARF |
| N1 Identity Matching | `accept` | CELEX 2025/846 und CELEX 2024/1183 |
| N2 Trusted Lists | `accept` | nur CELEX 2025/2164 |
| N3 Portabilitaet | `accept` | nur TS03 und TS10 |
| N4 TS11-Katalog | `accept` | nur TS11 |

Fuer alle acht Holdouts gilt:

- kein themenfremder Web-Gap-Query;
- kein degradierter Katalog-Fallback;
- `Final accept / reject: accept`.

H1 hebt Proposal und Annex als Entwurfsquellen hervor. H4 zeigt technische Standards sichtbar mit `technischer_standard_keine_eu_rechtsnorm`.

## Standardvalidierung

Ausgefuehrt nach Abschnitt 11:

```bash
python3 scripts/build_real_corpus_catalog.py
python3 scripts/build_source_crosswalk.py
python3 scripts/run_tests.py
python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_legacy_parity.py
```

Ergebnisse:

- Katalogaufbau: OK
- Source-Crosswalk: 29 Eintraege, OK
- Vollstaendige Testsuite: 428 Tests OK
- `run_eval.py`: alle 6 Szenarien PASS
- Legacy-Parity-Fragenpack: exit 0, Run `artifacts/real_question_pack_runs/20260602T110833Z`
- Legacy-Parity-Gate: Overall hard gate `true`, 20/20 Fragen hard-gate true, Locator Coverage 1.00, Traceability true
- `git diff --check`: OK

Die Round-2/3/4-Navigationsszenarien und negative Kontrollen sind als Regressionstests oder reproduzierbare CLI-Holdouts abgedeckt.

## Restschulden und Rollback

- Die Relevanzprofile sind bewusst explizit und reviewbar. Neue Corpus-Bereiche koennen weitere Profile oder stabile semantische Kollokationen benoetigen.
- H2 zeigt neben dem zentralen Zertifizierungsakt weiterhin legitimen eIDAS- und TS01-Kontext. Das ist kein Topic Drift, kann aber bei kuenftiger UI-Verdichtung kompakter dargestellt werden.
- Web-Gap-Expansion wurde in diesem Holdout-Set nicht ausgeloest; der Snippet-Reuse-Negativfall ist als Unit-Test abgedeckt.

Rollback bleibt einfach: Deployment auf Baseline `804578d` zuruecksetzen oder den Checkpoint-Commit revertieren. Runtime-Configs, Legacy-Verification-Gates und Default-Verhalten wurden nicht umgeschaltet.

Keine offenen Blocker fuer diesen Checkpoint.
