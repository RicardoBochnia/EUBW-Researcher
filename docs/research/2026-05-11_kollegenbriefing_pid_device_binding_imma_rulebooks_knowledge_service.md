# Briefing fuer 20-Minuten-Termin: PID-/Device-Binding, Immatrikulationsnachweise und Rulebooks

Stand: 2026-05-11. Ziel: erst drei kurze Antworten, danach Details und Quellen.

## Kurzantworten

### 1. PID vs. Device Binding bei PID-Batches

Fuer die PID selbst ist die Richtung im aktuellen EUDI-Regelwerk hart: PID muss kryptographisch an die Wallet Unit gebunden sein. Der PID Provider muss vor der Ausstellung die Wallet Unit Attestation authentifizieren und validieren. Bei Batch Issuance heisst das technisch: mehrere Credentials koennen denselben Credential Dataset haben, sollten aber unterschiedliche kryptographische Daten bzw. Schluessel nutzen.

Fuer Immatrikulationsbescheinigungen ist die bessere Primaerbindung meist fachlich: Person plus konkreter Studiengang, Hochschule, Status und Gueltigkeitszeitraum. Reines Device-/Key-Binding verhindert Weitergabe besser, erhoeht aber Aufwand bei Geraetewechsel, Re-Issuance, Sperrung und Statusketten. Wenn die Bescheinigung ohnehin stabile Personen- oder Studiengangsdaten offenlegt, bringt ein Batch allein wenig Privacy.

Fuer einen Studierendenausweis ist Device-/Key-Binding attraktiver als bei einer Verwaltungsbescheinigung: Der Ausweis wird haeufig und niedrigschwellig vorgelegt, und Weitergabe soll erschwert werden. Gleichzeitig sollte der Ausweis moeglichst wenig PID enthalten, eher "ist aktuell Student" bzw. "hat Berechtigung X"; fuer haeufige Praesentationen sind Batch-/Einmal- oder per-Verifier-Credentials mit unterschiedlichen Schluesseln sinnvoller.

### 2. Wer konzipiert die Abfrage der "richtigen" Immatrikulationsbescheinigung?

Die fachliche Query muss die Relying Party bzw. der Fachverfahrensverantwortliche konzipieren, also im Beispiel der BAfoeG-Prozess, nicht die Wallet. Die Wallet darf nicht raten, welcher von zwei Studiengaengen "der richtige" fuer BAfoeG ist.

Die Credential-/Rulebook-Seite muss aber die noetigen Attribute bereitstellen: Hochschule, Studiengangs-/Programm-ID, Abschlussziel, Fachsemester, Status, Semester/Gueltigkeitszeitraum, Issuer/Trust Anchor und ggf. Subject-/PID-Bezug. Die Wallet setzt die technische Anfrage um, prueft Registrierung/Zweckbindung/Overasking, zeigt dem Nutzer Zweck und Daten an und kann bei mehreren passenden Credentials Auswahl ermoeglichen.

Wenn die RP nur "eine gueltige Immatrikulationsbescheinigung" anfragt und mehrere passen, ist die Anfrage fachlich zu unscharf. Dann muss die RP praeziser fragen, z. B. nach Studiengang, Zeitraum oder Foerderkontext, oder das Verfahren muss bewusst akzeptieren, dass der Nutzer eine passende Credential auswaehlt.

### 3. Feldbeschreibungen fuer grenzueberschreitende Credentials im Rulebook

Nicht nur an der IANA-JWT-Claim-Liste orientieren. IANA ist fuer generische JWT-/OIDC-Claim-Namen nuetzlich, aber die fachliche Semantik grenzueberschreitender Credentials gehoert in Attestation Rulebooks, Attribute-/Scheme-Kataloge, stabile Namespaces, Identifier, Versionen und maschinenlesbare Schemas.

Der robuste Aufbau ist: Rulebook mit englischer normativer Basissprache; pro Feld ein stabiler Data Identifier, Definition, Datentyp, Beispiel, Kardinalitaet, Disclosure-Regel, Rechtsgrundlage, Trust-/Issuer-Modell, Status-/Revocation-Aussage und ggf. Binding-Regel. Fuer SD-JWT VC: `vct`, Claim Name und Selective Disclosure sauber definieren. Fuer mdoc: DocType, Namespace, Attribute Identifier und Encoding Format.

Ich habe keine harte allgemeine EU-Regel gefunden, dass jedes Rulebook vollstaendig auf Englisch geschrieben sein muss. Die Konvention geht aber klar dahin: mindestens englische Default-Namen/Beschreibungen fuer Katalogeintraege, zusaetzliche Lokalisierungen mit Language Tags, und fuer RPs eine englische, stabile, maschinen- und menschenlesbare Semantik.

## Detailnotizen

### Quellen- und Laufbasis

Der Knowledge Service wurde mit `configs/runtime.knowledge_assistive.yaml` gegen den realen Korpus ausgefuehrt. Die drei Hauptlaeufe liegen hier:

- `artifacts/tmp/kollegen_termin_2026-05-12/q1_pid_device_binding_v2`
- `artifacts/tmp/kollegen_termin_2026-05-12/q2_richtige_immabescheinigung_v2`
- `artifacts/tmp/kollegen_termin_2026-05-12/q3_field_descriptions_rulebooks_v2`

Zusaetzliche fokussierte Laeufe:

- `artifacts/tmp/kollegen_termin_2026-05-12/aux_pid_wua_binding`
- `artifacts/tmp/kollegen_termin_2026-05-12/aux_batch_wua_device_binding`
- `artifacts/tmp/kollegen_termin_2026-05-12/aux_rp_intended_use_multiple_credentials`
- `artifacts/tmp/kollegen_termin_2026-05-12/aux_rulebook_attributes_language`

Corpus-Ergaenzung: Drei im lokalen Archiv vorhandene, aber nicht im kuratierten Standardkatalog enthaltene Quellen wurden in `configs/real_corpus_selection.yaml` aufgenommen und `artifacts/real_corpus/curated_catalog.json` wurde neu gebaut: CIR 2024/2977 zu PID/EAA, CIR 2024/2979 zu Wallet-Integritaet/Core-Funktionen und CIR 2025/1569 zu QEAAs/PuB-EAAs sowie Attribute-/Scheme-Katalogen. Danach wurde `configs/terminology.yaml` neu generiert.

### 1. PID-, Claim- und Device-Binding sauber trennen

Wichtige Begriffe:

- PID = Person Identification Data, also der digitale Identitaetsdatensatz.
- Device-/Key-Binding = eine Credential ist an kryptographische Schluessel gebunden, deren Schutz ueber WUA/Key Attestation nachgewiesen wird.
- PID-/Claim-Binding = eine Attestation ist fachlich an eine Person oder eine andere Credential gebunden, z. B. durch Subject-Matching, Co-Presentation einer PID oder ein Rulebook-Feld wie `cryptographically_bound_to`.
- Batch Issuance = mehrere Credentials in einem Request. OpenID4VCI sagt: gleicher Credential Format und Credential Dataset, aber unterschiedliche kryptographische Daten; das kann Unlinkability unterstuetzen.

Bewertung je Use Case:

| Use Case | PID-/Claim-Binding | Device-/Key-Binding |
|---|---|---|
| Immatrikulationsbescheinigung | Gut, wenn die RP rechtliche Identitaet und konkreten Studiengang pruefen muss. Besser fuer Verwaltungsprozesse, Nachvollziehbarkeit und Geraetewechsel. Risiko: mehr identifizierende Daten und Linkability. | Gut bei hohem Missbrauchsrisiko. Nachteil: Geraetewechsel, Verlust, Re-Issuance und Revocation werden komplexer. |
| Studierendenausweis | Nur dann gut, wenn die RP wirklich Personenidentitaet braucht. Fuer Mensa, Bibliothek oder Rabatt ist das oft zu viel. | Gut fuer minimalen Berechtigungsnachweis. In Kombination mit Batch/Einmal-Credentials besser gegen Weitergabe und Verifier-zu-Verifier-Linkability. |

Praktische Empfehlung:

- Imma-Nachweis: fachlich eindeutig modellieren; PID oder PID-Bezug nur dort offenlegen, wo der Prozess das wirklich braucht.
- Student-ID: nicht als vollstaendige Imma-Bescheinigung missbrauchen; lieber minimaler Status-/Berechtigungsnachweis.
- Hybrid explizit im Rulebook definieren: device-bound Credential plus optionale Bindung an PID bzw. an einen PID-Typ auf derselben Wallet Unit.

### 2. "Richtige" Immatrikulationsbescheinigung

Rollenbild:

- RP/Fachverfahren: definiert Zweck, Rechtsgrundlage, Datenminimum und fachliche Selektionsregel.
- Registrar/RP-Registrierung: macht Intended Use und Datenumfang pruefbar.
- Rulebook-/Schema-Provider: modelliert die Attribute so, dass die fachliche Regel ausdrueckbar ist.
- Issuer, z. B. Hochschule: stellt die Daten korrekt aus und pflegt Status/Gueltigkeit.
- Wallet: prueft technische Anfrage, Registrierung, Zweck und Consent; sie entscheidet nicht die BAfoeG-Fachlogik.

OpenID4VP/DCQL passt dazu: Der Verifier beschreibt Credential-Typ, Format, Claims, Wertebedingungen und akzeptierte Trust Authorities. `multiple` bestimmt, ob mehrere Credentials fuer dieselbe Credential Query zurueckgegeben werden duerfen; ohne Angabe ist der Default `false`. Value Matching ist hilfreich fuer UX/Privacy, aber der Verifier darf sich fuer Sicherheitsentscheidungen nicht blind darauf verlassen.

Minimal sinnvolle Attribute fuer eine Imma-Credential:

- Issuer/Hochschule und Trust Anchor.
- Status, z. B. eingeschrieben, beurlaubt, exmatrikuliert.
- Semester bzw. Gueltigkeitszeitraum.
- Studiengangs-/Programm-ID, Abschlussziel, ggf. Fachsemester.
- Subject-/PID-Bezug, moeglichst datensparsam.
- Status-/Revocation-Mechanismus.

Offene Deutschland-/BAfoeG-Luecke: Im Korpus und in der kurzen Webpruefung habe ich keinen finalen BAfoeG-spezifischen Nachweiskatalog und kein finales deutsches Rulebook fuer Immatrikulationsbescheinigung oder Studierendenausweis gefunden. Zu klaeren bleibt, wer fachlich normiert: Gesetz/Verordnung, Verwaltungsvorschrift, Fachverfahrensbetreiber, Land/Hochschule oder ein EAA-Rulebook.

### 3. Rulebook-Feldbeschreibungen

Fuer grenzueberschreitende Semantik sollte ein Feld mindestens enthalten:

- stabiler Identifier, idealerweise URI-basiert;
- Namespace und Version;
- englischer Default-Name und englische Beschreibung;
- lokale Uebersetzungen optional bzw. zusaetzlich mit Language Tags;
- Datentyp, Format, Wertebereich, Kardinalitaet;
- Beispielwert;
- Rechtsgrundlage, moeglichst ELI-URI;
- Authentic Source oder Issuer-/Trust-Modell;
- Status-/Revocation-Aussage;
- Disclosure-Regel;
- Binding-Regel: device-bound, non-device-bound, PID-Co-Presentation oder `cryptographically_bound_to`.

Konventionen aus dem Rulebook-Template:

- Kapitel 2 definiert Attribute und Metadaten encoding-unabhaengig mit `Data Identifier`, `Definition`, `Data type`, `Example value`.
- mdoc-Encoding: Attribute Identifier, Encoding Format, Namespace und DocType.
- SD-JWT VC-Encoding: `vct`, Claim Name, Encoding Format, Notes und Disclosable. Claim Names muessen IANA-registered, RFC-7519-Public-Names oder attestation-type-spezifische Private Names sein.
- Fuer alle Claims muss angegeben werden, ob ein Attestation Provider sie selektiv offenlegen muss, darf oder nicht darf.
- Kapitel 4 soll festlegen, ob die Attestation device-bound oder non-device-bound ist und ob PID-Verifikation bzw. kryptographische Bindung an eine andere Attestation erforderlich ist.

Englisch-Frage:

- CIR 2025/1569 verlangt fuer Attribute/Schemes eindeutige Identifier, Namespace, Version, semantische Beschreibung, Datentyp, Trust-/Governance-Modell und maschinen- plus menschenlesbare Kataloge.
- TS11 sagt fuer Attribute: `name` braucht mindestens einen englischen Default; `description` sollte mindestens Englisch enthalten, weitere Lokalisierungen koennen mit Language Tags folgen.
- Fuer RP-Intended-Use-Texte sind Lokalisierungen fuer die offiziellen Sprachen der Mitgliedstaaten vorgesehen, in denen der Service angeboten wird.
- Ergebnis: keine allgemeine "English-only"-Pflicht gefunden, aber fuer Cross-Border-Interoperabilitaet sollte Englisch die normative Basissprache sein.

## Gespraechsformulierung

Wenn es in 60 Sekunden sitzen muss:

> Bei PID selbst ist Device-/Wallet-Unit-Binding nicht nur Geschmack, sondern im EUDI-Recht angelegt. Fuer Imma und Studierendenausweis ist die richtige Entscheidung aber use-case-getrieben: Imma braucht meist Person plus konkreten Studiengang; Student-ID eher einen minimalen, device-bound Berechtigungsnachweis. BAfoeG muss seine fachliche Query definieren, die Wallet darf nicht raten. Rulebooks sollten Attribute englisch, maschinenlesbar und mit stabilen Identifiern, Semantik, Trust, Disclosure und Binding-Regeln beschreiben; IANA-JWT ist nur ein Baustein fuer Claim-Namen.

## Quellen

Repo-/Korpusquellen:

- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-03/SRC-L-03_32024R2977_DOC_1_en.xhtml` - CIR 2024/2977: PID/EAA, PID-Binding, WUA-Validierung.
- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-04/SRC-L-04_32024R2979_DOC_1_en.xhtml` - CIR 2024/2979: Integritaet und Core-Funktionalitaeten der Wallet.
- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-36/SRC-L-36_32025R0848_DOC_1_en.xhtml` - CIR 2025/848: RP-Registrierung, Intended Use, Datenumfang.
- `artifacts/real_corpus/archive/context/celex_fulltext_en/SRC-L-41/SRC-L-41_32025R1569_DOC_1_en.xhtml` - CIR 2025/1569: Catalogue of Attributes und Catalogue of Schemes.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-06_openid4vci_1_0.html` - OpenID4VCI: Batch Issuance, Holder Binding, Key Attestation.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-07_openid4vp_1_0.html` - OpenID4VP: DCQL, Claims Query, `multiple`, minimale Claims.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-28_ec_ts03_wallet_unit_attestation.md` - EUDI WUA/WIA, device-bound vs non-device-bound.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-30_ec_ts05_rp_registration_api.md` - RP Intended Use und Credential/Claim-Modell.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-31_ec_ts06_rp_information_set.md` - Common Set of RP Information.
- `artifacts/real_corpus/archive/reference_web/technical_and_standards/SRC-W-TEC-36_ec_ts11_catalogues.md` - Catalogue of Attributes/Attestations, English default name/description.

Webpruefung:

- [EUDI Attestation Rulebooks Catalog](https://github.com/eu-digital-identity-wallet/eudi-doc-attestation-rulebooks-catalog)
- [Attestation Rulebook Template](https://raw.githubusercontent.com/eu-digital-identity-wallet/eudi-doc-attestation-rulebooks-catalog/main/template/attestation-rulebook-template.md)
- [CIR 2025/1569 on EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R1569)
- [OpenID4VCI 1.0](https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html)
- [OpenID4VP 1.0](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html)
- [Offizielle deutsche EUDI-Wallet-App-Seite](https://eudi-wallet.gov.de/app)
- [Offizielle deutsche EUDI-Wallet-Oekosystem-Seite](https://eudi-wallet.gov.de/oekosystem)
- [Deutsche EUDI-Wallet-Sandbox PID-Meldung vom 26.03.2026](https://eudi-wallet.gov.de/news/jetzt-testen-die-pid-funktion-in-der-eudi-wallet-sandbox)
