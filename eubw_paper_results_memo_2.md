# Overall analytical verdict

The six-class lens is usable as the paper's main analytical frame for the core wallet-requirement space. It captures identity/registry anchors, mandate authority, credential semantics, lifecycle/event state, institutional trust, and operational integration without needing structural redesign (C1-EF-01 to C6-DG-01).

Coverage is not total for the full proposal corpus. The clean claim is: full coverage of the core wallet-requirement space, but only partial clean coverage of the wider initiative because rollout economics and meta-governance/review remain residual (R-MKT-01 to R-META-03).

Proposal plus annex carry the normative core. The proposal defines the legal-functional framework, while the annex sharpens technical requirements for authentication, cryptographic assets, logging, QERDS, access control, issuance, presentation, and portability (C1-EF-01 to C6-EF-06).

The SWD is strongest as interpretive pressure, not as a source of extra legal requirements. It explains why the classes matter in practice: fragmented registers, manual PoA checks, repeated credential submissions, audit needs, interoperability limits, provider market dynamics, and adoption costs (C1-IS-01, C2-IS-01, C3-IS-01, C4-IS-02, C6-IS-01, R-MKT-02).

# Class-by-class results

## 1. Organizational Subject Identity and Registry Anchors

Class verdict: strong direct coverage. The proposal explicitly defines the wallet owner, owner identification data, EUID/unique identifiers, authentic-source-based issuance, and the European Digital Directory (C1-EF-01 to C1-EF-04).

Strongest `explicitly_framed` signals: Article 8 makes official name plus unique identifier the minimum identity payload; Article 9 makes EUID the first-choice anchor where available; Article 10 turns the Digital Directory into a restricted trusted information source with one-working-day update duties (C1-EF-02 to C1-EF-04).

Strongest `indirectly_shaped` signals: the SWD explains the coverage problem: BRIS/BORIS and EUID do not cover all relevant economic operators, public bodies, sole traders, or self-employed persons (C1-IS-01).

Strongest `delegated` signals: detailed owner-ID requirements, unique-identifier specifications, unique digital addresses, and directory information categories are left to implementing acts (C1-DG-01).

Strongest `open` signals: legal basis and verification mechanisms for broader or newly registered entity populations remain open, especially for public administrations and other groups beyond standard company-register coverage (C1-OP-01).

Boundary note: C1 holds when about identifying the wallet owner; it strains when access decisions use acting-subject identity together with role and mandate scope (B12-HOLD-01, B12-STRAIN-01).

## 2. Representation, Mandates, and Authority Scope

Class verdict: strong but boundary-heavy. The proposal and annex explicitly treat representatives, mandates, authorisations, and access-control outcomes as core wallet material (C2-EF-01 to C2-EF-03).

Strongest `explicitly_framed` signals: Article 3 defines authorised representative and mandate; Article 5 makes multi-user authorisation and relying-party request authorisation core functions; Annex point 12 turns role, mandate scope, validity, constraints, conflicts, over-delegation, and expired authorisations into access-control requirements (C2-EF-01 to C2-EF-03).

Strongest `indirectly_shaped` signals: the SWD treats manual and cross-border PoA verification as a central burden and reads the EUBW as a PoA/mandate layer for issuing, revoking, tracking, and auditing authority (C2-IS-01, C2-IS-02).

Strongest `delegated` signals: actual role/attribute formats, policy language, mandate interoperability, constraint enforcement, secure logging, timestamping, and audit standards are delegated (C2-DG-01).

Strongest `open` signals: statutory/legal substance of representation is outside the proposal and SWD; the wallet can carry and enforce authority evidence but does not settle underlying authority law (C2-OP-01).

Boundary note: C2 should not absorb registry identity, but in practice the access-control layer repeatedly combines identity, role, and mandate in one decision (B12-STRAIN-01, B12-STRAIN-02).

## 3. Credential and Attestation Object Semantics

Class verdict: strong direct coverage, with much detail delegated. The corpus clearly treats owner ID data, EAAs/QEAAs, wallet unit attestations, linked attestations, authentic-source attestations, and attestation schemes as object-semantic material (C3-EF-01 to C3-EF-04).

Strongest `explicitly_framed` signals: Article 3 defines the object vocabulary; Article 5 makes issuance, request, storage, disclosure, presentation, and linked chains core wallet functions; Article 8 makes owner ID data an attestation object; Annex point 17 requires validation information inside issued EAAs (C3-EF-01 to C3-EF-04).

Strongest `indirectly_shaped` signals: the SWD expands the semantic space beyond identity to licences, compliance certificates, VAT, beneficial ownership, procurement proofs, CE conformity, KYC/KYB, and reusable linked documentation (C3-IS-01, C3-IS-02).

Strongest `delegated` signals: reference standards and concrete role/attribute/EAA formats are not fixed in the proposal/annex and are left to implementing-act standard lists (C3-DG-01, C3-DG-02).

Strongest `open` signals: no separate open issue dominates class 3 once delegation is accepted as the intended mechanism; the main limitation is that paper-ready claims must not over-specify attestation schemas beyond the text (C3-DG-01, C3-DG-02).

Boundary note: C3 holds for what an attestation is and contains; it strains where linked attestations become reuse and lifecycle mechanisms (B34-HOLD-01, B34-STRAIN-01).

## 4. Credential Lifecycle, Exchange, and Event State

Class verdict: strong direct coverage. The annex is especially important here because it specifies revocation, status publication, logs, export, issuance, delivery, activation, validity, and binding (C4-EF-03 to C4-EF-06).

Strongest `explicitly_framed` signals: Article 5 covers storage, deletion, QERDS exchange, export, logs, and dashboard access; Article 6 covers revocation and validation mechanisms; Annex points 6, 7, 10, and 14-16 provide the lifecycle detail (C4-EF-01 to C4-EF-06).

Strongest `indirectly_shaped` signals: the SWD stresses validity-period management, real-time register updates, revocation, auditability, ERP/KYC integration, and traceability as practical reasons lifecycle control matters (C4-IS-01, C4-IS-02).

Strongest `delegated` signals: exchange and lifecycle protocols partly depend on the same implementing-act standard machinery used for core functions and technical features (C3-DG-01, C6-DG-01).

Strongest `open` signals: log retention is not fixed as an EUBW-specific period; it remains whatever Union or national law requires (C4-OP-01).

Boundary note: C4 should carry state change and event evidence, not general object meaning. It strains at issuance and linked-attestation points, where format, delivery, activation, validity, and reuse collapse into one cluster (B34-STRAIN-01, B34-STRAIN-02).

## 5. Institutional Trust and Governance Framework

Class verdict: strong coverage, but with a narrow residual edge. Provider eligibility, notification, provider lists, supervision, penalties, cooperation, Union-entity supervision, and third-country equivalence are all explicit (C5-EF-01 to C5-EF-06).

Strongest `explicitly_framed` signals: Article 7 sets provider trust constraints; Articles 11-13 establish notification, listing, supervision, penalties, breach cooperation, and removal/intervention; Articles 14-15 add cooperation and Union-entity supervision; Article 17 covers third-country equivalence (C5-EF-01 to C5-EF-06).

Strongest `indirectly_shaped` signals: the SWD frames EUBW as a coherent extension of EUDI, with interoperability as a defining principle, and reports stakeholder preference for trustworthiness, verifiable credentials, legal effect, open standards, and provider competition (C5-IS-01, C5-IS-02).

Strongest `delegated` signals: corrective or restrictive Commission action and many practical requirements operate through implementing acts and supervisory follow-through rather than fully specified front-end criteria (C5-EF-04).

Strongest `open` signals: the provider assurance model is intentionally streamlined and ex post; the corpus does not create full prior verification of every provider operation (C5-OP-01).

Boundary note: C5 covers the institutional trust frame, but penalty scales and high-level evaluation mechanics should only be used sparingly in class analysis because they can become residual meta-governance (R-META-01 to R-META-03).

## 6. Enterprise Integration and Operational Control

Class verdict: strong technical-operational coverage. This class is where the annex does the most work for wallet-unit authentication, integrity, secure cryptographic assets, QERDS integration, protocols, interfaces, presentation, dashboards, and portability (C6-EF-01 to C6-EF-07).

Strongest `explicitly_framed` signals: Article 6 lists common protocols and interfaces, remote onboarding, automated interaction, EUDI/EUBW interoperability, digital addresses, unit attestations, critical assets, security by design, and support/reporting channels; Annex points 1-4, 11, 13, and 15 make these operational (C6-EF-01 to C6-EF-06).

Strongest `indirectly_shaped` signals: the SWD expects ERP/CRM integration, secure APIs, no vendor lock-in, portability, future readiness for AI or asset identity, and multiple implementation models including mobile, enterprise-integrated, and cloud (C6-IS-01, C6-IS-02).

Strongest `delegated` signals: detailed technical features, standards, specifications, and procedures are delegated to implementing acts (C6-DG-01).

Strongest `open` signals: adoption depends on usability, minimal user interaction, training, price, and integration quality, which the normative core cannot fully settle (C6-OP-01).

Boundary note: C6 should not become a dump for all implementation talk. It covers wallet operational control; provider-market economics and general rollout support belong in the residual envelope (R-MKT-01, R-MKT-02).

# Boundary stress results

## 1/2

Boundary holds: owner identity and mandate authority are separately defined in Article 3, and owner identification data is anchored in Article 8/9 while representatives and mandates sit in Article 3(18)-(19) and Article 5(1)(j)-(k) (B12-HOLD-01, C1-EF-02, C2-EF-01, C2-EF-02).

Boundary strains: Annex point 12 makes access decisions depend simultaneously on acting-subject attestations, formal role, mandate scope, validity, constraints, and policy context. The SWD adds that multi-layered representation and internal mandates complicate verification (B12-STRAIN-01, B12-STRAIN-02).

Drafting use: keep C1 as "who/which organisation is this?" and C2 as "who may act, within what scope, under what mandate?" Then note that access control is the main boundary-stress zone.

## 3/4

Boundary holds: object semantics are separately defined in Article 3 and Article 8, while Annex points 6-7 separately address revocation, status, logging, access, and retention (B34-HOLD-01, B34-HOLD-02).

Boundary strains: linked attestations and issuance provisions combine semantic structure with reuse, delivery, activation, authenticity, and validity checks. This is not a taxonomy failure; it shows that attestation objects are designed for lifecycle behaviour (B34-STRAIN-01, B34-STRAIN-02).

Drafting use: C3 should carry vocabulary and payload meaning; C4 should carry state, event, exchange, proof, status, and audit behaviour. Linked attestations need a bridge paragraph.

## 5/6

Boundary holds: Articles 11-13 are institutional governance, while Annex points 1-4 and 11 are operational-control requirements (B56-HOLD-01, B56-HOLD-02).

Boundary strains: cybersecurity, high-risk suppliers, security by design, access controls, audit logs, and traceability connect provider governance directly to operational architecture and supply-chain control (B56-STRAIN-01, B56-STRAIN-02).

Drafting use: keep C5 for institutional trust allocation and oversight; keep C6 for system-level implementation obligations. Acknowledge cybersecurity as the bridge.

# Residual envelope

Residual envelope is narrow and should not be used to avoid hard coding. Most material fits the six classes.

`market/business model and rollout economics`: market-driven deployment, paid/free debates, fair competition, provider incentives, SME price sensitivity, training, adoption readiness, and cost-benefit estimates are analytically relevant but not best treated as wallet requirement classes (R-MKT-01 to R-MKT-03).

`meta-governance / enforcement / review`: Article 21 review duties, SWD monitoring indicators, penalty scales, and exceptional Commission corrective/restrictive measures support initiative governance, but they should not be over-coded into the six wallet classes unless the paper is discussing trust governance specifically (R-META-01 to R-META-03).

Residual implication: the six classes can claim full coverage of the core wallet-requirement space, not full clean coverage of all proposal/SWD material.

# Implications for the later class-based EUBW analysis

Use the six classes as the main paper structure with only minor boundary notes. No redesign is justified by this pass.

Best reusable main claim: the EUBW proposal is not merely "a business identity wallet"; it is a composite organisational-wallet framework linking registry-anchored identity, mandate authority, attestation semantics, lifecycle/audit state, trust governance, and enterprise integration (C1-EF-01, C2-EF-03, C3-EF-02, C4-EF-04, C5-EF-04, C6-EF-01).

Best limitation claim: several decisive implementation details are deliberately delegated to implementing acts, especially identifiers, directory details, technical standards, protocols, role/attribute formats, access-control policy language, and interoperability mechanisms (C1-DG-01, C2-DG-01, C3-DG-01, C3-DG-02, C6-DG-01).

Best residual claim: the class model captures wallet requirements well, but market rollout economics and meta-review/enforcement material require a separate residual envelope to avoid distorting the requirement classes (R-MKT-01 to R-META-03).

Do not overclaim final taxonomy status. The correct end-state is a disciplined preliminary class-based analysis whose strongest result is coverage of the core requirement space plus explicit boundary and residual management.
