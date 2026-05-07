from __future__ import annotations

from typing import List

from eubw_researcher.models import (
    ClaimTarget,
    ClaimType,
    QueryIntent,
    RetrievalPlan,
    RetrievalPlanStep,
    RetrievalTargetQuery,
    RuntimeConfig,
    SourceHierarchyConfig,
    SourceKind,
    SourceRoleLevel,
    TerminologyConfig,
)
from eubw_researcher.retrieval.terminology import (
    normalize_query_terms,
    normalize_query_terms_with_trace,
)
from eubw_researcher.retrieval.text_normalization import (
    normalize_text_for_matching,
    token_set,
)


def _contains_any(text: str, terms: List[str]) -> bool:
    normalized_text = normalize_text_for_matching(text)
    return any(normalize_text_for_matching(term) in normalized_text for term in terms)


def _phrase_score(text: str, phrases: List[str]) -> int:
    normalized_text = normalize_text_for_matching(text)
    return sum(
        1 for phrase in phrases if normalize_text_for_matching(phrase) in normalized_text
    )


def _token_overlap(tokens: set[str], expected: List[str]) -> int:
    return sum(1 for token in expected if token in tokens)


def _has_business_wallet_subject(lowered: str, tokens: set[str]) -> bool:
    return (
        _contains_any(lowered, ["business wallet", "wallet-relying party", "relying party"])
        or ({"wallet", "party"} <= tokens)
    )


def _is_information_request(lowered: str, tokens: set[str]) -> bool:
    return _phrase_score(
        lowered,
        [
            "what information",
            "which information",
            "what data",
            "which data",
            "which fields",
            "what fields",
            "must provide",
            "shall provide",
            "needs to provide",
            "must be registered",
            "needs to be registered",
            "registration information",
            "onboarding data",
            "data points",
        ],
    ) > 0 or (
        "information" in tokens or "data" in tokens or "fields" in tokens
    )


def _is_requirements_request(lowered: str, tokens: set[str]) -> bool:
    return _phrase_score(
        lowered,
        [
            "requirements apply",
            "what requirements",
            "which requirements",
            "summarize the requirements",
            "map the requirements",
            "organize the requirements",
            "cluster the obligations",
            "provisionally structure",
            "provisionally grouped",
            "structured provisionally",
        ],
    ) > 0 or (
        ("requirements" in tokens or "obligations" in tokens)
        and ("group" in tokens or "structure" in tokens or "cluster" in tokens or "map" in tokens)
    )


def _is_comparison_request(lowered: str, tokens: set[str]) -> bool:
    return _phrase_score(
        lowered,
        [
            "what is the difference",
            "difference between",
            "compare",
            "comparison",
            "distinguish",
            "versus",
        ],
    ) > 0 or "difference" in tokens or "compare" in tokens


def _protocol_comparison_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="openid4vci_authorization_server",
            claim_text=(
                "OpenID4VCI uses an authorization-server/token-endpoint flow "
                "for credential issuance."
            ),
            claim_type=ClaimType.PROTOCOL_BEHAVIOR,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
            scope_terms=["openid4vci", "credential issuance", "credential issuer"],
            primary_terms=["authorization", "server", "token endpoint", "access token"],
            support_groups=[
                ["credential issuer", "authorization server"],
                ["token endpoint", "access token"],
                ["authorization server", "credential endpoint"],
            ],
            contradiction_groups=[
                ["does not define", "authorization server"],
                ["no authorization server"],
            ],
            grouping_label="Protocol and authorization model",
        ),
        ClaimTarget(
            target_id="openid4vp_authorization_server",
            claim_text=(
                "OpenID4VP defines the verifier-facing presentation flow around an "
                "Authorization Request to the Wallet and Wallet metadata."
            ),
            claim_type=ClaimType.PROTOCOL_BEHAVIOR,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
            scope_terms=[
                "openid4vp",
                "presentation request",
                "wallet invocation",
                "wallet metadata",
                "vp_formats_supported",
            ],
            primary_terms=["authorization request", "wallet", "wallet metadata", "verifier"],
            support_groups=[
                ["presentation request", "wallet"],
                ["wallet invocation", "wallet"],
                ["wallet metadata", "vp_formats_supported"],
            ],
            contradiction_groups=[
                ["token endpoint", "credential issuer"],
                ["access token", "credential issuer"],
            ],
            grouping_label="Protocol and authorization model",
        ),
    ]


def _registration_mandatory_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="registration_certificate_eu_level",
            claim_text=(
                "At EU level, the qualified registration certificate identifies the "
                "organisation that uses the business wallet."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["registration", "certificate"],
            primary_terms=["registration", "certificate", "organisation"],
            support_groups=[
                ["qualified registration certificate", "identify the organisation"],
                ["shall identify the organisation"],
            ],
            contradiction_groups=[["optional everywhere"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="member_state_discretion",
            claim_text=(
                "Member States may define national registration procedures only where "
                "Union law leaves implementation discretion."
            ),
            claim_type=ClaimType.ALLOWANCE,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION, SourceKind.NATIONAL_IMPLEMENTATION],
            scope_terms=["member states", "national"],
            primary_terms=["member", "states", "discretion"],
            support_groups=[
                ["member states", "implementation discretion"],
                ["member states", "national registration procedures"],
            ],
            contradiction_groups=[["mandatory everywhere"]],
            grouping_label="Governance and discretion",
        ),
    ]


def _wallet_requirements_targets() -> List[ClaimTarget]:
    return [
        _registration_mandatory_targets()[0],
        ClaimTarget(
            target_id="wallet_access_certificate_requirement",
            claim_text=(
                "At EU level, the access certificate identifies the relying-party service "
                "that is entitled to request wallet-mediated access."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["access certificate", "wallet-mediated access", "relying party service"],
            primary_terms=["access certificate", "relying party", "wallet access"],
            support_groups=[
                ["access certificate", "relying party service"],
                ["wallet-mediated access"],
            ],
            contradiction_groups=[["no access certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="annex_registration_fields",
            claim_text=(
                "The annex lists minimum registration-certificate data fields when "
                "the governing Union act requires the certificate."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["annex", "registration"],
            primary_terms=["annex", "registration", "fields"],
            support_groups=[
                ["annex", "minimum fields"],
                ["registration certificate data fields"],
            ],
            contradiction_groups=[["override the regulation"]],
            grouping_label="Registration information",
        ),
        _registration_mandatory_targets()[1],
        ClaimTarget(
            target_id="wallet_national_guidance_boundary",
            claim_text=(
                "National guidance may refine procedures, but it does not override Union "
                "regulation or implementing-act requirements."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.NATIONAL_IMPLEMENTATION],
            scope_terms=["national guidance", "procedures", "union regulation"],
            primary_terms=["guidance", "procedures", "override"],
            support_groups=[
                ["does not override union regulation"],
                ["procedural registration steps"],
            ],
            contradiction_groups=[["replaces union regulation"]],
            grouping_label="Governance and discretion",
        ),
    ]


def _certificate_layer_targets() -> List[ClaimTarget]:
    return [
        _registration_mandatory_targets()[0],
        ClaimTarget(
            target_id="access_certificate_eu_level",
            claim_text=(
                "At EU level, the access certificate identifies the relying-party service "
                "that is entitled to request wallet-mediated access."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["access", "certificate"],
            primary_terms=["access", "certificate", "relying"],
            support_groups=[
                ["access certificate", "relying party service"],
                ["access certificate", "wallet-mediated access"],
            ],
            contradiction_groups=[["no access certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="national_guidance_boundary",
            claim_text=(
                "National guidance may add procedures, but it does not override Union "
                "regulation or referenced standards."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.NATIONAL_IMPLEMENTATION],
            scope_terms=["guidance", "national"],
            primary_terms=["guidance", "override", "union"],
            support_groups=[
                ["does not override union regulation"],
                ["procedural registration steps"],
            ],
            contradiction_groups=[["overrides union regulation"], ["replaces union regulation"]],
            grouping_label="Governance and discretion",
        ),
    ]


def _germany_wallet_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="germany_eu_wallet_anchor",
            claim_text=(
                "EU law remains the governing layer for the digital identity wallet and "
                "frames any Germany-specific implementation path."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
            scope_terms=["eu", "wallet", "germany", "implementation"],
            primary_terms=["eu", "wallet", "governing", "implementation"],
            support_groups=[
                ["union", "wallet"],
                ["regulation", "wallet"],
            ],
            contradiction_groups=[["germany overrides union law"]],
            grouping_label="Governance and discretion",
        ),
        ClaimTarget(
            target_id="germany_wallet_legal_path",
            claim_text=(
                "Germany is building its wallet implementation path through a national "
                "legal and legislative track that is still provisional where draft material is used."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.NATIONAL_IMPLEMENTATION],
            scope_terms=["germany", "deutschland", "gesetz", "eidas", "durchführungsgesetz"],
            primary_terms=["germany", "law", "draft", "wallet"],
            support_groups=[
                ["referentenentwurf", "eidas"],
                ["gesetzentwurf", "eidas"],
                ["durchführungsgesetz", "eidas"],
                ["gesetz", "digitale identität"],
                ["ressortabstimmung", "eidas"],
            ],
            contradiction_groups=[["final law already in force"]],
            grouping_label="Germany implementation path",
        ),
        ClaimTarget(
            target_id="germany_sprind_role",
            claim_text=(
                "SPRIND plays an official Germany-specific development or prototyping role in the "
                "wallet ecosystem, but that role does not itself create binding legal requirements."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.PROJECT_ARTIFACT, SourceKind.NATIONAL_IMPLEMENTATION],
            scope_terms=["sprind", "wallet", "germany"],
            primary_terms=["sprind", "prototype", "wallet", "development"],
            support_groups=[
                ["sprind", "wallet"],
                ["sprind", "prototype"],
                ["sprind", "digitale identität"],
            ],
            contradiction_groups=[["sprind creates binding law"]],
            grouping_label="Germany implementation path",
        ),
        ClaimTarget(
            target_id="germany_non_override_boundary",
            claim_text=(
                "Germany-specific guidance and implementation material may add delivery detail, "
                "but it does not override governing EU wallet obligations."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.NATIONAL_IMPLEMENTATION, SourceKind.REGULATION],
            scope_terms=["germany", "implementation", "eu", "obligations"],
            primary_terms=["override", "germany", "eu", "implementation"],
            support_groups=[
                ["does not override", "union"],
                ["does not override", "eu"],
                ["unionsrecht", "vorrang"],
                ["eu-recht", "vorrang"],
                ["union law", "implementation discretion"],
            ],
            contradiction_groups=[["germany overrides eu"]],
            grouping_label="Governance and discretion",
        ),
    ]


def _certificate_topology_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="topology_registration_certificate_role",
            claim_text=(
                "Governing EU sources define a wallet-relying party registration "
                "certificate as describing the relying party's intended use and the "
                "attributes it has registered to request from users."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.REGULATION],
            scope_terms=["wallet-relying party", "registration certificate", "intended use"],
            primary_terms=["registration certificate", "intended use", "attributes", "request from users"],
            support_groups=[
                ["wallet-relying party registration certificate", "describes the intended use"],
                ["registration certificate", "attributes", "request from users"],
            ],
            contradiction_groups=[["no registration certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="topology_access_certificate_role",
            claim_text=(
                "Governing EU sources define a wallet-relying party access certificate "
                "as authenticating and validating the wallet-relying party in wallet "
                "interactions."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.REGULATION],
            scope_terms=["wallet-relying party", "access certificate", "wallet interactions"],
            primary_terms=[
                "wallet-relying party access certificate",
                "authenticating",
                "validating",
                "wallet",
            ],
            support_groups=[
                ["wallet-relying party access certificate", "authenticating and validating the wallet-relying party"],
                ["authenticate and validate", "wallet-relying party access certificate"],
            ],
            contradiction_groups=[["no access certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="topology_registration_access_linkage",
            claim_text=(
                "Governing EU sources link registration-certificate issuance to a "
                "valid wallet-relying party access certificate."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["wallet-relying party", "registration certificate", "access certificate"],
            primary_terms=["issuing", "registration certificate", "access certificate", "valid"],
            support_groups=[
                ["issuing a wallet-relying party registration certificate", "access certificate is valid"],
                ["wallet-relying party access certificate is valid"],
            ],
            contradiction_groups=[["registration certificate without access certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="topology_project_artifact_multiplicity",
            claim_text=(
                "Official project artifacts explicitly describe one or more access "
                "certificates for relying party instances and one or more registration "
                "certificates when such certificates are issued."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.PROJECT_ARTIFACT],
            scope_terms=["relying party", "access certificate", "registration certificate", "relying party instances"],
            primary_terms=[
                "one or more access certificates",
                "one or more registration certificates",
                "relying party instances",
            ],
            support_groups=[
                ["one or more access certificates", "relying party instances"],
                ["one or more registration certificates"],
            ],
            contradiction_groups=[["single registration certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="topology_project_intended_use_scoping",
            claim_text=(
                "Official project artifacts explicitly describe registration "
                "certificates as issued per registered intended use or selected for "
                "the intended use relevant to the current request."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.PROJECT_ARTIFACT],
            scope_terms=["registration certificate", "intended use", "relying party"],
            primary_terms=[
                "registration certificates",
                "registered intended use",
                "current presentation request",
            ],
            support_groups=[
                ["registration certificates are issued per each registered intended use"],
                ["registration certificate", "intended use relevant for the current"],
            ],
            contradiction_groups=[["single organisation certificate"]],
            grouping_label="Certificates and identity",
        ),
    ]


def _relying_party_registration_information_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="rp_registration_annex_i_requirement",
            claim_text=(
                "Wallet-relying parties shall at least provide the information set out "
                "in Annex I to national registers."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.REGULATION],
            scope_terms=["wallet-relying party", "registration", "annex i", "national register"],
            primary_terms=["provide", "information", "annex i", "national register"],
            support_groups=[
                ["wallet-relying parties", "provide", "annex i"],
                ["information set out in annex i", "national registers"],
            ],
            contradiction_groups=[["no registration information"], ["outside annex i"]],
            grouping_label="Registration information",
        ),
        ClaimTarget(
            target_id="rp_registration_information_categories",
            claim_text=(
                "Annex I covers name or trade/service name, identifiers, physical address "
                "or URL/contact details, and intended-use, entitlement, and supervisory-authority data."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.PROJECT_ARTIFACT],
            scope_terms=["wallet-relying party", "annex i", "registration", "intended use"],
            primary_terms=[
                "trade name",
                "identifier",
                "physical address",
                "contact information",
                "intended use",
                "entitlement",
                "supervisory authority",
            ],
            support_groups=[
                ["trade name", "identifier"],
                ["physical address", "contact information"],
                ["intended use", "data"],
                ["entitlement", "supervisory authority"],
            ],
            contradiction_groups=[["only company name"], ["no intended use"]],
            grouping_label="Registration information",
        ),
    ]


def _relying_party_certificate_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="rp_registration_certificate_definition",
            claim_text=(
                "A wallet-relying party registration certificate describes the relying "
                "party's intended use and the attributes it has registered to request from users."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["wallet-relying party", "registration certificate", "intended use"],
            primary_terms=["describes", "intended use", "attributes", "request from users"],
            support_groups=[
                ["registration certificate", "describes the intended use"],
                ["registration certificate", "attributes", "request from users"],
            ],
            contradiction_groups=[["no registration certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="rp_access_certificate_role",
            claim_text=(
                "A wallet-relying party access certificate is used in interactions with "
                "wallet solutions and must remain accurate and consistent with the national-register information."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["wallet-relying party", "access certificate", "wallet solutions"],
            primary_terms=[
                "interactions with wallet solutions",
                "accurate",
                "consistent",
                "registration information",
            ],
            support_groups=[
                ["access certificate", "interactions with wallet solutions"],
                ["access certificate", "accurate", "consistent", "registration information"],
            ],
            contradiction_groups=[["no access certificate"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="rp_certificate_linkage",
            claim_text=(
                "When issuing a wallet-relying party registration certificate, the provider "
                "must verify that the wallet-relying party access certificate is valid."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["wallet-relying party", "registration certificate", "access certificate"],
            primary_terms=["issuing", "verify", "valid"],
            support_groups=[
                ["issuing a wallet-relying party registration certificate", "access certificate is valid"],
                ["registration certificate", "access certificate is valid"],
            ],
            contradiction_groups=[["registration certificate without access certificate"]],
            grouping_label="Certificates and identity",
        ),
    ]


def _is_relying_party_registration_information_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return (
        _has_business_wallet_subject(lowered, tokens)
        and ("registration" in tokens or "register" in tokens)
        and _is_information_request(lowered, tokens)
    )


def _is_relying_party_certificate_question(
    lowered: str,
    *,
    original_lowered: str | None = None,
) -> bool:
    tokens = token_set(lowered)
    original_tokens = token_set(original_lowered) if original_lowered is not None else tokens
    return (
        _contains_any(lowered, ["registration certificate"])
        and _contains_any(lowered, ["access certificate"])
        and _is_comparison_request(lowered, tokens)
        and (
            _has_business_wallet_subject(lowered, tokens)
            or (
                original_lowered is not None
                and _has_business_wallet_subject(original_lowered, original_tokens)
            )
        )
    )


def _is_certificate_topology_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    certificate_context = _has_business_wallet_subject(lowered, tokens) or _contains_any(
        lowered,
        [
            "wallet-relying-party",
            "wallet relying party",
            "relying-party",
            "relying party",
        ],
    )
    certificate_terms = _contains_any(
        lowered,
        [
            "access certificate",
            "registration certificate",
            "certificate",
            "certificates",
            "zertifikat",
            "zertifikate",
        ],
    ) or _token_overlap(tokens, ["access", "registration", "certificate", "certificates"]) >= 2
    topology_terms = _contains_any(
        lowered,
        [
            "derived certificate",
            "derived access",
            "derived registration",
            "multiple certificates",
            "single certificate",
            "organisation-level",
            "organization-level",
            "service-scoped",
            "organisation-scoped",
            "organization-scoped",
            "intended use",
            "service scope",
            "abgeleitet",
            "abgeleitete",
            "hauptzertifikat",
            "mehrere",
        ],
    ) or _token_overlap(
        tokens,
        [
            "derived",
            "multiple",
            "single",
            "organisation",
            "organization",
            "service",
            "scope",
            "intended",
            "mehrere",
            "hauptzertifikat",
        ],
    ) >= 2
    return certificate_context and certificate_terms and topology_terms


def _is_business_wallet_requirements_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return _has_business_wallet_subject(lowered, tokens) and _is_requirements_request(lowered, tokens)


def _is_registration_scope_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return (
        "registration certificate" in lowered
        and (
            _contains_any(
                lowered,
                ["mandatory", "member states", "delegated", "eu level", "union level", "national registration"],
            )
            or _token_overlap(tokens, ["mandatory", "delegated", "union", "member", "states", "national"]) >= 2
        )
    )


def _is_protocol_authorization_server_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return (
        _contains_any(lowered, ["openid4vci", "openid4vp"])
        and (
            _contains_any(lowered, ["authorization server", "token endpoint", "wallet metadata"])
            or _is_comparison_request(lowered, tokens)
            or _token_overlap(tokens, ["wallet", "metadata", "authorization", "server", "token", "endpoint"]) >= 3
        )
    )


def _is_arf_boundary_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return "arf" in lowered and (
        _contains_any(lowered, ["authorization server", "verifier", "presentation flow"])
        or _token_overlap(tokens, ["authorization", "server", "verifier", "presentation", "flow"]) >= 3
    )


def _is_germany_wallet_implementation_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    has_germany_signal = _contains_any(
        lowered,
        [
            "sprind",
            "germany",
            "german",
            "deutschland",
            "deutsch",
            "digitale identitaet",
            "digitale brieftasche",
            "eidas-durchfuehrungsgesetz",
            "durchfuehrungsgesetz",
        ],
    ) or _token_overlap(tokens, ["sprind", "germany", "deutschland", "deutsch"]) >= 1
    has_wallet_signal = _contains_any(
        lowered,
        [
            "wallet",
            "business wallet",
            "eudi",
            "brieftasche",
            "digitale identitaet",
        ],
    ) or _token_overlap(tokens, ["wallet", "eudi", "brieftasche"]) >= 1
    return has_germany_signal and has_wallet_signal


def _is_eubw_role_boundary_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    role_score = _phrase_score(
        lowered,
        [
            "verantwortungsgrenzen",
            "responsibility boundaries",
            "wallet provider",
            "issuer",
            "aussteller",
            "verifier",
            "pruefer",
            "registerbetreiber",
            "vertrauensdiensteanbieter",
            "trust service provider",
        ],
    )
    return role_score >= 2 or (
        _token_overlap(
            tokens,
            [
                "wallet",
                "provider",
                "issuer",
                "aussteller",
                "verifier",
                "pruefer",
                "register",
                "registerbetreiber",
                "vertrauensdiensteanbieter",
            ],
        )
        >= 4
    )


def _is_eubw_lifecycle_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return _contains_any(
        lowered,
        ["lebenszyklus", "lifecycle", "registerdaten", "vertretungsrechte", "unternehmensstatus"],
    ) or (
        _token_overlap(
            tokens,
            [
                "lebenszyklus",
                "lifecycle",
                "mandate",
                "registerdaten",
                "vertretungsrechte",
                "unternehmensstatus",
            ],
        )
        >= 3
    )


def _is_eubw_audit_trail_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return _contains_any(
        lowered,
        ["audit", "ereignisspuren", "streitfaelle", "streitfalle", "compliance-nachweise"],
    ) or _token_overlap(
        tokens,
        ["audit", "ereignisspuren", "streitfaelle", "compliance", "nachweise", "vollprotokollierung"],
    ) >= 3


def _is_eubw_identity_authority_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return (
        _contains_any(lowered, ["natuerlichen person", "natural person"])
        and _contains_any(lowered, ["juristische person", "legal person"])
        and (
            _contains_any(lowered, ["handlungsbefugnis", "mandate", "vertretung", "authority"])
            or _token_overlap(tokens, ["mandate", "vertretung", "handlungsbefugnis", "authority"]) >= 1
        )
    )


def _is_eubw_architecture_bucket_question(lowered: str) -> bool:
    tokens = token_set(lowered)
    return (
        _contains_any(lowered, ["proposal", "annex"])
        and _contains_any(lowered, ["architektur", "architecture"])
        and (
            _contains_any(lowered, ["technical specifications", "technische spezifikationen"])
            or _token_overlap(tokens, ["proposal", "annex", "architecture", "technical", "specifications"]) >= 4
        )
    )


def _arf_boundary_targets() -> List[ClaimTarget]:
    return [
        _protocol_comparison_targets()[1],
        ClaimTarget(
            target_id="arf_boundary",
            claim_text=(
                "The ARF profile note can describe deployment patterns, but it does not "
                "create binding protocol requirements."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.MEDIUM,
            preferred_kinds=[SourceKind.PROJECT_ARTIFACT],
            scope_terms=["profile note", "deployment"],
            primary_terms=["binding", "protocol", "requirements"],
            support_groups=[
                ["does not create binding", "protocol requirements"],
                ["deployment patterns"],
            ],
            contradiction_groups=[["arf", "requires"]],
        ),
    ]


def _eubw_role_boundary_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="eubw_registrar_boundary",
            claim_text=(
                "Member States designate registrars to manage and operate national registers "
                "and to publish registered relying-party information through a website and API."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["registrar", "national register", "wallet-relying party"],
            primary_terms=["registrar", "manage", "operate", "api", "website"],
            support_groups=[
                ["designate at least one registrar", "manage and operate at least one national register"],
                ["single common application programming interface", "national website"],
            ],
            contradiction_groups=[["wallet provider manages the national register"]],
            grouping_label="Governance and discretion",
        ),
        ClaimTarget(
            target_id="eubw_certificate_provider_boundary",
            claim_text=(
                "Providers of relying-party access and registration certificates are persons "
                "mandated by Member States to issue those certificates to registered relying parties."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["provider", "certificate", "mandated by a member state"],
            primary_terms=["access certificate", "registration certificate", "mandated", "issue"],
            support_groups=[
                ["provider of wallet-relying party access certificates", "mandated by a member state"],
                ["provider of wallet-relying party registration certificates", "mandated by a member state"],
            ],
            contradiction_groups=[["registrar issues every certificate directly"]],
            grouping_label="Certificates and identity",
        ),
        ClaimTarget(
            target_id="eubw_verifier_boundary",
            claim_text=(
                "Wallet-relying parties declare intended use and entitlements and may request "
                "only data that fall within their registered or authorised scope."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["wallet-relying party", "intended use", "entitlement"],
            primary_terms=["request", "data", "intended use", "authorised", "entitlements"],
            support_groups=[
                ["including their entitlement or entitlements", "national registers"],
                ["not to request users to provide any data other than those indicated for the intended use"],
            ],
            contradiction_groups=[["wallet-relying parties may request any data"]],
            grouping_label="Registration information",
        ),
        ClaimTarget(
            target_id="eubw_wallet_provider_boundary",
            claim_text=(
                "Proposal-stage EUBW sources assign wallet providers responsibility for "
                "access-control enforcement, transaction logging, and wallet-unit-attestation revocation."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["wallet provider", "access control", "transaction logs"],
            primary_terms=["wallet provider", "logging policy", "revocation", "access control"],
            support_groups=[
                ["providers of european business wallets shall provide an appropriate logging policy"],
                ["conditions and the timeframe for the revocation of wallets unit attestations"],
            ],
            contradiction_groups=[["wallet providers have no logging responsibilities"]],
            grouping_label="Operational controls",
        ),
        ClaimTarget(
            target_id="eubw_qtsp_boundary",
            claim_text=(
                "Qualified trust service providers verify authentic-source attributes, including "
                "powers and mandates, and issue qualified electronic attestations of attributes."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["qualified trust service provider", "attestation of attributes", "mandates"],
            primary_terms=["verify", "authenticity", "powers and mandates", "qualified electronic attestation"],
            support_groups=[
                ["qualified trust service providers of electronic attestations of attributes", "verify by electronic means"],
                ["powers and mandates to represent natural or legal persons"],
            ],
            contradiction_groups=[["qualified trust service providers do not verify attributes"]],
            grouping_label="Certificates and identity",
        ),
    ]


def _eubw_lifecycle_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="eubw_registration_updates",
            claim_text=(
                "National registration policies may include automated means to register "
                "or update existing registrations."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["registration", "update", "national registration policies"],
            primary_terms=["register", "update", "registration"],
            support_groups=[
                ["automated means of enabling wallet-relying parties to register or to update an existing registration"],
            ],
            contradiction_groups=[["no update an existing registration"]],
            grouping_label="Lifecycle and change handling",
        ),
        ClaimTarget(
            target_id="eubw_registration_suspension_cancellation",
            claim_text=(
                "Registrars may suspend or cancel registrations when registered information "
                "is inaccurate, out of date, misleading, or otherwise non-compliant."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["registrars", "suspend", "cancel", "registration"],
            primary_terms=["inaccurate", "out of date", "misleading", "suspend", "cancel"],
            support_groups=[
                ["suspend or cancel the registration", "inaccurate, out of date or misleading"],
                ["suspend or cancel the registration", "not complying with the registration policy"],
            ],
            contradiction_groups=[["registrations cannot be suspended"]],
            grouping_label="Lifecycle and change handling",
        ),
        ClaimTarget(
            target_id="eubw_lifecycle_record_retention",
            claim_text=(
                "Registrars keep registration information for 10 years for ex post monitoring, "
                "investigations, and dispute handling."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["registrars", "records", "10 years", "dispute handling"],
            primary_terms=["records", "10 years", "monitoring", "dispute"],
            support_groups=[
                ["keep records of all the information provided", "10 years"],
                ["ex post monitoring", "dispute handling"],
            ],
            contradiction_groups=[["delete all records immediately"]],
            grouping_label="Lifecycle and change handling",
        ),
        ClaimTarget(
            target_id="eubw_mandate_revocation_controls",
            claim_text=(
                "Proposal-stage EUBW sources require role and mandate mappings to be verifiable, "
                "auditable, revocable, and protected against expired authorisations."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["roles", "mandates", "revocable", "expired authorisations"],
            primary_terms=["verifiable", "auditable", "revocable", "expired authorisations"],
            support_groups=[
                ["mappings between roles and attributes are verifiable, auditable, revocable"],
                ["expired authorisations are automatically detected and prevented in real time"],
            ],
            contradiction_groups=[["expired authorisations may continue indefinitely"]],
            grouping_label="Lifecycle and change handling",
        ),
    ]


def _eubw_audit_trail_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="eubw_dispute_record_retention",
            claim_text=(
                "Registrars retain registration information for 10 years for ex post "
                "monitoring, investigations, and dispute handling."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT],
            scope_terms=["records", "10 years", "dispute handling", "registrars"],
            primary_terms=["records", "10 years", "investigations", "dispute"],
            support_groups=[
                ["keep records of all the information provided", "10 years"],
                ["ex post monitoring", "investigations", "dispute handling"],
            ],
            contradiction_groups=[["no records are kept"]],
            grouping_label="Audit and evidence",
        ),
        ClaimTarget(
            target_id="eubw_transaction_logging_minimum",
            claim_text=(
                "Proposal-stage EUBW sources require a logging policy that covers at least "
                "electronic signing, sealing, and transaction notifications."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["transaction logs", "logging policy", "signing", "sealing"],
            primary_terms=["logging policy", "electronic signing", "electronic sealing", "notifications"],
            support_groups=[
                ["logging policy", "electronic signing", "electronic sealing"],
                ["notifications of all transactions"],
            ],
            contradiction_groups=[["no transaction logging"]],
            grouping_label="Audit and evidence",
        ),
        ClaimTarget(
            target_id="eubw_authorisation_event_proofs",
            claim_text=(
                "Proposal-stage EUBW sources require access and execution events to be logged, "
                "timestamped, and bound to cryptographically verifiable proofs of authorisation."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["access", "execution events", "authorisation", "audit"],
            primary_terms=["logged", "timestamped", "cryptographically verifiable proofs of authorisation"],
            support_groups=[
                ["all access and execution events are logged, timestamped"],
                ["cryptographically verifiable proofs of authorisation"],
            ],
            contradiction_groups=[["authorisation events need not be auditable"]],
            grouping_label="Audit and evidence",
        ),
        ClaimTarget(
            target_id="eubw_log_retention_boundary",
            claim_text=(
                "Proposal-stage EUBW sources tie log accessibility to Union or national law "
                "instead of unlimited full retention."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["logs", "accessible", "union law", "national law"],
            primary_terms=["logs", "accessible", "required by union law", "national law"],
            support_groups=[
                ["shall remain accessible for as long as required to be accessible by union law or national law"],
            ],
            contradiction_groups=[["retain all logs forever"]],
            grouping_label="Audit and evidence",
        ),
    ]


def _eubw_identity_authority_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="eubw_qtsp_mandate_verification",
            claim_text=(
                "Qualified trust service providers may verify authentic-source attributes, including "
                "powers and mandates to represent natural or legal persons."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["qualified trust service providers", "powers and mandates", "natural or legal persons"],
            primary_terms=["verify", "authenticity", "powers", "mandates", "represent"],
            support_groups=[
                ["qualified trust service providers of electronic attestations of attributes", "verify by electronic means"],
                ["powers and mandates to represent natural or legal persons"],
            ],
            contradiction_groups=[["mandates cannot be verified electronically"]],
            grouping_label="Identity and authority",
        ),
        ClaimTarget(
            target_id="eubw_natural_legal_person_separation",
            claim_text=(
                "EU sources separate natural-person certificate data from legal-person certificate data."
            ),
            claim_type=ClaimType.OBLIGATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["natural persons", "legal persons", "certificate"],
            primary_terms=["natural persons", "legal persons", "certificate", "registration number"],
            support_groups=[
                ["for natural persons: at least the name of the person"],
                ["for legal persons: a unique set of data unambiguously representing the legal person"],
            ],
            contradiction_groups=[["natural and legal persons use the same certificate identity fields"]],
            grouping_label="Identity and authority",
        ),
        ClaimTarget(
            target_id="eubw_identity_role_mandate_layering",
            claim_text=(
                "Proposal-stage EUBW sources layer acting-subject identity, formal role, "
                "and mandate scope and validity as separate inputs to authorisation decisions."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["acting subject", "formal role", "mandate", "power of attorney"],
            primary_terms=["acting subject", "formal role", "scope", "validity", "mandate"],
            support_groups=[
                ["electronic attestation of attributes of the acting subject"],
                ["the formal role of the acting subjects"],
                ["the scope, validity and constraints of any mandate, delegation, or power of attorney"],
            ],
            contradiction_groups=[["one undifferentiated identity blob"]],
            grouping_label="Identity and authority",
        ),
    ]


def _eubw_architecture_bucket_targets() -> List[ClaimTarget]:
    return [
        ClaimTarget(
            target_id="eubw_direct_architecture_constraints",
            claim_text=(
                "Proposal-stage EUBW sources directly require digital management of representation rights "
                "and mandates and a secure channel supported by a common directory."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["representation rights", "mandates", "common directory"],
            primary_terms=["representation rights", "mandates", "secure channel", "common directory"],
            support_groups=[
                ["digital management of representation rights and mandates"],
                ["secure channel for exchanging official documents and attestations supported by a common directory"],
            ],
            contradiction_groups=[["no common directory or secure channel"]],
            grouping_label="Architecture and layering",
        ),
        ClaimTarget(
            target_id="eubw_arf_subordination",
            claim_text=(
                "Proposal-stage EUBW sources treat the Architecture and Reference Framework as applicable helper material, "
                "with regulation specifications taking precedence where they conflict."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["architecture and reference framework", "specifications", "precedence"],
            primary_terms=["architecture and reference framework", "taking precedence", "inconsistency"],
            support_groups=[
                ["architecture and reference framework", "should apply"],
                ["specifications laid down in this regulation taking precedence"],
            ],
            contradiction_groups=[["arf overrides the regulation"]],
            grouping_label="Architecture and layering",
        ),
        ClaimTarget(
            target_id="eubw_identifier_delegated_specs",
            claim_text=(
                "Proposal-stage EUBW sources delegate the detailed structure and technical specifications "
                "of the business-wallet identifier to implementing acts."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["identifier", "technical specifications", "implementing acts"],
            primary_terms=["structure", "technical specifications", "identifier", "implementing acts"],
            support_groups=[
                ["structure and technical specifications of this identifier", "will be defined by implementing acts"],
            ],
            contradiction_groups=[["identifier structure is fully fixed in the proposal text"]],
            grouping_label="Governance and discretion",
        ),
        ClaimTarget(
            target_id="eubw_access_control_delegated_specs",
            claim_text=(
                "Proposal-stage EUBW sources delegate detailed access-control formats, interoperability mechanisms, "
                "protocols, and logging requirements to implementing acts."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION],
            scope_terms=["access control mechanism", "implementing acts", "protocols", "logging"],
            primary_terms=["reference standards", "technical specifications", "protocols", "logging"],
            support_groups=[
                ["list of reference standards, technical specifications and procedures", "shall be defined in the implementing acts"],
                ["formats for the representation of roles and attributes"],
                ["requirements for secure logging, timestamping and auditability of authorisation events"],
            ],
            contradiction_groups=[["all access-control details are fully specified already"]],
            grouping_label="Governance and discretion",
        ),
        ClaimTarget(
            target_id="eubw_trust_model_still_open",
            claim_text=(
                "Proposal-stage EUBW sources leave room for later assessment of concrete trust models "
                "and alternative standards rather than fixing one final model now."
            ),
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.REGULATION],
            scope_terms=["trust models", "alternative standards", "assessed"],
            primary_terms=["trust models", "alternative standards", "assessed"],
            support_groups=[
                ["trust models that have proven their efficacy and security", "should be assessed"],
                ["new or alternative standards", "could be implemented"],
            ],
            contradiction_groups=[["the proposal fixes one immutable trust model"]],
            grouping_label="Architecture and layering",
        ),
    ]


def analyze_query(question: str, terminology: TerminologyConfig) -> QueryIntent:
    normalized_question = normalize_query_terms(question, terminology)
    lowered = normalize_text_for_matching(normalized_question)
    original_lowered = normalize_text_for_matching(question)
    tokens = token_set(normalized_question)
    eu_first = True

    if _is_eubw_role_boundary_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="eubw_role_boundary_analysis",
            eu_first=eu_first,
            claim_targets=_eubw_role_boundary_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
            answer_pattern="eubw_role_boundaries",
        )

    if _is_eubw_lifecycle_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="eubw_lifecycle_analysis",
            eu_first=eu_first,
            claim_targets=_eubw_lifecycle_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
            answer_pattern="eubw_lifecycle",
        )

    if _is_eubw_audit_trail_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="eubw_audit_trail_analysis",
            eu_first=eu_first,
            claim_targets=_eubw_audit_trail_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
            answer_pattern="eubw_audit_trails",
        )

    if _is_eubw_identity_authority_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="eubw_identity_authority_analysis",
            eu_first=eu_first,
            claim_targets=_eubw_identity_authority_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
            answer_pattern="eubw_identity_authority",
        )

    if _is_eubw_architecture_bucket_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="eubw_architecture_bucket_analysis",
            eu_first=eu_first,
            claim_targets=_eubw_architecture_bucket_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
            answer_pattern="eubw_architecture_buckets",
        )

    if _is_protocol_authorization_server_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="protocol_authorization_server_comparison",
            eu_first=False,
            claim_targets=_protocol_comparison_targets(),
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD],
        )

    if _is_registration_scope_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="registration_certificate_scope",
            eu_first=eu_first,
            claim_targets=_registration_mandatory_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.NATIONAL_IMPLEMENTATION,
            ],
        )

    if _is_germany_wallet_implementation_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="germany_wallet_implementation_status",
            eu_first=eu_first,
            claim_targets=_germany_wallet_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.NATIONAL_IMPLEMENTATION,
                SourceKind.PROJECT_ARTIFACT,
            ],
        )

    if _is_certificate_topology_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="certificate_topology_analysis",
            eu_first=eu_first,
            claim_targets=_certificate_topology_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
            answer_pattern="certificate_topology",
            undefined_terms=[
                "derived certificate",
                "derived access certificate",
                "derived registration certificate",
            ],
        )

    if _is_relying_party_registration_information_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="relying_party_registration_information",
            eu_first=eu_first,
            claim_targets=_relying_party_registration_information_targets(),
            preferred_kinds=[
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.REGULATION,
                SourceKind.PROJECT_ARTIFACT,
            ],
        )

    if _is_relying_party_certificate_question(
        lowered,
        original_lowered=original_lowered,
    ):
        return QueryIntent(
            question=question,
            intent_type="relying_party_certificate_requirements",
            eu_first=eu_first,
            claim_targets=_relying_party_certificate_targets(),
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.REGULATION],
        )

    if (
        "access certificate" in lowered
        or "registration and access certificate" in lowered
        or (
            _has_business_wallet_subject(lowered, tokens)
            and _token_overlap(tokens, ["access", "certificate", "guidance", "national"]) >= 2
        )
    ):
        return QueryIntent(
            question=question,
            intent_type="certificate_layer_analysis",
            eu_first=eu_first,
            claim_targets=_certificate_layer_targets(),
            preferred_kinds=[
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.NATIONAL_IMPLEMENTATION,
                SourceKind.SCIENTIFIC_LITERATURE,
            ],
        )

    if _is_business_wallet_requirements_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="wallet_requirements_summary",
            eu_first=eu_first,
            claim_targets=_wallet_requirements_targets(),
            preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
        )

    if _is_arf_boundary_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="arf_boundary_check",
            eu_first=False,
            claim_targets=_arf_boundary_targets(),
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD, SourceKind.PROJECT_ARTIFACT],
        )

    regulation_targets = [
        ClaimTarget(
            target_id="broad_regulatory_answer",
            claim_text="The answer requires EU-level regulatory support before national or project material.",
            claim_type=ClaimType.SYNTHESIS,
            required_source_role_level=SourceRoleLevel.HIGH,
            preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
            scope_terms=["regulation", "union"],
            primary_terms=["requirement", "article"],
            support_groups=[["article"]],
            contradiction_groups=[["optional everywhere"]],
            grouping_label="Governance and discretion",
        )
    ]
    return QueryIntent(
        question=question,
        intent_type="broad_regulation_question",
        eu_first=eu_first,
        claim_targets=regulation_targets,
        preferred_kinds=[
            SourceKind.REGULATION,
            SourceKind.IMPLEMENTING_ACT,
            SourceKind.TECHNICAL_STANDARD,
        ],
        clarification_note="Broad question: continue with an EU-first first-pass answer.",
    )


def build_target_query_text(question: str, target: ClaimTarget) -> str:
    support_terms = [" ".join(group) for group in target.support_groups]
    return " ".join(
        [
            question,
            target.claim_text,
            " ".join(target.scope_terms),
            " ".join(target.primary_terms),
            " ".join(support_terms),
        ]
    )


def build_retrieval_plan(
    query_intent: QueryIntent,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
    terminology: TerminologyConfig,
) -> RetrievalPlan:
    hierarchy_kinds = [rule.source_kind for rule in sorted(hierarchy.rules, key=lambda item: item.rank)]
    normalized_question, question_term_normalizations = normalize_query_terms_with_trace(
        query_intent.question,
        terminology,
    )
    target_queries: List[RetrievalTargetQuery] = []
    for target in query_intent.claim_targets:
        raw_query = build_target_query_text(query_intent.question, target)
        normalized_target_query, applied_target_normalizations = normalize_query_terms_with_trace(
            raw_query,
            terminology,
        )
        target_queries.append(
            RetrievalTargetQuery(
                target_id=target.target_id,
                raw_query=raw_query,
                normalized_query=normalized_target_query,
                applied_term_normalizations=applied_target_normalizations,
            )
        )

    if query_intent.eu_first:
        # In EU-first mode, query preferences must not pull lower-ranked material
        # ahead of higher-ranked governing layers.
        kinds = hierarchy_kinds
    else:
        preferred: List[SourceKind] = []
        for kind in query_intent.preferred_kinds:
            if kind not in preferred:
                preferred.append(kind)
        remaining = [kind for kind in hierarchy_kinds if kind not in preferred]
        kinds = preferred + remaining

    steps = [
        RetrievalPlanStep(
            step_id=f"step_{index + 1}",
            required_kind=kind,
            required_source_role_level=hierarchy.role_for(kind),
            inspection_depth=runtime_config.retrieval_top_k,
            reason=f"Search {kind.value} sources in ranked order.",
        )
        for index, kind in enumerate(kinds)
    ]
    return RetrievalPlan(
        question=query_intent.question,
        normalized_question=normalized_question,
        question_term_normalizations=question_term_normalizations,
        target_queries=target_queries,
        steps=steps,
        local_retrieval_backend=runtime_config.local_retrieval_backend,
        local_index_candidate_pool=runtime_config.local_index_candidate_pool,
    )
