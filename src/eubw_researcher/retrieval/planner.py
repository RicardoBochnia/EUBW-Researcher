from __future__ import annotations

import re
from typing import List

from eubw_researcher.models import (
    ClaimTarget,
    ClaimType,
    QueryIntent,
    RetrievalPlan,
    RetrievalPlanStep,
    RuntimeConfig,
    SourceHierarchyConfig,
    SourceKind,
    SourceRoleLevel,
)


def _contains_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _token_set(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _phrase_score(text: str, phrases: List[str]) -> int:
    return sum(1 for phrase in phrases if phrase in text)


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
            preferred_kinds=[SourceKind.IMPLEMENTING_ACT, SourceKind.REGULATION],
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
            preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
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
    tokens = _token_set(lowered)
    return (
        _has_business_wallet_subject(lowered, tokens)
        and ("registration" in tokens or "register" in tokens)
        and _is_information_request(lowered, tokens)
    )


def _is_relying_party_certificate_question(lowered: str) -> bool:
    tokens = _token_set(lowered)
    return (
        _has_business_wallet_subject(lowered, tokens)
        and _contains_any(lowered, ["registration certificate", "access certificate"])
        and _is_comparison_request(lowered, tokens)
    )


def _is_certificate_topology_question(lowered: str) -> bool:
    tokens = _token_set(lowered)
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
    tokens = _token_set(lowered)
    return _has_business_wallet_subject(lowered, tokens) and _is_requirements_request(lowered, tokens)


def _is_registration_scope_question(lowered: str) -> bool:
    tokens = _token_set(lowered)
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
    tokens = _token_set(lowered)
    return (
        _contains_any(lowered, ["openid4vci", "openid4vp"])
        and (
            _contains_any(lowered, ["authorization server", "token endpoint", "wallet metadata"])
            or _is_comparison_request(lowered, tokens)
            or _token_overlap(tokens, ["wallet", "metadata", "authorization", "server", "token", "endpoint"]) >= 3
        )
    )


def _is_arf_boundary_question(lowered: str) -> bool:
    tokens = _token_set(lowered)
    return "arf" in lowered and (
        _contains_any(lowered, ["authorization server", "verifier", "presentation flow"])
        or _token_overlap(tokens, ["authorization", "server", "verifier", "presentation", "flow"]) >= 3
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


def analyze_query(question: str) -> QueryIntent:
    lowered = question.lower()
    tokens = _token_set(lowered)
    eu_first = True

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

    if _is_business_wallet_requirements_question(lowered):
        return QueryIntent(
            question=question,
            intent_type="wallet_requirements_summary",
            eu_first=eu_first,
            claim_targets=_wallet_requirements_targets(),
            preferred_kinds=[SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
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

    if _is_relying_party_certificate_question(lowered):
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


def build_retrieval_plan(
    query_intent: QueryIntent,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
) -> RetrievalPlan:
    hierarchy_kinds = [rule.source_kind for rule in sorted(hierarchy.rules, key=lambda item: item.rank)]

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
    return RetrievalPlan(question=query_intent.question, steps=steps)
