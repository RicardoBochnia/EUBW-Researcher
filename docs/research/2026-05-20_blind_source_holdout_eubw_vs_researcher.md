# Blind Source Holdout: EUBW vs. EUBW-Researcher

Datum: 2026-05-20

Vollstaendiger externer Plan: `/mnt/c/Arbeit/EUBW/blind_source_holdout_2026-05-20_plan.md`

## Summary

Round 1 ist abgeschlossen, wird aber methodisch nicht als verwertbarer Vergleichspunkt gezaehlt. Im Blind-Content-Review gewann die Legacy-EUBW-Antwort gegen EUBW-Researcher. Beide Reviewer lagen bei der optionalen Identitaetsvermutung falsch: Sie hielten die quellen- und locatorreichere Legacy-Antwort fuer EUBW-Researcher.

Wichtige Nuance: Der Legacy-Standardpfad war nicht ausfuehrbar, weil `./.venv/bin/python` im Legacy-Repo nicht vorhanden/ausfuehrbar war. Die Legacy-Antwort entstand dadurch nicht ueber den vorgesehenen Query-Profile-Runtime-Pfad, sondern ueber direkte lokale Repo-Lektuere. Inhaltlich war sie im Review staerker; als sauberer Runtime-Pfadvergleich ist Round 1 deshalb eingeschraenkt.

Post-Round-Fix: Im Legacy-Repo wurde ein ignorierter venv-Kompatibilitaets-Shim `.venv/bin/python` auf die vorhandene `.venv/Scripts/python.exe` gelegt. Der geplante Legacy-Befehl laeuft danach durch und endet mit `contract_checks=pass`. Round 2 kann daher wieder als Runtime-Pfadvergleich gestartet werden.

## Round 1

Round id: `round-1-ebw-public-procedure-boundary`

Frage:

> Ein Unternehmen will wissen, wofuer eine European Business Wallet kuenftig praktisch eingesetzt werden kann. Welche Arten von Behoerden- und Unternehmensinteraktionen sollte sie fachlich abdecken, und wo liegen die Grenzen zwischen echter Wallet-Interaktion, blosser Kommunikation und noch offener technischer Umsetzung?

### Pre-Run Checks

Novelty-Check:

- Treffer zu aehnlichen EBW-Benchmarks existieren, insbesondere Public-Sector-Wallet, Article-16-Aktionen und QERDS-Kommunikationskanal.
- Keine identische Frage gefunden.
- Bewertung: akzeptabler diagnostischer Holdout, aber nicht komplett orthogonal zu bestehenden EBW-Fragen.

Gemeinsame Quellen:

- EUBW-Researcher hat `ebw_proposal_com_2025_0838` und `ebw_annex_com_2025_0838` im real-corpus-Katalog.
- Legacy-Katalog enthaelt `52025PC0838`/`COM_2025_0838`/Business-Wallet/EBW-Hinweise.
- Corpus-Confounder: keiner fuer die erwarteten EBW-Quellenanker sichtbar.

### Commands

Researcher:

```bash
python3 scripts/answer_question.py "Ein Unternehmen will wissen, wofuer eine European Business Wallet kuenftig praktisch eingesetzt werden kann. Welche Arten von Behoerden- und Unternehmensinteraktionen sollte sie fachlich abdecken, und wo liegen die Grenzen zwischen echter Wallet-Interaktion, blosser Kommunikation und noch offener technischer Umsetzung?" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/blind_source_holdout_2026-05-20/round-1-ebw-public-procedure-boundary/researcher
```

Legacy:

```bash
./.venv/bin/python scripts/query_with_profile.py \
  --profile analysis_hybrid_semantic_global_tuned \
  --question "Ein Unternehmen will wissen, wofuer eine European Business Wallet kuenftig praktisch eingesetzt werden kann. Welche Arten von Behoerden- und Unternehmensinteraktionen sollte sie fachlich abdecken, und wo liegen die Grenzen zwischen echter Wallet-Interaktion, blosser Kommunikation und noch offener technischer Umsetzung?" \
  --fail-on-contract \
  --no-write-answer
```

Legacy-Fallback:

```bash
./.venv/bin/python scripts/query_with_profile.py \
  --profile analysis_balanced_global \
  --question "Ein Unternehmen will wissen, wofuer eine European Business Wallet kuenftig praktisch eingesetzt werden kann. Welche Arten von Behoerden- und Unternehmensinteraktionen sollte sie fachlich abdecken, und wo liegen die Grenzen zwischen echter Wallet-Interaktion, blosser Kommunikation und noch offener technischer Umsetzung?" \
  --fail-on-contract \
  --no-write-answer
```

Legacy Runtime-Befund:

- `./.venv/bin/python` war nicht ausfuehrbar.
- Der Legacy-Agent nutzte danach direkte lokale Artefakte und Claims.
- Das ist eine Methodeneinschraenkung der Runde.

### Redaction Log

Keine inhaltliche Redaktion.

| System alias | Entfernte Textart | Anzahl |
| --- | --- | ---: |
| A | keine | 0 |
| B | keine | 0 |

### Anonymisierte Antworten

System A:

> Eine European Business Wallet sollte fachlich vor allem Interaktionen abdecken, in denen ein Unternehmen gegenüber Behörden oder Geschäftspartnern verlässlich als wirtschaftlicher Akteur auftreten muss: Identifikation und Authentifizierung, elektronisches Signieren oder Siegeln von Dokumenten, Speichern, Einreichen und Empfangen von Dokumenten sowie Senden und Empfangen von Mitteilungen. Der EBW-Vorschlag COM(2025)838 nennt außerdem typische Entlastungsfälle wie Registrierung, Lizenzierung und Reporting sowie die Wiederverwendung verifizierter Daten und amtlicher Nachweise über Grenzen hinweg.
>
> Die echte Wallet-Interaktion liegt dort, wo die Wallet nicht nur ein Postfach ist, sondern vertrauenswürdige Nachweise, Identitäten oder Erklärungen technisch und rechtlich nutzbar macht: ein Unternehmen weist Attribute nach, erhält oder präsentiert Attestierungen, authentifiziert sich, unterschreibt/siegelt oder übermittelt verifizierte Unterlagen. Dazu passen die eIDAS-Änderung durch Verordnung (EU) 2024/1183, Durchführungsrecht zu elektronischen Attributsattestierungen, sowie OpenID4VCI/OpenID4VP als technische Muster für Ausstellung und Präsentation von Credentials.
>
> Die Grenze zur bloßen Kommunikation verläuft dort, wo nur Nachrichten oder Unterlagen transportiert werden, ohne dass Identität, Berechtigung, Signatur/Siegel oder verifizierte Attribute wallet-basiert geprüft oder verwendet werden. Auch der EBW-Vorschlag hält fest, dass die Pflicht öffentlicher Stellen zur Annahme von Business Wallets nicht die Systeme für Dokumenten- oder Datenaustausch zwischen zuständigen Behörden berühren soll. Die Wallet ergänzt also Verwaltungsverfahren und bestehende Austauschmechanismen, ersetzt sie aber nicht automatisch.
>
> Offen bleibt die technische und rechtliche Konkretisierung überall dort, wo der Korpus nur den Vorschlagsstand belegt: Die EBW-Regelung COM(2025)838 ist als Vorschlag gekennzeichnet, also nicht als endgültiges Recht zu behandeln. Die vorhandenen technischen Standards belegen Credential-Ausstellung und -Präsentation, aber nicht die vollständige Umsetzung jedes Verwaltungsverfahrens, jedes Benachrichtigungskanals oder jeder Fachintegration.

System B:

> Eine European Business Wallet sollte fachlich vor allem B2G- und registerbezogene Unternehmensinteraktionen abdecken: Identifikation und Authentifizierung von Unternehmen bzw. wirtschaftlichen Akteuren, Einreichung von Dokumenten, elektronische Signatur/Siegelung, verfahrensbezogene Benachrichtigungen sowie den Austausch von Unternehmensidentitätsdaten und elektronischen Attributsattestationen. Der lokale Evidenzbestand stuetzt das besonders fuer oeffentliche Stellen: Sie sollen wirtschaftlichen Akteuren die Nutzung von EBW-Kernfunktionen ermoeglichen; fuer Dokumenten- und Benachrichtigungsfluesse ist QERDS als sicherer Kommunikationsbaustein vorgesehen. Belege: SRC-L-EBW-04, Art. 16; SRC-L-EBW-09, S. 30/34; SRC-L-EBW-04, Art. 43.
>
> Der zweite fachliche Kern sind Nachweise aus Registern und anderen authentischen Quellen: Unternehmens-/Owner-Identifikation, eindeutige Identifikatoren, elektronische Attributsnachweise, Unternehmensstatus, Berechtigungen sowie Vertretungsrechte und Mandate. Die Wallet ist hier nicht nur ein Postfach, sondern ein Traeger und Praesentationsmittel fuer maschinenpruefbare Nachweise, deren Herkunft, Status und rechtliche Wirkung nachvollziehbar sein muessen. Belege: SRC-L-02-FT-EN-DOC_1, Art. 45b/45f; SRC-L-EBW-04, Art. 2/3; SRC-L-EBW-04, S. 3.
>
> Echte Wallet-Interaktion beginnt dort, wo die Wallet-Funktionen selbst genutzt werden: Daten oder Attestationen werden ausgestellt, angefordert, gespeichert, geteilt, praesentiert, widerrufen oder validiert; Gegenparteien werden ueber Wallet-Relying-Party-Access-Certificates, Wallet-Unit-Attestations und Statusinformationen geprueft; Transaktionen und relevante Interaktions-/Kommunikationsspuren werden exportierbar oder auditierbar gehalten. Belege: SRC-L-EBW-04, Art. 5; SRC-L-EBW-05, Art. 8; SRC-L-06-FT-EN-DOC_1, Art. 3/4; SRC-L-04-FT-EN-DOC_1, Art. 9.
>
> Blosse Kommunikation liegt dagegen vor, wenn nur eine Nachricht, Zustellung oder Verfahrensinformation uebermittelt wird, ohne dass dabei Wallet-Identitaet, Attestation, Berechtigungspruefung, Signatur/Siegel, Statusvalidierung oder Wallet-Transaktionslogik fachlich gebraucht wird. QERDS kann Teil einer Wallet-Interaktion sein, ist aber fachlich nicht automatisch die ganze Wallet: Erst die Verbindung mit identifizierter Gegenpartei, Nachweisen, Validierung und Verfahrenshandlung macht daraus mehr als sichere Kommunikation.
>
> Offen bleibt vor allem die konkrete technische Umsetzung: Wire-Formate fuer Wallet-Attestations, Registrar-APIs, Certificate-Policies, sektorale Attributprofile, ein voll harmonisiertes Schema fuer Vertretungsrechte/Mandate und vollstaendige End-to-End-Prozessprofile sind im lokalen Bestand eher als spaetere Spezifikation, vorgeschlagene Regelung oder offene Luecke sichtbar. Darum sollte ein Unternehmen die EBW kurzfristig als Infrastruktur fuer verifizierbare B2G-Nachweise, Identifikation, Einreichung, Zustellung und Rollenvalidierung verstehen, nicht als bereits fertig ausdefinierten Universalprozess fuer alle Unternehmensinteraktionen.

### Blind Review Matrix

| Reviewer | System | Quellentreue | Antwortqualitaet | Grenzen/Luecken | Traceability | Nutzbarkeit | Hard Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| reviewer_1 | A | 2 | 3 | 2 | 1 | 2 | none |
| reviewer_1 | B | 2 | 3 | 3 | 3 | 3 | none |
| reviewer_2 | A | 2 | 3 | 3 | 1 | 2 | none |
| reviewer_2 | B | 2 | 3 | 2 | 3 | 3 | none |

Totals:

| System | Reviewer 1 | Reviewer 2 | Average |
| --- | ---: | ---: | ---: |
| A | 10 | 11 | 10.5 |
| B | 14 | 13 | 13.5 |

Konfliktaufloesung:

- Keine Abweichung groesser als 1 Punkt je Kriterium.
- Kein Hard-Error-Widerspruch.
- Keine Adjudication erforderlich.

Reviewer-Identitaetsvermutungen:

| Reviewer | guessed A | guessed B | Confidence | Ergebnis |
| --- | --- | --- | ---: | --- |
| reviewer_1 | Legacy | Researcher | 2 | falsch |
| reviewer_2 | Legacy | Researcher | 2 | falsch |

Fingerprinting-Befund:

- Beide Reviewer interpretierten starke Source-ID-/Locator-Traceability als Researcher-Signal.
- Das war hier falsch: Die Legacy-Antwort war traceability-staerker.
- Das spricht gegen triviales Repo-Fingerprinting in Round 1, zeigt aber auch, dass Source-ID-Stil allein kein verlaessliches Identitaetsmerkmal ist.

### Entblindung

| System alias | Repo |
| --- | --- |
| A | EUBW-Researcher |
| B | Legacy-EUBW |

Round-1-Ergebnis:

- Blind-Content-Review: Legacy-EUBW gewinnt.
- Wertung fuer Holdout-Gesamtstand: nicht gezaehlt, weil der Legacy-Standardpfad in der urspruenglichen Runde nicht lief.
- EUBW-Researcher: haette die Runde nach reiner Blind-Review-Punktzahl verloren; diese Niederlage wird wegen des Runtime-Confounders nicht in die 3/4-Stichprobe aufgenommen.
- Keine harten Fehler bei beiden Antworten.

### Methodendiagnose

Researcher-Agent:

- `repo_helpfulness_score`: 3
- Standardpfad lief und schrieb vollstaendige Artefakte unter `artifacts/tmp/blind_source_holdout_2026-05-20/round-1-ebw-public-procedure-boundary/researcher`.
- Vorhandene Artefakte: u. a. `final_answer.txt`, `approved_ledger.json`, `reading_plan.json`, `opened_passages.json`, `evidence_synthesis_matrix.json`, `selected_evidence.json`, `manual_review_report.md`.
- Subagent musste aus Artefakten eine bessere Antwort synthetisieren; `final_answer.txt` selbst war eher Pruefprotokoll als fachliche Produktantwort.
- `reading_plan.json` oeffnete u. a. eIDAS 2024/1183, eIDAS 2014/910, CIR 2025/1569, CIR 2024/2977, EBW Proposal, OpenID4VCI und OpenID4VP.
- EBW Proposal wurde nur dokument-/PDF-level geoeffnet, ohne praezisen Article-16-Anker.
- `evidence_synthesis_matrix.json` enthielt teils rohe/trunkierte Passagen statt direkt nutzbarer Syntheseaussagen.

Legacy-Agent:

- `repo_helpfulness_score`: 2
- Vorgesehener Primaerbefehl und Fallback konnten wegen fehlendem `./.venv/bin/python` nicht laufen.
- Antwort wurde ueber direkte lokale Lektuere rekonstruiert: `docs/05_use_cases.md`, `docs/07_findings.md`, `docs/08_recommendations.md`, `answers.MD` und `knowledge/claims`.
- Trotz Runtime-Ausfall war die Antwort im Blind-Review fachlich und traceability-seitig staerker.

Limitation:

- Legacy hat keine aequivalenten Intermediate-Artefakte zu `reading_plan.json`, `opened_passages.json` oder `evidence_synthesis_matrix.json`; Pfadqualitaet ist daher asymmetrisch beobachtbar.
- Round 1 ist kein sauberer Runtime-Pfadvergleich, weil Legacy nicht ueber den geplanten CLI-Pfad antwortete.

### Verbesserungsfolgerungen fuer EUBW-Researcher

1. Der vNext-Renderer muss bei breiten EBW-Fragen eine echte Fachantwort erzeugen, nicht nur ein Ledger-/Pruefprotokoll.
2. EBW Proposal/Annex brauchen bessere PDF- bzw. Abschnittsanker; dokument-level Evidenz reicht fuer Article-16-nahe Fragen nicht.
3. Die Reading-Loop muss EBW-spezifische Artikel mit hoher Signalstaerke bevorzugen. In Round 1 wurden mehrere generische eIDAS-/OpenID-Passagen vor praezisen EBW-Artikeln geoeffnet.
4. Die `evidence_synthesis_matrix` sollte verwertbare Synthesezeilen enthalten, keine rohen abgeschnittenen Snippets.
5. Gute Traceability im Antworttext bleibt entscheidend. Die Researcher-Subagentenantwort verlor vor allem wegen zu grober Quellenhinweise.

### Entscheidung fuer Round 2

Die Rubrik bleibt eingefroren. Keine Adjudication-Aenderung erforderlich.

Der Legacy-Pfad wurde repariert. Round 2 soll mit dem urspruenglich geplanten Legacy-Befehl laufen:

```bash
./.venv/bin/python scripts/query_with_profile.py \
  --profile analysis_hybrid_semantic_global_tuned \
  --question "$QUESTION" \
  --fail-on-contract \
  --no-write-answer
```

## Round 2: trust_mark_boundary

### Frage

> Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?

### Pre-Run Checks

Novelty:

- Keine Treffer in `configs/legacy_parity_question_pack.yaml`.
- Keine Treffer in `configs/legacy_gold_holdout_question_pack.yaml`.
- Keine Treffer in Legacy-`knowledge/benchmarks/*.jsonl`.

Gemeinsame Quellen:

- EUBW-Researcher-Katalog enthaelt `ec_ts01_wallet_trust_mark` mit `archive_source_id=SRC-W-TEC-26`.
- Legacy enthaelt dieselbe Quelle unter `sources/reference_web/technical_and_standards/SRC-W-TEC-26_ec_ts01_wallet_trust_mark.md`.
- Beide Repos enthalten zudem eIDAS-Quellen zum Wallet Trust Mark und Zertifizierungskontext.

### Verwendete Befehle

Researcher:

```bash
python3 scripts/answer_question.py "Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/blind_source_holdout_2026-05-20/round-2-trust-mark-boundary/researcher
```

Legacy:

```bash
./.venv/bin/python scripts/query_with_profile.py \
  --profile analysis_hybrid_semantic_global_tuned \
  --question "Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen entfernen, und was sagt das darueber aus, ob damit auch Relying Parties oder Attestation Provider bewertet werden?" \
  --fail-on-contract \
  --no-write-answer
```

Legacy Runtime-Befund:

- Der reparierte Legacy-Standardpfad lief.
- Kein Contract-Failure wurde fuer diese Runde berichtet.

### Redaction Log

Keine inhaltliche Redaktion.

| System alias | Entfernte Textart | Anzahl |
| --- | --- | ---: |
| A | keine | 0 |
| B | keine | 0 |

### Anonymisierte Antworten

System A:

> Ein Wallet-Provider muesste das sichtbare EUDI-Wallet-Vertrauenszeichen entfernen, sobald die Grundlage fuer dessen Anzeige wegfaellt: Die betroffene Wallet-Loesung ist dann nicht mehr als zertifizierte Wallet gueltig oder nicht mehr von mindestens einem Mitgliedstaat anerkannt. Die Trust-Mark-Spezifikation sagt dazu ausdruecklich, dass das Zeichen nur angezeigt werden darf, wenn die Wallet diese beiden Voraussetzungen erfuellt; werden sie unanwendbar und kommt es zur Stornierung, muss der Wallet-Provider das sichtbare Zeichen und alle Bezugnahmen darauf aus der betroffenen Wallet-Loesung entfernen. Gestuetzt wird das durch Regulation (EU) 2024/1183: Die Zertifizierung kann bei nicht rechtzeitig behobener Schwachstelle aufgehoben werden; Mitgliedstaaten informieren Kommission und Cooperation Group ueber aufgehobene Zertifizierungen, und die Kommission fuehrt die Liste zertifizierter Wallets fort.
>
> Fuer Relying Parties und Attestation Provider folgt daraus gerade keine Mitbewertung. Der Trust Mark bezieht sich auf die EUDI-Wallet-Loesung und ihre Zertifizierungs-/Anerkennungsstellung. Die Trust-Mark-Spezifikation grenzt den Scope ausdruecklich ab: Nicht umfasst sind Relying-Party-Services oder Qualifikationen von Attestation Providern. Solche Rollen koennen in anderen Registern, Zertifikaten oder Vertrauensankern vorkommen, aber das sichtbare Wallet-Vertrauenszeichen ist kein Urteil ueber sie.

System B:

> Ein Wallet-Provider muesste das sichtbare EUDI-Wallet-Vertrauenszeichen entfernen, wenn die Nutzungsvoraussetzungen fuer das betroffene Wallet wegfallen und es zur Cancellation kommt: Das Wallet darf das Zeichen nur anzeigen, solange es als Wallet-Solution den Anforderungen entspricht, also zertifiziert ist, und zugleich von mindestens einem Mitgliedstaat anerkannt wird. Werden diese Grundvoraussetzungen nicht mehr erfuellt, sollen die Mitgliedstaaten Kommission und Cooperation Group informieren; nach der Cancellation muss der Wallet-Provider das sichtbare Trust Mark und Verweise darauf aus der betroffenen Wallet-Solution entfernen.
>
> Das sagt gerade nicht, dass damit auch Relying Parties oder Attestation Provider bewertet werden. Die lokale Trust-Mark-Spezifikation grenzt den Umfang ausdruecklich auf das in der EUDI Wallet sichtbare Zeichen fuer die Wallet-Solution ein; Relying-Party-Services und Attestation-Provider-Qualifikationen liegen ausserhalb dieses Trust-Mark-Scopes. Relying Parties werden separat ueber Wallet-Relying-Party Access Certificates/Registrierung adressiert, aber das Wallet-Vertrauenszeichen ist kein Guetesiegel fuer sie oder fuer Attestation Provider. Quellen: SRC-W-TEC-26, Sections 1.1 und 1.2; Query-Ausgabe mit SRC-L-06/SRC-L-33 zu Wallet-Relying-Party Access Certificates.

### Blind Review Matrix

| Reviewer | System | Quellentreue | Antwortqualitaet | Grenzen/Luecken | Traceability | Nutzbarkeit | Hard Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| reviewer_1 | A | 2 | 3 | 2 | 1 | 2 | none |
| reviewer_1 | B | 2 | 3 | 2 | 3 | 3 | none |
| reviewer_2 | A | 2 | 3 | 2 | 1 | 2 | none |
| reviewer_2 | B | 3 | 3 | 3 | 3 | 3 | none |

Totals:

| System | Reviewer 1 | Reviewer 2 | Average |
| --- | ---: | ---: | ---: |
| A | 10 | 10 | 10.0 |
| B | 13 | 15 | 14.0 |

Konfliktaufloesung:

- Keine Abweichung groesser als 1 Punkt je Kriterium.
- Kein Hard-Error-Widerspruch.
- Keine Adjudication erforderlich.

Reviewer-Identitaetsvermutungen:

| Reviewer | guessed A | guessed B | Confidence | Ergebnis |
| --- | --- | --- | ---: | --- |
| reviewer_1 | Legacy | Researcher | 2 | falsch |
| reviewer_2 | Legacy | Researcher | 2 | falsch |

Fingerprinting-Befund:

- Beide Reviewer hielten System B wegen Source-IDs, Sections und staerkerer Evidenzorientierung fuer Researcher.
- Das war erneut falsch. Die staerkere Traceability kam aus der Legacy-Antwort.

### Entblindung

| System alias | Repo |
| --- | --- |
| A | EUBW-Researcher |
| B | Legacy-EUBW |

Round-2-Ergebnis:

- Wertung fuer Holdout-Gesamtstand: zaehlbar.
- Blind-Content-Review: Legacy-EUBW gewinnt.
- EUBW-Researcher verliert wegen deutlich schlechterer Traceability im Antworttext.
- Keine harten Fehler bei beiden Antworten.
- Kein Corpus-Confounder: die zentrale Trust-Mark-Quelle war in beiden Repos vorhanden.

### Methodendiagnose

Researcher-Agent:

- `repo_helpfulness_score`: 2
- Standardpfad lief und schrieb Artefakte unter `artifacts/tmp/blind_source_holdout_2026-05-20/round-2-trust-mark-boundary/researcher`.
- Der Katalog enthielt die richtige Quelle `ec_ts01_wallet_trust_mark` / `SRC-W-TEC-26`.
- Der vNext-Lauf hob diese Quelle aber nicht in den `reading_plan.json`.
- `reading_plan.json` oeffnete stattdessen u. a. eIDAS 2024/1183, eIDAS 2014/910, WRP-Registration 2025/848, Wallet-Breach 2025/847, ARF-Trust-Model, RP-Registration-Diskussionen und OpenID4VCI.
- `final_answer.txt` war fachlich klar daneben fokussiert: Es begann mit Wallet-Relying-Party-Access-Certificate und war eher Claim-/Pruefprotokoll als Antwort auf das Trust-Mark-Entfernungsproblem.
- Die bessere System-A-Antwort entstand erst durch gezielte direkte Quellenlekture im Repo, nicht durch den vNext-Final-Answer selbst.

Legacy-Agent:

- `repo_helpfulness_score`: 3
- Der geplante Query-Pfad lief.
- Die Antwort nutzte ebenfalls direkte lokale Lektuere der Trust-Mark-Spezifikation, war aber im Review sichtbar besser belegbar.
- Friktion: Auch Legacy brauchte nach eigener Methodennotiz direkte Quellenlekture, weil die erste Query-Ausgabe staerker RP-/Attestation-Kontext als die Trust-Mark-Kernstelle traf.

Limitation:

- Legacy hat keine aequivalenten Intermediate-Artefakte zu `reading_plan.json`, `opened_passages.json` oder `evidence_synthesis_matrix.json`; Pfadqualitaet ist daher asymmetrisch beobachtbar.
- Trotzdem ist Round 2 als Runtime-Pfadvergleich verwertbar, weil beide Antwort-Agenten den geplanten Repo-Pfad nutzen konnten und die zentrale Quelle in beiden Repos vorhanden war.

### Verbesserungsfolgerungen fuer EUBW-Researcher

1. Der Retriever muss Dokumenttitel und zentrale Section-Treffer hoeher gewichten: Eine Frage mit "Wallet-Vertrauenszeichen" darf `ec_ts01_wallet_trust_mark` nicht uebergehen.
2. vNext muss `final_answer.txt` als produktorientierte Fachantwort rendern. Der aktuelle automatisierte Review akzeptierte eine klar unnuetzliche Antwort als `accept`.
3. Source-IDs und Locators muessen in der Antwort sichtbar bleiben, sonst verliert Researcher selbst bei fachlich plausibler Synthese gegen Legacy.
4. Die `evidence_synthesis_matrix` sollte kurze, zitierfaehige Aussagen enthalten. In dieser Runde enthielt sie wieder stark trunkierte Rohtextfragmente.
5. Die Review-Gates muessen erkennen, wenn die Antwort thematisch abdriftet, obwohl Quellen formal bestaetigt sind.

## Round 3: rp_intermediary_disclosure

### Frage

> Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck und Datenschutzinformationen auseinanderhalten?

### Pre-Run Checks

Novelty:

- Aehnliche, aber nicht identische Legacy-Benchmarks existieren zu RPAC/WRPRC und Relying-Party-Registration-Certificates.
- Keine identische Frage zu Nutzeranzeige plus Intermediaer-Trennung wurde in den lokalen Packs gefunden.

Gemeinsame Quellen:

- EUBW-Researcher enthaelt TS05/TS06 zu Relying-Party-Registration-Information und ARF-Abschnitte zu Relying Parties, Relying Party Instances und Intermediaries.
- Legacy-EUBW enthaelt dieselben Quellfamilien, u. a. `SRC-W-TEC-30`, `SRC-W-TEC-31`, `SRC-W-TEC-04` und einschlaegige RP-Registration-Claims.

### Verwendete Befehle

Researcher:

```bash
python3 scripts/answer_question.py "Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck und Datenschutzinformationen auseinanderhalten?" \
  --catalog artifacts/real_corpus/curated_catalog.json \
  --runtime-config configs/runtime.knowledge_composer_vnext.yaml \
  --output-dir artifacts/tmp/blind_source_holdout_2026-05-20/round-3-rp-intermediary-disclosure/researcher
```

Legacy:

```bash
./.venv/bin/python scripts/query_with_profile.py \
  --profile analysis_hybrid_semantic_global_tuned \
  --question "Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt: welche Informationen muessen in Registrierung und Nutzeranzeige erhalten bleiben, und wie sollte die Wallet Relying Party, Intermediaer, Zweck und Datenschutzinformationen auseinanderhalten?" \
  --fail-on-contract \
  --no-write-answer
```

Legacy Runtime-Befund:

- Der geplante Query-Pfad lief laut Legacy-Answer-Agent mit `contract_checks=pass`.
- Kein Fallback war erforderlich.

### Redaction Log

Keine inhaltliche Redaktion.

| System alias | Entfernte Textart | Anzahl |
| --- | --- | ---: |
| A | keine | 0 |
| B | keine | 0 |

### Anonymisierte Antworten

System A:

> Wenn eine Wallet-Relying Party ueber einen Intermediaer handelt, darf die fachliche Rolle der eigentlichen Wallet-Relying Party nicht hinter dem Intermediaer verschwinden. In der Registrierung muessen die Identitaet der Wallet-Relying Party, nutzerfreundlicher Name, eindeutiger Identifier, Kontakt-/Supportdaten, Entitlements, Dienstbeschreibung, der konkrete Intended Use, die dafuer angefragten Attestationen/Attribute, die Datenschutzaufsicht und die Privacy-Policy-Information erhalten bleiben. Zusaetzlich muss kenntlich bleiben, dass ein Intermediaer genutzt wird, inklusive Zuordnung zum Intermediaer, dessen nutzerfreundlichem Namen, eindeutigem Identifier und Registrar-/Registry-Bezug.
>
> In der Nutzeranzeige sollte die Wallet daher trennen: Der Intermediaer ist der technisch auftretende/requestende Akteur und wird ueber sein Access Certificate authentifiziert; die intermediierte Wallet-Relying Party ist die fachliche Partei, fuer deren Dienst und Zweck Daten angefragt werden; der Zweck gehoert zum registrierten Intended Use dieser Wallet-Relying Party; Datenschutzinformationen und Privacy Policy sollten auf diesen Intended Use bzw. diese End-Relying Party zeigen, nicht pauschal auf den Intermediaer. Die Anzeige sollte also sinngemaess sagen: "Intermediaer X handelt im Auftrag von Wallet-Relying Party Y", dazu die angefragten Attribute, den registrierten Zweck, die passende Privacy Policy und ggf. DPA-/Beschwerdeinformationen zeigen.
>
> Pro Presentation Request sollte nur ein Intended Use behandelt werden. Die Wallet sollte pruefen koennen, ob die angefragten Attribute zu diesem registrierten Zweck passen, und den Nutzer warnen, wenn Attribute nicht registriert sind, die Intermediaer-Beziehung nicht verifizierbar ist oder Registrierungsinformationen nicht abrufbar sind. Der Intermediaer darf die erhaltenen Transaktionsdaten nicht als eigene Zweck-/Datenschutzdomaene vereinnahmen: Er leitet sie nur an die beauftragende Wallet-Relying Party weiter und loescht sie danach; Loesch- oder Datenschutzanfragen richten sich grundsaetzlich an die eigentliche Wallet-Relying Party.

System B:

> Eine Wallet-Relying Party bleibt auch dann die fachlich massgebliche Relying Party, wenn sie die Wallet-Interaktion durch einen Intermediaer abwickeln laesst. Der Intermediaer ist selbst als Relying Party zu behandeln, authentifiziert sich gegenueber der Wallet aber mit seinem eigenen Access Certificate und darf Transaktionsinhalte nicht dauerhaft speichern.
>
> In der Registrierung muessen deshalb getrennt erhalten bleiben: die Identitaet der eigentlichen Wallet-Relying Party, ihre registrierten Zwecke, die je Zweck zulaessigen Daten/Attribute, die Datenschutzinformationen zum jeweiligen Zweck sowie die Information, dass sie einen bestimmten Intermediaer nutzt. Zusaetzlich muss der Intermediaer als eigene Partei identifizierbar bleiben, mit eigenem Namen, Identifier und Registrar-/Kontaktbezug. Wenn Registration Certificates genutzt werden, sollte das Zertifikat fuer die intermediierte Relying Party den registrierten Zweck, den Datenumfang, die Privacy-Policy-URL und die Intermediaer-Beziehung ausdruecken; ohne Zertifikat muss die Wallet diese Informationen beim Registrar der intermediaeren Relying Party pruefen koennen.
>
> In der Nutzeranzeige sollte die Wallet klar trennen:
> - Wer fragt technisch an: der Intermediaer, erkennbar aus dessen Access Certificate.
> - Fuer wen wird gefragt: die intermediierte Wallet-Relying Party, erkennbar aus Request/Registration Certificate/Registrar.
> - Wofuer wird gefragt: genau ein registrierter intended use pro Praesentationsanfrage.
> - Welche Daten sind erlaubt: nur die fuer diesen intended use registrierten Attestationen/Attribute.
> - Welche Datenschutzinformationen gelten: Privacy Policy und zustaendige Datenschutzaufsicht der eigentlichen Wallet-Relying Party bzw. des konkreten intended use, nicht pauschal die des Intermediaers.
>
> Praktisch heisst das: Die Wallet sollte dem Nutzer nicht nur "Intermediaer X moechte Daten" anzeigen, sondern "Intermediaer X handelt fuer Wallet-Relying Party Y; Zweck Z; angefragte Daten A/B/C; Datenschutzinformationen/Privacy Policy und DPA-Kontakt fuer Y/Z". Wenn Name/Identifier des Intermediaers aus dem Access Certificate nicht zur in der Registrierung hinterlegten Intermediaer-Beziehung passen, oder wenn Zweck/Datenumfang nicht registriert sind, sollte die Wallet den Nutzer warnen.

### Blind Review Matrix

| Reviewer | System | Quellentreue | Antwortqualitaet | Grenzen/Luecken | Traceability | Nutzbarkeit | Hard Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| reviewer_1 | A | 1 | 2 | 1 | 0 | 2 | yes |
| reviewer_1 | B | 2 | 3 | 2 | 0 | 2 | yes |
| reviewer_2 | A | 1 | 2 | 1 | 0 | 2 | yes |
| reviewer_2 | B | 2 | 3 | 2 | 0 | 2 | yes |

Totals:

| System | Reviewer 1 | Reviewer 2 | Average |
| --- | ---: | ---: | ---: |
| A | 6 | 6 | 6.0 |
| B | 9 | 9 | 9.0 |

Konfliktaufloesung:

- Keine Abweichung groesser als 1 Punkt je Kriterium.
- Beide Reviewer sahen bei beiden Systemen denselben Hard Error: keine konkreten Quellenpfade, Locators oder pruefbaren Evidenzverweise in der anonymisierten Antwort.
- Keine Adjudication erforderlich.

Reviewer-Identitaetsvermutungen:

| Reviewer | guessed A | guessed B | Confidence | Ergebnis |
| --- | --- | --- | ---: | --- |
| reviewer_1 | keine belastbare Vermutung | keine belastbare Vermutung | 0 | nicht anwendbar |
| reviewer_2 | keine belastbare Vermutung | keine belastbare Vermutung | 0 | nicht anwendbar |

Fingerprinting-Befund:

- Beide Reviewer konnten die Systeme nicht belastbar erraten.
- Durch das Fehlen von Quellen-/Artefaktspuren war Fingerprinting in dieser Runde niedrig, allerdings war dadurch auch die Traceability-Bewertung fuer beide Systeme bei 0.

### Entblindung

| System alias | Repo |
| --- | --- |
| A | EUBW-Researcher |
| B | Legacy-EUBW |

Round-3-Ergebnis:

- Wertung fuer Holdout-Gesamtstand: diagnostisch verwertbar, aber nicht als sauberer Sieg/Niederlage-Punkt, weil beide anonymisierten Antworten denselben Hard Error erhielten.
- Blind-Content-Review ohne Hard-Error-Regel: Legacy-EUBW liegt vorn.
- Mit Hard-Error-Regel: beide Systeme bestehen die Runde nicht, da beide Review-Antworten ohne Quellenpfad nicht ueberpruefbar waren.
- Kein offensichtlicher Corpus-Confounder: die relevanten RP-Registration-/Intermediaer-Quellfamilien waren in beiden Repos vorhanden.

### Methodendiagnose

Researcher-Agent:

- Standardpfad lief und schrieb Artefakte unter `artifacts/tmp/blind_source_holdout_2026-05-20/round-3-rp-intermediary-disclosure/researcher`.
- `reading_plan.json` oeffnete u. a. `ec_ts05_rp_registration_api`, `ec_ts06_rp_information_set`, `eudi_discussion_topic_x_rp_registration`, `celex_32025R0848_fulltext_en` und weitere Kontextquellen.
- `final_answer.txt` enthielt zwar Quellenanker, war aber in der Kurzantwort roh und nur teilweise fragebezogen: Es begann mit allgemeinen Registration-Regeln und TS05-Details, nicht mit der fachlichen Trennung Wallet-Relying Party / Intermediaer / Zweck / Datenschutzinformation.
- Der Answer-Agent musste `opened_passages`, `evidence_synthesis_matrix`, `manual_review_report` und konkrete Korpusstellen nachlesen, um eine brauchbare Fachantwort zu synthetisieren.
- Die synthetisierte Antwort verlor dabei die sichtbaren Quellenanker; dadurch entstand im Blind Review der Hard Error.

Legacy-Agent:

- Der geplante Query-Pfad lief mit `contract_checks=pass`; kein Fallback war erforderlich.
- Die Legacy-Antwort war fachlich strukturierter und operationalisierte Nutzeranzeige/Registrierung besser.
- Auch Legacy brauchte laut Methodennotiz direkte lokale Lektuere, weil der erste Query-Lauf den Intermediaer-Aspekt nur teilweise traf.
- Auch die Legacy-Review-Antwort enthielt keine konkreten Quellen/Locators; dadurch derselbe Hard Error.

Limitation:

- Legacy hat keine aequivalenten Intermediate-Artefakte zu `reading_plan.json`, `opened_passages.json` oder `evidence_synthesis_matrix.json`; Pfadqualitaet ist daher asymmetrisch beobachtbar.
- In dieser Runde kommt eine zusaetzliche Protokoll-Limitation hinzu: Die Answer-Agenten wurden nicht hart genug angewiesen, Quellenanker in `answer_for_review` zu erhalten. Das machte die Blind-Review-Texte fuer beide Systeme schlechter traceable als die zugrunde liegenden Artefakte.

### Verbesserungsfolgerungen fuer EUBW-Researcher

Ausformuliert als Arbeitsauftrag:

- `docs/architecture/EUBW_ROUND3_INTERMEDIARY_SYNTHESIS_WORK_ORDER.md`

1. vNext braucht eine deutlich bessere erste Kurzantwort fuer Intermediaer-/RP-Registration-Fragen; die richtigen Quellen waren grob vorhanden, aber die Antwortoberflaeche begann mit unnuetzlichen Rohsaetzen.
2. Die Synthesis-Matrix sollte Intermediaer-Beziehung, End-Relying-Party, Intended Use, erlaubte Attribute und Privacy-/DPA-Information als eigene answer-ready Aussagen liefern.
3. Die automatisierte Review darf eine solche Kurzantwort nicht als `accept` bewerten, wenn sie die eigentliche Frage nur indirekt beruehrt.
4. Fuer weitere Holdout-Runden muss der Answer-Agent-Prompt explizit verlangen, dass `answer_for_review` konkrete Quellenanker/Locators enthaelt, ohne Repo-Pfade zu nennen.

### Zwischenstand nach Round 3

| Runde | Zaehlt? | Ergebnis Researcher | Grund |
| --- | --- | --- | --- |
| 1 | nein | verloren im Blind Review | Legacy-CLI lief urspruenglich nicht, daher Runtime-Confounder |
| 2 | ja | verloren | richtige Quelle im Katalog, aber nicht im Reading Plan; schwache Traceability |
| 3 | eingeschraenkt | beide Hard Error; Legacy inhaltlich vorn | beide Review-Antworten ohne Quellenpfad; Researcher-Final war traceable, aber roh und schlecht synthetisiert |
