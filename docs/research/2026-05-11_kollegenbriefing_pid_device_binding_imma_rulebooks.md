# Briefing: PID-/Device-Binding, Immatrikulationsnachweise und Rulebooks

Stand: 2026-05-11. Zweck: Vorbereitung eines 20-Minuten-Termins am 2026-05-12.

## Kurzantworten

### 1. PID vs. Device Binding bei PID-Batches

Für die PID selbst ist die Lage in den aktuellen EUDI-Spezifikationen relativ hart: Bei PID-Ausstellung soll die PID an einen Schlüssel gebunden werden, der aus einer Wallet Unit Attestation (WUA) stammt und dessen Key Storage ein WSCD ist. Für Immatrikulationsbescheinigung und Studierendenausweis ist die Wahl dagegen eine Rulebook-/Use-Case-Entscheidung: claim-/PID-gebunden, device-/key-gebunden oder hybrid.

Für eine Immatrikulationsbescheinigung spricht viel für eine fachlich saubere Personen- und Studiengangsbindung über PID-/Subject-Matching plus eindeutige Studiengangsattribute. Reines Device Binding erhöht zwar Diebstahl- und Weitergabeschutz, macht aber Gerätewechsel, Re-Issuance und Statusketten aufwendiger.

Für einen Studierendenausweis ist Device-/Key-Binding attraktiver, weil der Nachweis häufig und in niedrigschwelligen Situationen präsentiert wird und nicht einfach weitergegeben werden soll. Wenn aber dieselbe Credential oder dieselben stabilen PID-Claims immer wieder präsentiert werden, ist der Privacy-Gewinn von Batch Issuance schnell weg; deshalb sollten Student-ID-Batches möglichst unterschiedliche kryptographische Daten/Schlüssel verwenden und nur minimale Statusattribute enthalten.

### 2. Wer konzipiert die Abfrage der richtigen Immatrikulationsbescheinigung?

Die fachliche Query muss die Relying Party bzw. der Fachverfahrensverantwortliche konzipieren, hier also der BAföG-Prozess bzw. die Stelle, die rechtlich und fachlich weiß, welche Immatrikulation für den Antrag relevant ist. Die Wallet sollte nicht raten, welcher Studiengang "der richtige" ist.

Die Credential-/Rulebook-Seite muss aber die dafür nötigen Attribute liefern: z. B. Hochschule, Studiengang, Abschlussziel, Fachsemester/Zeitraum, Status, ggf. Programm-/Studiengangs-ID und Gültigkeit. Die Wallet setzt die Anfrage technisch um, prüft Registrierung/Overasking, zeigt dem Nutzer den Zweck und lässt bei mehreren passenden Credentials ggf. auswählen; sie definiert aber nicht die BAföG-Fachregel.

Wenn zwei Immatrikulationsbescheinigungen in der Wallet liegen und die BAföG-RP nur "eine gültige Immatrikulationsbescheinigung" abfragt, ist die Anfrage fachlich zu unscharf. Dann muss entweder die RP präziser fragen oder das Verfahren bewusst eine Nutzerwahl akzeptieren.

### 3. Feldbeschreibungen für grenzüberschreitende Credentials im Rulebook

Nicht nur an der IANA-JWT-Claim-Liste orientieren. IANA ist nützlich für generische JWT-/JOSE-/OIDC-Claims, aber die fachliche Semantik grenzüberschreitender Credentials soll über Attestation Rulebooks, Attestation Schemas, Kataloge, Namespaces und stabile Identifier laufen.

Der robuste Aufbau ist: Rulebook in Englisch als normative Basissprache, zusätzlich sprachgetaggte Anzeigenamen/Beschreibungen für Nutzer; pro Attribut ein stabiler Data Identifier, Definition, Datentyp, Beispiel, Kardinalität, Offenlegbarkeit, Rechtsgrundlage/Trust-Modell und ggf. Verweis auf den Catalogue of Attributes. Für SD-JWT VC: VCT und Claim-Namen sauber definieren; für mdoc: DocType, Namespace und Attribute Identifier.

Ich habe keine belastbare Quelle gefunden, die pauschal sagt: "Alle Rulebooks im EU-Raum müssen vollständig auf Englisch geschrieben sein." Die technischen Vorgaben gehen aber klar in diese Richtung: Attributnamen müssen mindestens eine englische Default-Bezeichnung haben; Beschreibungen sollten mindestens Englisch enthalten; maschinenlesbare Kataloge und Rulebook-URIs machen die Semantik RP-tauglich.

## Detailnotizen

### Quellenbasis und Lücken

Genutzte Repo-Quellen:

- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-28_ec_ts03_wallet_unit_attestation.md` - WIA/WUA, Key Attestation, Batch-Schlüssel, PID-WSCD-Binding.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-06_openid4vci_1_0.html` - OpenID4VCI, Batch Credential Issuance, Key Attestation.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-07_openid4vp_1_0.html` - OpenID4VP, DCQL, mehrere Credentials, Consent/Error-Fälle.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-30_ec_ts05_rp_registration_api.md` und `SRC-W-TEC-31_ec_ts06_rp_information_set.md` - RP-Registrierung, Intended Use, Data Requested.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-36_ec_ts11_catalogues.md` - Catalogue of Attributes, Catalogue of Attestations, Attestation Rulebooks, SchemaMeta.
- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-02/SRC-L-02_32024R1183_DOC_1_en.xhtml` - eIDAS 2.0 / Regulation (EU) 2024/1183.
- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-36/SRC-L-36_32025R0848_DOC_1_en.xhtml` - CIR 2025/848 zur Wallet-RP-Registrierung.
- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-41/SRC-L-41_32025R1569_DOC_1_en.xhtml` - CIR 2025/1569 zu EAA, Catalogue of Attributes und Catalogue of Schemes. Achtung: im Archiv vorhanden, aber nicht im aktuell kuratierten Katalog gelistet.

Ergänzend per Web geprüft:

- [OpenID4VCI 1.0](https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html) und [OpenID4VP 1.0](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html).
- [Commission Implementing Regulation (EU) 2025/1569](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R1569).
- [Commission Implementing Regulation (EU) 2025/848](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R0848).
- [EUDI ARF latest, Abschnitt 5.5](https://eudi.dev/latest/architecture-and-reference-framework-main/).
- [Attestation Rulebooks Catalog](https://github.com/eu-digital-identity-wallet/eudi-doc-attestation-rulebooks-catalog) und aktuelles Template `attestation-rulebook-template.md` (v1.4 vom 2026-03-09).
- [Offizielle deutsche EUDI-Wallet-Hintergrundseite](https://eudi-wallet.gov.de/app/hintergrund), [deutscher Blueprint](https://bmi.usercontent.opencode.de/eudi-wallet/eidas-2.0-architekturkonzept/) und [Architekturdokumentation der deutschen staatlichen Wallet](https://bmi.usercontent.opencode.de/eudi-wallet/wallet-development-documentation-public/latest/).

Wichtige Lücken:

- Kein finaler deutscher Rulebook-/Schema-Stand für Immatrikulationsbescheinigung oder Studierendenausweis im Korpus gefunden.
- Kein BAföG-spezifischer Nachweiskatalog im Korpus gefunden.
- Die deutsche öffentliche Architektur-Dokumentation sagt derzeit selbst, dass der Fokus auf PID-Funktion, Online Issuance/Presentation und Wallet-Core-Funktionen liegt; EAA/QES-Funktionen kommen später. Der deutsche Blueprint ist Diskussions- und Designbasis, nicht finale bindende Spezifikation.

### 1. PID-, Claim- und Device-Binding sauber trennen

Begriffe für den Termin:

- PID ist Person Identification Data. TS11 merkt ausdrücklich an, dass PID nicht einfach eine normale Attestation ist.
- Device-/Key-Binding bedeutet: Die Credential wird an kryptographische Schlüssel gebunden, deren Schutz über WUA/Key Attestation nachgewiesen wird.
- Claim-/PID-Binding bedeutet: Die Attestation wird fachlich an eine Person bzw. an eine andere Credential wie PID gebunden, etwa durch Subject-Identifier, PID-Co-Presentation oder ein Rulebook-Feld wie `cryptographically_bound_to`.
- Batch Issuance bedeutet bei OpenID4VCI: mehrere Credentials in einem Request, gleicher Credential Dataset, aber unterschiedliche kryptographische Daten. Das kann Unlinkability unterstützen, wenn nicht gleichzeitig stabile eindeutige Personen- oder Credentialwerte offengelegt werden.

Bewertung je Use Case:

| Thema | PID-/Claim-Binding | Device-/Key-Binding |
|---|---|---|
| Immatrikulationsbescheinigung | Gut, wenn BAföG/Hochschule die Person und den konkreten Studiengang fachlich prüfen muss. Besser für Gerätewechsel und langfristige Verwaltungsprozesse. Risiko: mehr identifizierende Daten, Batch bringt wenig Privacy, wenn stabile PID-Daten offengelegt werden. | Gut bei hohem Missbrauchsrisiko oder wenn Weitergabe verhindert werden soll. Nachteil: Re-Issuance, Statusprüfung, Geräteverlust und Migration werden aufwendiger. |
| Studierendenausweis | Nur sinnvoll, wenn die RP wirklich Personenidentität braucht. Für Mensa, Rabatte, Bibliothek oft zu viel. Risiko: Overdisclosure und Linkability. | Attraktiv für "ist aktuell Student" mit minimalen Attributen. In Kombination mit Batch/Einmal-Credentials besser gegen Weitergabe und gegen Verifier-zu-Verifier-Linkability. |

Praktische Empfehlung:

- Imma-Nachweis: Schema/Rulebook so bauen, dass Studiengang und Gültigkeitszeitraum eindeutig querybar sind; PID nur dann mitgeben oder co-präsentieren, wenn die RP die rechtliche Identität wirklich braucht.
- Student-ID: so wenig personenbezogene Attribute wie möglich; besser Status-/Berechtigungsnachweis als vollständige Imma-Bescheinigung. Wenn häufige Präsentation erwartet wird, Batch/one-per-presentation und Key-Binding prüfen.
- Hybrid ist möglich: Eine Attestation kann device-bound sein und zusätzlich an PID bzw. einen PID-Typ auf derselben Wallet Unit gebunden werden. Das sollte aber im Rulebook ausdrücklich stehen, nicht implizit in der Wallet-UI entstehen.

### 2. "Richtige" Immatrikulationsbescheinigung: Verantwortlichkeit

Die Verantwortung ist geteilt, aber nicht beliebig:

- RP/Fachverfahren: definiert Zweck, Rechtsgrundlage, Datenminimum und die fachliche Regel. Bei BAföG wäre das der zuständige BAföG-/Fachverfahrenskontext, nicht der Wallet Provider.
- RP-Registrierung: muss Intended Use und Data Requested abbilden. Die EU-RP-Regelung zielt gerade darauf, dass Wallet-Nutzer sehen können, welche Daten die RP für welchen Zweck verlangen darf.
- Attestation Rulebook / Schema Provider: muss die Attribute so modellieren, dass die RP die Fachregel überhaupt ausdrücken kann.
- Issuer, z. B. Hochschule oder beauftragte Stelle: muss die Attribute korrekt ausstellen und Status/Gültigkeit pflegen.
- Wallet: wertet die technische Anfrage aus, zeigt Zweck und Daten an, verhindert oder warnt bei Overasking, holt Consent ein und kann dem Nutzer bei mehreren Treffern eine Auswahl geben. Sie ist nicht die Instanz, die BAföG-Fachlogik erfindet.

Technisch passt dazu OpenID4VP/DCQL:

- Der Verifier kann Credential-Typ, Format, Claims, Trusted Authorities und Kombinationen von Credentials/Claims abfragen.
- Das Feld `multiple` entscheidet, ob mehrere Credentials für eine Credential Query zurückgegeben werden können; ohne Angabe ist der Default `false`.
- Wenn mehrere Imma-Credentials passen, muss die Query entweder präziser sein oder die Wallet muss eine Nutzerentscheidung ermöglichen. "Nimm schon die richtige" ist keine interoperable Anforderung.

Minimal sinnvolle Attribute für eine Imma-Credential:

- Hochschule/Issuer und Trust Anchor.
- Status: eingeschrieben, beurlaubt, exmatrikuliert, etc.
- Gültigkeitszeitraum/Semester.
- Studiengangs-ID oder Programm-ID, Abschlussziel, ggf. Fachsemester.
- Person-/Subject-Bezug, idealerweise so, dass die RP nicht mehr PID-Daten bekommt als nötig.
- Status-/Revocation-Mechanismus.

Offener Punkt für Deutschland:

Für BAföG müsste noch geklärt werden, welche Stelle die fachliche Nachweisdefinition normiert: Gesetz/Verordnung, Verwaltungsvorschrift, Fachverfahrensbetreiber, Länder-/Hochschulregister oder ein EAA-Rulebook. Diese Quelle ist im Korpus nicht belegt.

### 3. Rulebook-Feldbeschreibungen: Konventionen

TS11 und das Rulebook-Template liefern zusammen eine brauchbare Konvention:

1. Encoding-unabhängig in Kapitel 2 definieren:
   - `Data Identifier`
   - `Definition`
   - `Data type`
   - `Example value`
   - mandatory/optional/conditional
   - ggf. Metadata vs. Attribute

2. Danach formatabhängig mappen:
   - mdoc: Attribute Identifier, Encoding Format, Namespace, DocType.
   - SD-JWT VC: VCT, Claim Name, Encoding Format, Notes, Selective Disclosure.
   - W3C VC: nur für non-qualified EAA sinnvoll, wenn im Profil zugelassen.

3. Für SD-JWT VC gilt laut aktuellem Template:
   - Claim Name ist entweder in der IANA JWT Claims Registry enthalten,
   - oder ein Public Name im Sinne von RFC 7519,
   - oder ein Private Name spezifisch für diesen Attestation Type.
   - Für jeden Claim muss angegeben werden, ob er selektiv offenlegbar sein muss, sein darf oder nicht sein darf.

4. Für grenzüberschreitende Semantik braucht jedes Feld:
   - stabilen Identifier, möglichst URI-basiert,
   - Namespace und Version,
   - englische Default-Bezeichnung,
   - englische Beschreibung, lokale Übersetzungen optional/zusätzlich,
   - Datentyp, Format, Wertebereich, Kardinalität,
   - Rechtsgrundlage, idealerweise ELI-URI,
   - Authentic Source oder Issuer-/Trust-Modell,
   - Status-/Revocation-Aussage,
   - Hinweise zu Device-/PID-Binding und Selective Disclosure.

5. Englisch-Frage:
   - Der Catalogue of Attributes verlangt mindestens eine englische Default-Bezeichnung für `name`.
   - Die Beschreibung sollte mindestens Englisch enthalten; zusätzliche Lokalisierungen können mit Language Tags ergänzt werden.
   - RP-Intended-Use-/Service-Beschreibungen sind dagegen nutzerseitig zu lokalisieren, insbesondere für die Mitgliedstaaten, in denen der Service angeboten wird.
   - Eine harte, allgemeine Pflicht "jedes Rulebook vollständig nur auf Englisch" habe ich nicht gefunden. Für Cross-Border-Interoperabilität sollte aber Englisch als normative Basissprache gesetzt werden, weil RPs sonst zwar Maschinen-Identifier sehen, aber die nicht-maschinenlesbare Governance schwer prüfen können.

### Gesprächsformulierung für die 20 Minuten

Wenn es kurz werden muss:

> Bei PID selbst ist Device-/WSCD-Binding im aktuellen EUDI-Bild stark vorgezeichnet. Für Imma und Studierendenausweis ist die richtige Antwort aber nicht "immer PID" oder "immer Device", sondern: Was muss die RP beweisen, wie oft wird präsentiert, wie hoch ist Missbrauchsrisiko und wie stark darf Linkability sein? BAföG muss seine Fachquery definieren; die Wallet darf nicht raten. Rulebooks sollten die Attribute englisch und maschinenlesbar sauber definieren, mit stabilen URIs/Namespaces, Datentypen, Semantik, Binding, Trust und Disclosure-Regeln; IANA-JWT ist nur ein Teil der Namenskonventionen.

