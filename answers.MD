# Antworten zu den 5 EUBW-Fragen

Kurze Vorbemerkung: Alle fünf isolierten RAG-Läufe wurden mit frischen Subagents auf demselben fokussierten Real-Corpus-Katalog ausgeführt. Alle fünf Bundles sind reviewbar und enden in `manual_review_report.md` mit `accept`; zugleich enthält jedes `approved_ledger.json` nur **einen** freigegebenen Claim mit `final_claim_state: confirmed`, nämlich den Meta-Befund, dass für die jeweilige breite Frage zunächst hochrangige EU-Regulierung maßgeblich ist und nationales oder projektbezogenes Material erst nachrangig tragen soll. Die Antworten unten bleiben deshalb bewusst eng an den Artefakten und markieren die fachlichen Lücken ausdrücklich.

## 1. Welche Verantwortungsgrenzen sollten im EUBW-Ökosystem zwischen Wallet-Provider, Aussteller, Prüfer, Registerbetreiber und Vertrauensdiensteanbieter technisch und organisatorisch gezogen werden?

**Antwort**  
Auf Basis des erzeugten Bundles lässt sich derzeit nur belastbar festhalten, dass die Grenzziehung zuerst aus hochrangiger EU-Regulierung entwickelt werden muss. Eine konkrete technische und organisatorische Abgrenzung zwischen Wallet-Provider, Aussteller, Prüfer, Registerbetreiber und Vertrauensdiensteanbieter ist im freigegebenen `final_answer.txt` nicht actor-by-actor ausgearbeitet.

**Evidenzstatus**  
`approved_ledger.json`: `confirmed` = 1, keine `interpretive`-, `open`- oder `blocked`-Claims.  
`manual_review_report.md`: `accept`.  
`gap_records.json` und `web_fetch_records.json`: leer.

**Kernquellen**  
- `Regulation (EU) 2024/1183 amending Regulation (EU) No 910/2014`
- `Commission Implementing Regulation (EU) 2024/2982`
- `Commission Implementing Regulation (EU) 2025/848`
- `COM(2025)838 final EN proposal text (Part 1 PDF)`
- `COM(2025)838 final EN annex (Part 1 PDF)`

**Offene Punkte**  
- Keine belastbare Zuordnung der Verantwortlichkeiten je Rolle im finalen Bundle.
- Keine explizit protokollierten Gaps, obwohl die Sachantwort schmal bleibt.

**Artefakte**  
`/mnt/c/Users/Admin/Documents/GitHub/EUBW-Researcher/artifacts/manual_runs/eubw_five_questions_2026_04_20/01_responsibility_boundaries`

## 2. Wie sollte der Lebenszyklus organisatorischer Nachweise und Mandate im EUBW aussehen, wenn sich Registerdaten, Vertretungsrechte oder Unternehmensstatus ändern?

**Antwort**  
Der erzeugte Run liefert keine ausgearbeitete Zielbeschreibung für Ausstellung, Aktualisierung, Suspendierung, Widerruf oder Revalidierung organisatorischer Nachweise und Mandate. Belastbar bestätigt wird nur, dass die Antwort zuerst auf hochrangiger EU-Regulierung beruhen muss; der eigentliche Soll-Lebenszyklus wird im Bundle nicht fachlich ausformuliert.

**Evidenzstatus**  
`approved_ledger.json`: `confirmed` = 1, sonst keine weiteren Claim-States.  
`manual_review_report.md`: `accept`.  
`corpus_coverage_report.json`: `passed: true`.  
`gap_records.json` und `web_fetch_records.json`: leer.

**Kernquellen**  
- `Regulation (EU) 2024/1183 amending Regulation (EU) No 910/2014`
- `Commission Implementing Regulation (EU) 2025/848`
- `Commission Implementing Regulation (EU) 2024/2982`
- `Commission Implementing Regulation (EU) 2025/846`
- `Commission Implementing Regulation (EU) 2025/849`
- `COM(2025)838 final EN proposal text (Part 1 PDF)`
- `COM(2025)838 final EN annex (Part 1 PDF)`

**Offene Punkte**  
- Kein artefaktgestützter Soll-Prozess bei Änderungen von Registerdaten, Vertretungsrechten oder Unternehmensstatus.
- Keine explizit festgehaltenen Gaps trotz dünner Sachantwort.

**Artefakte**  
`/mnt/c/Users/Admin/Documents/GitHub/EUBW-Researcher/artifacts/manual_runs/eubw_five_questions_2026_04_20/02_lifecycle_of_credentials_and_mandates`

## 3. Welche Audit- und Ereignisspuren müssten für Streitfälle oder Compliance-Nachweise erhalten bleiben, ohne in eine unverhältnismäßige Vollprotokollierung abzugleiten?

**Antwort**  
Das freigegebene Bundle beantwortet die Frage nicht mit einer konkreten Liste von Audit- oder Ereignisspuren. Bestätigt wird nur der methodische Vorrang hochrangiger EU-Regelung. Welche Mindestereignisse, Belegfelder, Aufbewahrungsgrenzen oder Selektionsregeln gegen Vollprotokollierung erforderlich wären, bleibt artefaktseitig offen.

**Evidenzstatus**  
`approved_ledger.json`: `confirmed` = 1, keine weiteren Claim-States.  
`manual_review_report.md`: `accept`.  
`Discovery / gap-handling verdict`: `not_exercised`.  
`gap_records.json` und `web_fetch_records.json`: leer.

**Kernquellen**  
- `Regulation (EU) 2024/1183 amending Regulation (EU) No 910/2014`

**Offene Punkte**  
- Keine konkrete, freigegebene Minimalmenge an Audit- und Event-Spuren.
- Keine protokollierte Lückenbehandlung oder Web-Nachzüge.

**Artefakte**  
`/mnt/c/Users/Admin/Documents/GitHub/EUBW-Researcher/artifacts/manual_runs/eubw_five_questions_2026_04_20/03_audit_and_event_trails`

## 4. Wie sollte ein EUBW in einem grenzüberschreitenden Verfahren die Identität einer natürlichen Person sauber von ihrer Handlungsbefugnis für eine juristische Person trennen?

**Antwort**  
Aus dem erzeugten Bundle lässt sich nur belastbar ableiten, dass diese Trennung zuerst auf hochrangiger EU-Regelung gestützt werden müsste. Eine konkrete technische oder rechtliche Trennlogik zwischen Personenidentität und Handlungsbefugnis für eine juristische Person ist in den freigegebenen Artefakten nicht ausformuliert.

**Evidenzstatus**  
`approved_ledger.json`: `confirmed` = 1, keine weiteren Claim-States.  
`manual_review_report.md`: `accept`.  
`corpus_coverage_report.json`: `passed: true`.  
`gap_records.json` und `web_fetch_records.json`: leer.

**Kernquellen**  
- `Regulation (EU) 2024/1183 amending Regulation (EU) No 910/2014`
- `Commission Implementing Regulation (EU) 2024/2982`
- `COM(2025)838 final EN proposal text (Part 1 PDF)`
- `COM(2025)838 final EN annex (Part 1 PDF)`

**Offene Punkte**  
- Keine belastbare, artefaktgestützte Aussage zur Trennung von Identität und Vertretungsbefugnis.
- Keine protokollierten Gaps trotz sehr knapper Sachantwort.

**Artefakte**  
`/mnt/c/Users/Admin/Documents/GitHub/EUBW-Researcher/artifacts/manual_runs/eubw_five_questions_2026_04_20/04_identity_vs_authority_separation`

## 5. Welche Aussagen zur EUBW-Architektur lassen sich direkt aus Proposal und Annex ableiten, welche sind an spätere technische Spezifikationen delegiert, und welche bleiben derzeit nur plausible Architekturannahmen?

**Direkt aus Proposal und Annex ableitbar**  
Im freigegebenen Bundle ist keine belastbare Bucket-Zuordnung ausgearbeitet. Proposal und Annex sind zwar im Run-Korpus vorhanden, wurden im `approved_ledger.json` aber nicht als freigegebene Kernbelege für eine direkte Ableitung einzelner Architekturpunkte verwertet.

**An spätere technische Spezifikationen delegiert**  
Im freigegebenen Bundle gibt es keine separat freigegebenen Claims, die Delegation an spätere technische Spezifikationen explizit markieren oder systematisch auflisten.

**Plausible Architekturannahmen**  
Auch hierfür gibt es im `approved_ledger.json` keine gesondert freigegebenen Claims. `provisional_grouping.json` enthält lediglich die vorläufige Gruppe `Governance and discretion`, nicht aber eine belastbare Dreiteilung der Architekturaussagen.

**Evidenzstatus**  
`approved_ledger.json`: `confirmed` = 1, keine weiteren Claim-States.  
Der einzige freigegebene Claim bestätigt nur den Vorrang hochrangiger EU-Regulierung.  
`manual_review_report.md`: `accept`, aber `Human reviewed: false`.  
`gap_records.json` und `web_fetch_records.json`: leer.

**Kernquellen**  
- `Regulation (EU) 2024/1183 amending Regulation (EU) No 910/2014`

**Offene Punkte**  
- Keine artefaktgestützte Dreiteilung in `direkt ableitbar`, `delegiert` und `plausible Annahme`.
- Proposal/Annex, Implementing Acts und technische Spezifikationen sind im Korpus abgedeckt, wurden aber nicht in diese Buckets überführt.

**Artefakte**  
`/mnt/c/Users/Admin/Documents/GitHub/EUBW-Researcher/artifacts/manual_runs/eubw_five_questions_2026_04_20/05_architecture_claim_buckets`
