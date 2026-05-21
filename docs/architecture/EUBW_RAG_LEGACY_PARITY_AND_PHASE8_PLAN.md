# EUBW-RAG Legacy-Parität Und Phase-8-Rollout

Status: Initial implementation baseline

Stand: 2026-05-11

Implementierungsstand:

- Legacy-Paritätsfragepack, Research Profiles, Composer-vNext-Runtime,
  Reading-Loop-Artefakte und Legacy-Parity-Reporter sind angelegt.
- Der normale Legacy-Paritätsfragepack läuft über
  `configs/runtime.knowledge_composer_vnext.yaml` fuer alle 20 Fragen durch.
- Der strenge `legacy_parity_report` bleibt bewusst rot, solange
  legacy-only Caveats nicht sichtbar genug erhalten bleiben. Beim letzten
  Smoke betraf das drei Caveat-Erhaltungsfälle, nicht Kernaussagen,
  Source-Role-Verletzungen, Locator-Coverage oder Artefakttraceability.

Scope: Anschlussplan zur Annäherung von EUBW-Researcher an die Antwortqualität
des Legacy-Repos `C:\Users\Admin\PycharmProjects\EUBW` und zur kontrollierten
Umsetzung von Phase 8 aus `EUBW_AGENTIC_RAG_MIGRATION_PLAN.md`.

## 1. Ausgangspunkt

Die Phasen 1-7 der agentischen RAG-Migration haben den wichtigsten
Architekturwechsel eingeleitet:

- Der Knowledge Service kann Evidence-Cluster, ausgewählte Evidenz,
  Navigationsspuren und Claim-Verifikation erzeugen.
- Der assistive Pfad kann dynamisch gefundene Evidenz in die Ledger- und
  Review-Kette einspeisen.
- Q1-Q8 plus Holdouts können ohne neue Q6-Q8-spezifische Intents laufen.
- Die neuen Artefakte machen Retrieval, Source Governance und offene Lücken
  besser prüfbar als der alte Text-only-Pfad.

Der Qualitätsvergleich am Kollegenbriefing zeigt aber: Legacy EUBW bleibt bei
der finalen Antwortqualität stärker. Der Abstand liegt nicht mehr primär im
Retrieval, sondern in der Antwortkomposition und in der Nutzung einer breiten,
vorkuratierten Claim-/Profilbasis.

Kurzdiagnose:

- Legacy EUBW ist claim-first und profilgetrieben. Es findet domänenspezifische
  Bausteine flexibel und komponiert daraus fachlich dichte Antworten.
- EUBW-Researcher ist inzwischen evidence-aware und verification-first, nutzt
  die Evidence-Artefakte aber noch zu schwach in der finalen Prosa.
- Das Ziel ist nicht, Legacy-Prosa zu kopieren, sondern Legacy-Flexibilität mit
  Researcher-Traceability zu verbinden.

## 2. Zielbild Für Diesen Anschlussplan

EUBW-Researcher soll bei neuen eIDAS-/EUBW-Fragen so arbeiten:

1. Frage zerlegen und passende Research-Profile wählen.
2. Breite Claim-, Source- und Cluster-Kandidaten finden, auch ohne
   fragefamilienspezifische Intents.
3. Relevante Passagen und Nachbarpassagen öffnen.
4. Kandidaten gegen Source Governance, Bindungsniveau, Dokumentstatus,
   Locator, Widersprüche und offene Issues verifizieren.
5. Eine Antwort schreiben, die pro Kernaussage Claim-/Source-/Locator-Belege
   und Caveats enthält.
6. Lücken sichtbar machen, statt sie mit flüssiger Prosa zu verdecken.

Phase 8 darf erst abgeschlossen werden, wenn dieser Pfad auf
Legacy-Paritätsbenchmarks besser oder mindestens gleich gut abschneidet und
weiterhin rollbackfähig bleibt.

## 3. Nicht-Ziele

- Keine Rückkehr zu einem reinen Legacy-System.
- Kein blindes Freischalten importierter Legacy-Claims.
- Keine neuen benchmark-spezifischen Intents für jedes auffällige Beispiel.
- Kein Entfernen der bestehenden spezialisierten Intents vor bestandener
  Dual-Run- und Rollback-Prüfung.
- Kein Default-Umschalten auf `runtime.knowledge_assistive.yaml`, solange die
  Antwortkomposition nicht parity-gated ist.

## 4. Workstream 0: Freeze Vor Tuning

Ziel:

- Paritäts- und Holdout-Erwartungen festlegen, bevor Research Profiles,
  Aliases, Source-Family-Regeln oder Composer-Patterns optimiert werden.

Umsetzung:

- Neues `configs/legacy_parity_question_pack.yaml` vor Workstream B-D
  erstellen.
- Pflichtkonzepte pro Frage nicht als Legacy-Wahrheit modellieren, sondern als
  `expected_concept_candidate` mit Status:
  - `source_backed_required`;
  - `source_backed_optional`;
  - `legacy_only_gap`;
  - `rejected_or_outdated`.
- Nur `source_backed_required` darf ein hartes Gate sein.
- Mindestens ein sealed Holdout-Satz wird vor Profil-/Composer-Tuning
  eingefroren.
- Freeze-Manifest erzeugen:
  - `question_pack_digest`;
  - `holdout_digest`;
  - `legacy_reference_digest`;
  - `catalog_digest`;
  - `created_at`;
  - `commit_sha`, falls verfügbar.
- Jede spätere Änderung an Aliaslisten, Profilregeln, Source-Family-Regeln oder
  Rendering-Patterns muss gegen `benchmark_specific_risk` geprüft werden.

Akzeptanz:

- Parity-Pack und sealed Holdouts existieren vor Composer-VNext-Tuning.
- Freeze-Manifest ist im Report referenzierbar.
- Kein `expected_concept_candidate` wird ohne aktuelle Source-Verification zur
  Pflichtaussage.

## 5. Workstream A: Legacy-Knowledge-Import VNext

Ziel:

- Die Stärke des Legacy-Repos als breite Claim-/Chunk-/Benchmark-Basis nutzen,
  ohne dessen Aussagen automatisch als autoritativ zu behandeln.

Umsetzung:

- `scripts/import_legacy_knowledge.py` von Fixture-Support auf repräsentative
  echte Legacy-Slices erweitern:
  - `knowledge/claims/*_claim_candidates.jsonl`;
  - `knowledge/claims/*_claims_draft.jsonl`;
  - `knowledge/chunks/chunks_a.jsonl`;
  - `knowledge/chunks/chunks_bc.jsonl`;
  - `knowledge/benchmarks/*.jsonl`;
  - optional `knowledge/answers/*.json` als Referenzantworten, nicht als
    Wahrheit.
- Importierte Claims als `candidate` oder `legacy_reference` markieren.
- Legacy-IDs (`CLM-*`, `CH-*`, `SRC-*`) erhalten und per Crosswalk auf aktuelle
  `source_id`s abbilden.
- Importberichte mit unresolved sources, source-role gaps, digest gaps und
  locator gaps erzeugen.
- Full import nicht sofort erzwingen: erst repräsentative Claim-Familien, dann
  sukzessive Erweiterung.

Akzeptanz:

- Mindestens fünf Legacy-Claim-Familien importieren ohne ungeprüfte Approval.
- Jede importierte Aussage hat Status, Source-IDs, Chunk-/Locator-Bezug oder
  einen sichtbaren Gap.
- Keine importierte Legacy-Aussage erscheint in `approved_ledger.json`, ohne
  durch `claim_verification.json` zu laufen.

## 6. Workstream B: Research Profiles Statt Spezialintents

Ziel:

- Die flexible Profilstärke des Legacy-Repos in generische, wiederverwendbare
  Such- und Denkmodi übersetzen.

Umsetzung:

- Neues `configs/research_profiles.yaml` einführen.
- Legacy-Profile aus `external_profiles.json`, `agent_tools/services/` und
  Benchmark-Erfahrungen auswerten, aber in generische Profile überführen:
  - `legal_hierarchy`;
  - `technical_specification`;
  - `rulebook_catalogue`;
  - `source_conflict`;
  - `role_boundary`;
  - `lifecycle_status`;
  - `audit_traceability`;
  - `identity_authority_separation`;
  - `open_issue_heavy`;
  - `web_gap_official_sources`.
- Query Analyzer soll ein oder mehrere Profile pro Frage wählen können.
- Profile beeinflussen Retrieval-Prioritäten, Source-Familien,
  Passage-Navigation, Higher-Authority-Suche und Gap-Checks.
- Profile dürfen keine konkreten Benchmarkfragen, Q-IDs oder
  hartcodierten Antwortfragmente enthalten.
- Profile müssen generische Aktivierungsregeln dokumentieren:
  - Concepts;
  - Source-Rollen;
  - Claim-Typen;
  - Relationstypen;
  - mögliche negative Controls.
- Profiltests müssen Paraphrase- und False-Friend-Fälle enthalten: Ein Profil
  soll bei semantisch ähnlichen Holdouts feuern und bei lexikalisch ähnlichen,
  aber fachlich anderen Fragen nicht.

Akzeptanz:

- Q6-Q8, Kollegenbriefing und mindestens acht Holdouts nutzen Profile, ohne
  neue fragefamilienspezifische Intents.
- Profilwahl ist in einem Artefakt sichtbar, z. B. `research_profile_trace.json`.
- Ein Reviewer kann nachvollziehen, warum ein Profil aktiviert wurde.

## 7. Workstream C: Agentic Evidence Reading Loop

Ziel:

- Den Agenten nicht nur Top-Chunks konsumieren lassen, sondern
  quellenorientiert lesen lassen: Cluster, Passagen, Nachbarpassagen,
  Gegenbelege und offene Issues.

Umsetzung:

- Pipeline-Schritt vor dem Composer einführen:
  1. Frage in Teilfragen und claim-near questions zerlegen.
  2. Evidence-Cluster pro Teilfrage bilden.
  3. Pro Cluster beste Passage öffnen.
  4. Nachbarpassage öffnen, wenn Locator oder Abschnitt auf Kontext hindeutet.
  5. Höherrangige Quellen prüfen, wenn ein technisches oder proposal-stage
     Dokument eine normative Aussage stützt.
  6. Widersprüche, Status-/Revocation-Quellen und offene Issues verknüpfen.
  7. Candidate Claims mit Verifikationsstatus an den Composer geben.
- Neue Artefakte:
  - `reading_plan.json`;
  - `opened_passages.json`;
  - `evidence_synthesis_matrix.json`;
  - optional `profile_trace.json`.
- Bestehende Artefakte behalten und nur additiv erweitern.
- Budget-Grenzen pro Lauf konfigurieren:
  - maximale Evidence-Cluster;
  - maximale geöffnete Passagen;
  - maximale Nachbarpassagen pro Cluster;
  - Timeout;
  - Fallback-Verhalten, wenn das Budget erschöpft ist.

Akzeptanz:

- Für jede Kernaussage in der finalen Antwort gibt es einen Eintrag in der
  Synthesis Matrix.
- Source Reader kann die im Text referenzierten Passagen öffnen.
- Bei mehrdeutigen Begriffen, z. B. `PID Binding`, taucht die Begriffsklärung
  vor der Synthese in der Matrix auf.

## 8. Workstream D: Composer VNext

Ziel:

- Die finalen Antworten sollen Legacy-artige fachliche Dichte erreichen, aber
  mit Researcher-Artefaktstrenge.

Umsetzung:

- Composer bekommt ein strukturiertes Eingabemodell aus:
  - verified dynamic claims;
  - selected evidence;
  - source hierarchy report;
  - open issues;
  - evidence synthesis matrix;
  - research profile trace.
- Pro Kernaussage soll der Composer ausgeben können:
  - Aussage;
  - Claim-ID oder dynamic claim ID;
  - Source-ID;
  - Locator, Artikel, Abschnitt oder Seite;
  - Source Role / Evidence Tier;
  - Binding Level und Document Status;
  - Caveat oder Open Issue.
- Antwortmuster:
  - `Kurzantwort`;
  - `Normative Evidence`;
  - `Technical / Operational Interpretation`;
  - `Open Issues`;
  - optional `Gesprächsformulierung` für briefingartige Prompts.
- Bei mehrdeutigen Begriffen muss die Kurzantwort die relevante
  Begriffsklärung enthalten, wenn sie evidence-backed ist.
- Deutsche Ausgabequalität verbessern:
  - Umlaute nicht unnötig transliterieren;
  - konsistente Bezeichner für BAföG, eIDAS, EUDI, EUBW;
  - Zitierstil stabil halten.

Akzeptanz:

- Mehrdeutige Begriffe werden evidence-backed geklärt, wenn diese Klärung die
  Antwortgrenze verändert.
- Technische, normative und interpretive Aussagen werden sichtbar getrennt.
- Pro Kernaussage werden Source, Locator, Verification-Status und Caveat
  gerendert oder als strukturierter Beleg im Artefakt verknüpft.
- Fallkonkrete Regressionserwartungen, z. B. aus dem Kollegenbriefing, leben im
  Legacy-Parity-Pack und nicht als Composer-Sonderlogik.
- Jede normative Kernaussage ist source- und locator-gebunden.
- Answer-Text verbessert sich nicht auf Kosten der Artefakttraceability.

## 9. Workstream E: Legacy-Paritäts-Evaluation

Ziel:

- Nicht nur "akzeptable" Antworten messen, sondern spezifisch die
  Qualitätslücke gegenüber Legacy EUBW schließen.

Umsetzung:

- Neues Benchmark-Pack:
  `configs/legacy_parity_question_pack.yaml`.
- Inhalte:
  - Q1-Q8;
  - Kollegenbriefing PID-/Device-Binding, Imma, Rulebooks;
  - Legacy `gold_questions_rag*.jsonl` als Referenzfälle;
  - mindestens acht adjacent-unseen Holdouts;
  - mindestens drei mehrdeutige Begriffsfragen;
  - mindestens drei source-conflict Fragen;
  - mindestens drei corpus-gap Fragen.
- Neue Review-Dimensionen:
  - Begriffsklärung übernommen;
  - entscheidende Legacy-Konzepte getroffen;
  - source-role / binding-level korrekt;
  - locator density;
  - caveat preservation;
  - open issue preservation;
  - termin- oder briefing-taugliche Struktur, wenn angefragt;
  - keine overconfident final-law Aussagen aus proposal/spec Quellen.
- Vergleichsartefakt:
  - `legacy_parity_report.json`;
  - `legacy_parity_report.md`.

Paritäts-Scorecard:

| Dimension | Mindestkriterium |
| --- | --- |
| Kernaussagenabdeckung | Alle review-definierten Pflichtkonzepte einer Frage erscheinen in Kurzantwort oder Detailteil, oder werden als Gap markiert. |
| Quellenbindung | Jede normative Kernaussage hat Source-ID und Locator; technische Aussagen haben mindestens Source-ID und Abschnitt/Artefakt-Locator. |
| Source-Role-Treue | Proposal, technische Spezifikation, bindendes Recht und Interpretation werden nicht vermischt. |
| Caveat-Erhalt | Relevante Unsicherheiten aus Legacy oder `open_issues.json` werden übernommen, wenn sie die Antwortgrenze verändern. |
| Begriffsklärung | Mehrdeutige Nutzerbegriffe werden geklärt, wenn der Korpus eine solche Mehrdeutigkeit zeigt. |
| Legacy-Konzeptabdeckung | Die Legacy-Antwort darf bei entscheidenden Konzepten nicht mehr relevante Konzepte enthalten, ohne dass Researcher diese als Treffer oder Gap ausweist. |
| Artefakttraceability | Jede substantive Antwortaussage ist über Ledger, Verification oder Synthesis Matrix rückverfolgbar. |
| Termin-Tauglichkeit | Wenn der Prompt ein Briefing verlangt, stehen Kurzantworten vor Details und Open Issues. |

Ein Fall gilt als parity-pass, wenn alle harten Kriterien erfüllt sind:

- keine unsupported normative core claim;
- keine source-role violation;
- keine ausgelassene entscheidende Legacy-Kernaussage ohne Gap;
- keine verschlechterte Artefakttraceability gegenüber dem bisherigen
  Researcher-Pfad.

Weiche Kriterien wie Stil, Lesbarkeit und Gesprächsnützlichkeit werden im
Report getrennt ausgewiesen und dürfen ein Gate nur dann blockieren, wenn der
Prompt ausdrücklich ein briefing- oder terminfertiges Dokument verlangt.

Akzeptanz:

- Knowledge-Service-Pfad schlägt den alten Researcher-Pfad auf allen
  Paritätsfällen.
- Gegen Legacy EUBW ist er mindestens gleichwertig in Quellenbindung,
  Caveat-Erhalt und Kernaussagenabdeckung.
- Wo Legacy fachlich stärker bleibt, erzeugt der Report konkrete
  Fehlkategorien statt nur Score-Differenzen.

Maschinenlesbare harte Booleans in `legacy_parity_report.json`:

- `hard_gate_pass`;
- `required_concepts_met`;
- `unsupported_normative_claims`;
- `source_role_violations`;
- `locator_coverage`;
- `caveat_preservation_pass`;
- `artifact_traceability_pass`;
- `legacy_only_concepts_marked_as_gap_or_rejected`.

Report-Provenienz:

- `schema_version`;
- `catalog_digest`;
- `runtime_config_digest`;
- `question_pack_digest`;
- `legacy_reference_digest`;
- `freeze_manifest_digest`;
- `commit_sha`;
- `git_dirty`.

Artifact-Invariant-Gate:

- kein `hard_gate_pass`, wenn eine finale Kernaussage keinen Source-/Locator-,
  Verification- oder Synthesis-Matrix-Pfad hat;
- kein `hard_gate_pass`, wenn `answer_alignment.json` blocking violations
  enthält;
- kein `hard_gate_pass`, wenn `pinpoint_evidence.json` zitierte Evidenz nicht
  abbilden kann.

Optionales Zusatzmaß:

- Pairwise Blind Review kann Legacy, alten Researcher-Pfad und neuen
  Composer-VNext-Pfad ohne Repo-Label vergleichen. Das ist kein automatisches
  Release-Gate, aber ein sinnvolles Architekturentscheidungs-Signal.

## 10. Workstream F: Corpus-Governance Und Gap-Driven Web Expansion

Ziel:

- Relevante offizielle Dokumente können bei Lücken ergänzt werden, ohne den
  Korpus beliebig oder unprüfbar zu machen.

Umsetzung:

- Offizielle Webrecherche bleibt gap-driven und allowlist-bounded.
- Neu gefundene Quellen bekommen:
  - canonical URL;
  - retrieval timestamp;
  - digest;
  - admission policy;
  - source role;
  - binding level;
  - document status;
  - locator strategy.
- Antwortdateien sollen sichtbar machen:
  - welche Quellen bereits kuratiert waren;
  - welche Quellen neu ergänzt wurden;
  - welche Aussagen von neu ergänzten Quellen abhängen.

Akzeptanz:

- Keine Webquelle darf final-answer-governing sein, wenn Source Governance
  fehlt.
- Corpus-Ergänzungen sind reproduzierbar über Katalog- und Digest-Artefakte.

## 11. Phase 8: Rollout Und Decommissioning

Phase 8 bleibt der letzte Schritt, nicht der Anfang.

Runtime-Matrix:

| Runtime Config | Antwortverhalten | Neue Artefakte | Dynamic Evidence answer-governing | Composer VNext | Gate |
| --- | --- | --- | --- | --- | --- |
| `configs/runtime.yaml` | bisheriger Default | nein | nein | nein | Regression baseline |
| `configs/runtime.knowledge_shadow.yaml` | bisherige Antwort | Cluster/Verification sichtbar | nein | nein | Shadow artifact check |
| `configs/runtime.knowledge_assistive.yaml` | assistive dynamische Evidenz | Cluster/Selected/Verification sichtbar | ja, strikt verifiziert | nein | Migration pack and holdout check |
| `configs/runtime.knowledge_composer_vnext.yaml` | assistive plus claim-nahe Antwort | Reading Plan, Opened Passages, Synthesis Matrix, Profile Trace | ja, strikt verifiziert | ja | Legacy parity hard gate |
| rollback config / `configs/runtime.yaml` | bisheriger Default | alte Artefaktfläche | nein | nein | Rollback drill |

### 8.1 Shadow Default

- `configs/runtime.yaml` bleibt zunächst unverändert.
- `configs/runtime.knowledge_shadow.yaml` wird für Dual-Runs auf Standardfragen
  genutzt.
- Ziel: neue Artefakte erzeugen, ohne Antwortverhalten zu ändern.

Gate:

- Keine Regression in `scripts/run_unit_tests.py`,
  `scripts/run_integration_tests.py`, default question pack und `run_eval.py`.

### 8.2 Assistive Dual-Run

- Standardfragen werden parallel mit `runtime.yaml` und
  `runtime.knowledge_assistive.yaml` ausgeführt.
- Report vergleicht Antwortqualität, Source Coverage, Claim Coverage,
  Artifact Completeness und Review Verdicts.

Gate:

- Assistive Pfad ist in Q1-Q8, Legacy-Paritätspack und Holdouts mindestens
  gleichwertig.
- Keine Verbesserung darf durch neue benchmark-spezifische Intents, Targets,
  Aliases oder Source-Family-Hacks entstehen.

### 8.3 Composer VNext Hinter Feature Flag

- Composer VNext wird nur über eigene Runtime-Config aktiviert, z. B.
  `configs/runtime.knowledge_composer_vnext.yaml`.
- Alter Composer bleibt verfügbar.

Gate:

- VNext verbessert die Legacy-Paritätsmetriken.
- Jede neue Antwortaussage bleibt über Ledger, Claim Verification und
  Synthesis Matrix prüfbar.

### 8.4 Rollback Drill

- Eine dokumentierte Rollback-Probe beweist, dass `runtime.yaml` oder eine
  explizite rollback config den bisherigen Pfad wiederherstellt.
- Artefaktbundle bleibt kompatibel oder versioniert.

Gate:

- Rollback-Lauf produziert erwartete alte Artefakte und besteht Eval-Smoke.

### 8.5 Default-Umschaltung

- Erst nach bestandener Parität, Manual Review und Rollback-Probe wird der
  agentische Pfad Default für Real-Corpus-Runs.
- Empfohlen: zunächst `knowledge_service.enabled=true`,
  `discovery_mode=assistive`, Composer VNext noch feature-flagged; danach
  Composer VNext als Default, wenn die Paritätsreports stabil bleiben.

Gate:

- Mindestens zwei vollständige grüne Läufe:
  - default real question pack;
  - migration question pack;
  - legacy parity question pack;
  - `run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json`;
  - manuelle Review von mindestens drei high-risk Fragen.

### 8.6 Decommissioning

- Spezialisierte Intents werden nicht gelöscht, sondern als Regression- und
  Presentation-Overlays klassifiziert.
- Ein Intent oder Target darf erst entfernt werden, wenn der generische
  Profile-/Cluster-/Verification-Pfad dieselben Fälle ohne Speziallogik
  besteht.
- Rollback-Config bleibt mindestens einen Release-Zyklus erhalten.

## 12. Vorgeschlagene Umsetzungsschritte

1. Legacy-Parity-Pack und Freeze-Manifest vor Tuning erstellen.
2. Legacy-Import VNext und Crosswalk auf echte Legacy-Slices erweitern.
3. Research-Profile-Konfiguration und Profile-Trace einführen.
4. Evidence Reading Loop plus Synthesis Matrix implementieren.
5. Composer VNext hinter neuer Runtime-Config bauen.
6. Legacy-Parity-Report mit harten Booleans einführen.
7. Corpus-Governance für gap-driven Ergänzungen nachziehen.
8. Assistive Dual-Run und Rollback Drill durchführen.
9. Nach bestandenen Gates Phase-8-Default-Umschaltung vornehmen.

## 13. Standard-Validierung

Vor jedem Rollout-Gate:

```bash
python3 scripts/build_real_corpus_catalog.py
python3 scripts/build_source_crosswalk.py
python3 scripts/run_unit_tests.py
python3 scripts/run_integration_tests.py
python3 scripts/run_real_question_pack.py --all --catalog artifacts/real_corpus/curated_catalog.json
python3 scripts/run_real_question_pack.py --all --pack configs/migration_question_pack.yaml --catalog artifacts/real_corpus/curated_catalog.json --runtime-config configs/runtime.knowledge_assistive.yaml
python3 scripts/run_eval.py --all --catalog artifacts/real_corpus/curated_catalog.json
```

Nach Workstream E zusätzlich:

```bash
python3 scripts/build_legacy_parity_freeze_manifest.py
python3 scripts/run_real_question_pack.py --all --pack configs/legacy_parity_question_pack.yaml --catalog artifacts/real_corpus/curated_catalog.json --runtime-config configs/runtime.knowledge_composer_vnext.yaml
python3 scripts/run_legacy_parity.py --pack configs/legacy_parity_question_pack.yaml --catalog artifacts/real_corpus/curated_catalog.json --runtime-config configs/runtime.knowledge_composer_vnext.yaml
```

## 14. Review-Kriterien

Reviewer sollen den Plan oder eine Umsetzung ablehnen, wenn:

- Legacy-Claims ohne aktuelle Verification answer-governing werden.
- Research Profiles zu versteckten Benchmark-Intents werden.
- Der Knowledge Service selbst finale Prosa erzeugt.
- Antwortqualität steigt, aber Claim-/Source-/Locator-Traceability sinkt.
- Phase 8 als Default-Umschaltung ohne Rollback- und Paritätsgate umgesetzt
  wird.
- Source-Governance-Felder bei Corpus-Ergänzungen fehlen.
- Begriffliche Unsicherheiten aus der Evidenz nicht in der Antwort erscheinen.

## 15. Definition Of Done

Der Anschlussplan gilt als umgesetzt, wenn:

- EUBW-Researcher auf dem Legacy-Paritätspack mindestens so gut wie Legacy EUBW
  in Kernaussagen, Source Binding, Caveat-Erhalt und Reviewbarkeit abschneidet.
- Der neue Composer pro Kernaussage Source-/Locator- und Verification-Bezug
  herstellen kann.
- Legacy-Wissen als Kandidatenbasis nutzbar ist, ohne automatisch autoritativ
  zu sein.
- Research Profiles flexible Fragebeantwortung ermöglichen, ohne in
  benchmark-spezifische Intents zurückzufallen.
- Phase 8 mit Shadow, Dual-Run, Feature Flag, Rollback Drill und
  Decommissioning-Regeln abgeschlossen ist.
