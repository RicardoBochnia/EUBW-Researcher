# Qualitätsvergleich: Kollegenbriefing PID-/Device-Binding, Imma, Rulebooks

Stand: 2026-05-11.

Verglichene Antworten:

- Legacy EUBW: `/mnt/c/Users/Admin/PycharmProjects/EUBW/docs/generated/2026-05-12_termin_imma_studierendenausweis.md`
- EUBW-Researcher, alter Pfad: `docs/research/2026-05-11_kollegenbriefing_pid_device_binding_imma_rulebooks.md`
- EUBW-Researcher, Knowledge-Service-Pfad: `docs/research/2026-05-11_kollegenbriefing_pid_device_binding_imma_rulebooks_knowledge_service.md`

## Kurzfazit

Die Legacy-EUBW-Antwort ist fachlich weiterhin die stärkste Antwort. Sie ist
begrifflich vorsichtiger, quellenpräziser und erklärt die entscheidenden
technischen Unterschiede besser, insbesondere bei `PID Binding`, Batch Issuance
und kryptographischem Binding.

Der neue Knowledge-Service-Pfad ist innerhalb von EUBW-Researcher klar besser
als der alte Pfad: Er hat die relevanten Quellen in den kuratierten Korpus
nachgezogen, dokumentiert die tatsächlichen assistive-Runs und liefert eine
terminfreundliche Antwortstruktur. Er erreicht aber noch nicht ganz die
Legacy-Qualität, weil die Antwortprosa weniger claim-/abschnittsgenau zitiert
und die stärksten Evidence-Artefakte noch nicht automatisch in eine
prüffreundliche Quellenargumentation übersetzt.

Der alte EUBW-Researcher-Pfad ist inhaltlich brauchbar, aber am schwächsten
reproduzierbar: Er erkennt selbst, dass wichtige Quellen zwar im Archiv, aber
noch nicht im kuratierten Katalog waren. Der Knowledge-Service-Pfad behebt
genau diesen Punkt teilweise.

## Ranking

1. Legacy EUBW: beste fachliche Tiefe und beste epistemische Vorsicht.
2. EUBW-Researcher Knowledge Service: beste Researcher-Variante, gute
   Terminform, bessere Korpus-/Run-Transparenz.
3. EUBW-Researcher alter Pfad: gute Synthese, aber schwächere
   Reproduzierbarkeit und geringere Quellenintegration.

## Vergleich Nach Kriterien

### Fachliche Präzision

Legacy gewinnt hier deutlich. Die Antwort klärt früh, dass `PID Binding` kein
scharfer Normbegriff im Corpus ist, und übersetzt ihn explizit als
attribute-/subject-binding an PID. Das verhindert eine Begriffsverwechslung mit
cryptographic/device binding. Außerdem nennt Legacy für Batch Issuance die
wichtige Grenze: gleiche Attestation Type, gleiche Attributwerte und gleiche
technische Gültigkeit; unterschiedliche Studiengänge gehören daher nicht in
einen Batch.

Der Knowledge-Service-Pfad ist fachlich im Ergebnis nicht falsch, aber stärker
verdichtet. Die Formulierung "PID muss kryptographisch an die Wallet Unit
gebunden sein" ist für eine Kurzantwort nützlich, aber weniger sauber als die
Legacy-Trennung zwischen PID-/Attribut-Binding, Präsentations-Binding und
kryptographischem Binding.

### Quellenbindung und Prüfbarkeit

Legacy nennt Claim-IDs, Source-IDs und konkrete Abschnitte/Artikel direkt im
Detailteil. Das ist für Review und Wiederverwendung sehr stark.

Der Knowledge-Service-Pfad dokumentiert die Runtime-Basis besser als der alte
Researcher-Pfad: Er nennt die assistive-Läufe, die zusätzlich fokussierten
Läufe und die Korpus-Ergänzung um CIR 2024/2977, CIR 2024/2979 und CIR
2025/1569. Zusätzlich existieren im Repo die neuen Artefakte
`evidence_clusters.json`, `claim_verification.json` und
`manual_review_report.md`. In der Antwort selbst fehlen aber noch häufig
Claim-IDs, exakte Locator-Angaben und direkte Verweise pro Aussage.

Der alte Researcher-Pfad enthält zwar eine gute Quellenliste, markiert aber
selbst, dass CIR 2025/1569 nur im Archiv und nicht im kuratierten Katalog war.
Das macht den Lauf schlechter reproduzierbar.

### Termin-Tauglichkeit

Beide Researcher-Antworten sind für den 20-Minuten-Termin sehr gut nutzbar,
weil sie zuerst drei Kurzantworten liefern und danach Details, Lücken und eine
Gesprächsformulierung anbieten.

Der Knowledge-Service-Pfad ist hier leicht besser als der alte Researcher-Pfad:
Er ist kompakter, trennt Laufbasis und Quellen klarer und nennt die
Deutschland-/BAföG-Lücke direkt bei der betreffenden Frage. Die Legacy-Antwort
ist ebenfalls gut strukturiert, aber etwas dichter und weniger "fertig
sprechbar".

### Frage 1: PID vs. Device Binding Bei PID-Batches

Legacy ist am stärksten. Sie bringt drei Punkte, die in den Researcher-Antworten
weniger deutlich sind:

- `PID Binding` ist terminologisch unscharf und muss im Termin geklärt werden.
- Batch Issuance setzt gleiche fachliche Werte voraus; mehrere Studiengänge
  sind deshalb keine Batch-Variante, sondern getrennte Credentials oder
  unterscheidbare Attribute.
- Kryptographisches Binding kann bei kombinierten Präsentationen
  privacy-preserving sein, weil nicht zusätzliche PID-/Namensattribute gezeigt
  werden müssen.

Der Knowledge-Service-Pfad liefert die bessere Kurzfassung für einen Termin,
verliert aber gegenüber Legacy technische Nuancen.

### Frage 2: Richtige Immatrikulationsbescheinigung

Alle drei Antworten sind in der Kernaussage sehr nah beieinander: Die RP bzw.
das Fachverfahren muss die fachliche Query definieren; die Wallet darf nicht
raten.

Legacy ist quellenstärker, weil sie RP-Verantwortung, RPRC, intended use und
general access policy mit konkreten Norm-/Claim-Ankern belegt. Der
Knowledge-Service-Pfad ergänzt dafür eine gute technische Nuance: DCQL
`multiple`, Value Matching und die Warnung, dass Value Matching nicht blind zur
Sicherheitsentscheidung werden darf.

### Frage 3: Rulebook-Feldbeschreibungen und Sprache

Legacy ist normativ am stärksten: CIR 2025/1569, TS11 `name`/`description`,
URI-Identifier, semanticDataSpecification und Rulebooks als human-readable
Governance-Ort werden sauber belegt.

Der Knowledge-Service-Pfad ist praktisch am besten als Checkliste: Er ergänzt
Binding-Regeln, Kapitelstruktur des Rulebook-Templates, SD-JWT-VC Claim Names,
Selective Disclosure und Kapitel-4-Aussagen zu device-bound/non-device-bound.

Die beste Zielantwort sollte beide Stärken verbinden: Legacy-Quellenpräzision
plus Knowledge-Service-Template-/Praxischeckliste.

## Auffällige Unterschiede

- Legacy bewahrt Unsicherheit stärker: Es markiert `PID Binding` als zu
  klärenden Begriff und formuliert offen, wo keine A-tier-Quelle existiert.
- Knowledge Service verbessert den Korpus aktiv: Quellen, die vorher nur im
  Archiv lagen, wurden in den kuratierten Katalog übernommen.
- Knowledge Service belegt den Rechercheprozess besser über Artefakte, aber
  nicht automatisch besser in der finalen Prosa.
- Alter Researcher-Pfad und Knowledge-Service-Pfad sind inhaltlich sehr
  ähnlich; der Qualitätssprung kommt eher aus Korpus-/Run-Basis und
  Zusatzläufen als aus sichtbar anderer Antwortkomposition.
- Die Knowledge-Service-Datei nutzt ASCII-Umschreibungen (`fuer`, `BAfoeG`).
  Das ist fachlich egal, wirkt aber für eine direkte Weitergabe weniger
  polished als die alte Researcher-Datei mit Umlauten.

## Architektur-/Migrationsimplikation

Der Knowledge Service hilft bereits dort, wo er helfen soll: relevante Quellen
finden, Lücken sichtbar machen, Korpuslücken schließen und Evidence-Artefakte
erzeugen. Er löst aber noch nicht automatisch das eigentliche Qualitätsproblem
der finalen Antwort: Die stärksten Evidence-Cluster und Verification Records
müssen in claim-nahe, abschnittsgenaue und caveat-stabile Antwortbausteine
übersetzt werden.

Für Phase 8 oder die nächste Umsetzungsschleife wäre daher wichtiger als ein
weiterer Intent:

- Composer soll pro Kernaussage Claim-/Source-/Locator-Verweise einweben
  können.
- Begriffsklärungen aus Evidence-Clustern müssen priorisiert werden, wenn der
  Nutzer mehrdeutige Begriffe verwendet.
- Review-Gates sollten nicht nur "Antwort akzeptabel" prüfen, sondern auch:
  Wurde eine relevante Unsicherheit aus dem Corpus in die Kurzantwort
  übernommen?
- Knowledge-Service-Läufe sollten sichtbar machen, welche Quellen neu in den
  Korpus aufgenommen wurden und welche Antwortaussagen davon abhängen.
- Für terminfertige Dokumente sollte die Ausgabequalität, inklusive deutscher
  Umlaute und Zitierstil, bewusst behandelt werden.

## Bewertung

Der neue Knowledge-Service-Pfad ist ein echter Fortschritt gegenüber dem alten
Researcher-Pfad, aber noch kein Gleichstand mit Legacy EUBW. Der Abstand ist
nicht mehr primär Retrieval, sondern Antwortkomposition: Legacy macht aus der
Evidenz eine bessere fachliche Argumentation, während Researcher die Evidenz
inzwischen findet und prüfbarer ablegt, sie aber noch zu wenig präzise in der
Antwortprosa nutzt.
