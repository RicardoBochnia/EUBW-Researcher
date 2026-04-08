from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.config import load_runtime_config, load_source_hierarchy
from eubw_researcher.corpus import ingest_catalog, load_source_catalog
from eubw_researcher.models import SourceKind, SourceRoleLevel
from eubw_researcher.retrieval import analyze_query, build_retrieval_plan, retrieve_candidates


REPO_ROOT = Path(__file__).resolve().parents[2]


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.yaml")
        self.hierarchy = load_source_hierarchy(REPO_ROOT / "configs" / "source_hierarchy.yaml")
        catalog = load_source_catalog(
            REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        )
        self.bundle = ingest_catalog(catalog)

    def test_analyze_query_classifies_registration_mandatory_question(self) -> None:
        intent = analyze_query(
            "Is the registration certificate mandatory at EU level, or is that delegated to member states?"
        )
        self.assertEqual(intent.intent_type, "registration_certificate_scope")
        self.assertEqual(len(intent.claim_targets), 2)
        self.assertEqual(intent.preferred_kinds[0], SourceKind.REGULATION)

    def test_analyze_query_classifies_primary_business_wallet_requirements_question(self) -> None:
        intent = analyze_query(
            "What requirements apply to the Business Wallet, and how can they be provisionally structured?"
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertTrue(any(target.grouping_label for target in intent.claim_targets))
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_business_wallet_requirements_route_is_not_shadowed_by_specific_registration_paths(self) -> None:
        intent = analyze_query(
            "What requirements apply to a business wallet relying party?"
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")

    def test_build_retrieval_plan_uses_hierarchy_config_role_levels(self) -> None:
        intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime)
        first_step = plan.steps[0]
        self.assertEqual(first_step.required_kind, SourceKind.TECHNICAL_STANDARD)
        self.assertEqual(first_step.required_source_role_level, SourceRoleLevel.HIGH)

    def test_build_retrieval_plan_preserves_global_hierarchy_for_eu_first_registration_question(self) -> None:
        intent = analyze_query(
            "Is the registration certificate mandatory at EU level, or is that delegated to member states?"
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime)
        self.assertEqual(
            [step.required_kind for step in plan.steps],
            [
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.TECHNICAL_STANDARD,
                SourceKind.PROJECT_ARTIFACT,
                SourceKind.SCIENTIFIC_LITERATURE,
                SourceKind.NATIONAL_IMPLEMENTATION,
                SourceKind.COMMENTARY,
            ],
        )

    def test_retrieve_candidates_returns_inspected_top_k_with_threshold_flags(self) -> None:
        intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime)
        candidates = retrieve_candidates(
            question=intent.question,
            step=plan.steps[0],
            bundle=self.bundle,
            hierarchy=self.hierarchy,
            runtime_config=self.runtime,
        )
        self.assertLessEqual(len(candidates), self.runtime.retrieval_top_k)
        self.assertTrue(any(candidate.meets_threshold for candidate in candidates))
        self.assertEqual(candidates[0].chunk.source_kind, SourceKind.TECHNICAL_STANDARD)

    def test_analyze_query_classifies_relying_party_registration_information_question(self) -> None:
        intent = analyze_query(
            "What information must a wallet-relying party provide during relying party registration?"
        )
        self.assertEqual(intent.intent_type, "relying_party_registration_information")
        self.assertEqual(len(intent.claim_targets), 2)
        self.assertEqual(intent.preferred_kinds[0], SourceKind.IMPLEMENTING_ACT)

    def test_analyze_query_classifies_relying_party_certificate_question(self) -> None:
        intent = analyze_query(
            "What is the difference between a wallet-relying party registration certificate and a wallet-relying party access certificate?"
        )
        self.assertEqual(intent.intent_type, "relying_party_certificate_requirements")
        self.assertEqual(len(intent.claim_targets), 3)
        self.assertEqual(intent.preferred_kinds[0], SourceKind.IMPLEMENTING_ACT)

    def test_single_certificate_question_does_not_route_to_certificate_comparison(self) -> None:
        intent = analyze_query(
            "What requirements apply to a wallet-relying party access certificate?"
        )
        self.assertEqual(intent.intent_type, "certificate_layer_analysis")
        self.assertNotEqual(intent.intent_type, "relying_party_certificate_requirements")

    def test_analyze_query_classifies_certificate_topology_anchor_question(self) -> None:
        intent = analyze_query(
            "Gibt es abgeleitete Access bzw. Registration Certificates? Also kann eine Wallet-Relying-Party mehrere solcher Zertifikate besitzen oder gibt es nur Hauptzertifikat fuer die Ganze Organisation?"
        )
        self.assertEqual(intent.intent_type, "certificate_topology_analysis")
        self.assertGreaterEqual(len(intent.claim_targets), 5)
        self.assertEqual(intent.answer_pattern, "certificate_topology")
        self.assertIn("derived certificate", intent.undefined_terms)

    def test_analyze_query_generalizes_out_of_distribution_business_wallet_question(self) -> None:
        intent = analyze_query(
            "Map the Union-level obligations for Business Wallet relying parties and cluster them provisionally for research notes."
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_eubw_alias_routes_to_business_wallet_requirements_path(self) -> None:
        intent = analyze_query(
            "What requirements apply to the EUBW, and how can they be provisionally structured?"
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_protocol_paraphrase_stays_on_protocol_comparison_route(self) -> None:
        intent = analyze_query(
            "Compare OpenID4VCI and OpenID4VP on token endpoint use and wallet metadata handling."
        )
        self.assertEqual(intent.intent_type, "protocol_authorization_server_comparison")
        self.assertFalse(intent.eu_first)
        self.assertEqual(intent.preferred_kinds, [SourceKind.TECHNICAL_STANDARD])
        self.assertIsNone(intent.answer_pattern)

    def test_build_retrieval_plan_keeps_protocol_questions_non_eu_first(self) -> None:
        intent = analyze_query(
            "Compare OpenID4VCI and OpenID4VP on token endpoint use and wallet metadata handling."
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime)
        self.assertEqual(
            [step.required_kind for step in plan.steps[:4]],
            [
                SourceKind.TECHNICAL_STANDARD,
                SourceKind.REGULATION,
                SourceKind.IMPLEMENTING_ACT,
                SourceKind.PROJECT_ARTIFACT,
            ],
        )

    def test_topology_language_wins_over_generic_certificate_layer_route(self) -> None:
        intent = analyze_query(
            "Can a wallet-relying party hold multiple access and registration certificates per intended use, "
            "or is there only a single organisation-level certificate?"
        )
        self.assertEqual(intent.intent_type, "certificate_topology_analysis")
        self.assertEqual(intent.answer_pattern, "certificate_topology")
        self.assertGreaterEqual(len(intent.claim_targets), 5)

    def test_authorisation_spelling_routes_consistently_with_protocol_question(self) -> None:
        canonical_intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
        )
        normalized_intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorisation server?"
        )
        self.assertEqual(normalized_intent.intent_type, canonical_intent.intent_type)
        self.assertEqual(normalized_intent.preferred_kinds, canonical_intent.preferred_kinds)
        normalized_plan = build_retrieval_plan(normalized_intent, self.hierarchy, self.runtime)
        canonical_plan = build_retrieval_plan(canonical_intent, self.hierarchy, self.runtime)
        self.assertEqual(
            [step.required_kind for step in normalized_plan.steps[:4]],
            [step.required_kind for step in canonical_plan.steps[:4]],
        )

    def test_analyze_query_classifies_certificate_layer_guidance_question(self) -> None:
        intent = analyze_query(
            "What national guidance exists for Business Wallet access certificate handling?"
        )
        self.assertEqual(intent.intent_type, "certificate_layer_analysis")
        self.assertEqual(intent.preferred_kinds[0], SourceKind.REGULATION)
        self.assertIn(SourceKind.NATIONAL_IMPLEMENTATION, intent.preferred_kinds)
        self.assertTrue(any(target.grouping_label for target in intent.claim_targets))

    def test_wallet_specific_access_cert_alias_routes_to_certificate_layer_analysis(self) -> None:
        intent = analyze_query(
            "What national guidance exists for Business Wallet access cert handling?"
        )
        self.assertEqual(intent.intent_type, "certificate_layer_analysis")
        self.assertIn(SourceKind.NATIONAL_IMPLEMENTATION, intent.preferred_kinds)

    def test_analyze_query_classifies_arf_boundary_question(self) -> None:
        intent = analyze_query(
            "Does the ARF require a verifier authorization server in the presentation flow?"
        )
        self.assertEqual(intent.intent_type, "arf_boundary_check")
        self.assertFalse(intent.eu_first)
        self.assertEqual(
            intent.preferred_kinds,
            [SourceKind.TECHNICAL_STANDARD, SourceKind.PROJECT_ARTIFACT],
        )
        self.assertEqual(len(intent.claim_targets), 2)

    def test_analyze_query_falls_back_to_broad_regulation_question(self) -> None:
        intent = analyze_query(
            "Give me an overview of Union rules for business wallet supervision."
        )
        self.assertEqual(intent.intent_type, "broad_regulation_question")
        self.assertTrue(intent.eu_first)
        self.assertEqual(
            intent.preferred_kinds[:2],
            [SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT],
        )
        self.assertEqual(
            intent.clarification_note,
            "Broad question: continue with an EU-first first-pass answer.",
        )

    def test_api_client_access_cert_without_wallet_context_routes_to_broad_fallback(self) -> None:
        intent = analyze_query(
            "How should we rotate an access cert for internal API clients?"
        )
        self.assertEqual(intent.intent_type, "broad_regulation_question")
        self.assertEqual(
            intent.clarification_note,
            "Broad question: continue with an EU-first first-pass answer.",
        )

    def test_unrelated_broad_question_keeps_existing_fallback_route(self) -> None:
        intent = analyze_query(
            "Give me an overview of Union rules for company supervision."
        )
        self.assertEqual(intent.intent_type, "broad_regulation_question")
        self.assertEqual(
            intent.clarification_note,
            "Broad question: continue with an EU-first first-pass answer.",
        )

    def test_analyze_query_classifies_germany_wallet_question_with_umlauts(self) -> None:
        intent = analyze_query(
            "Wie ist der Stand der SPRIND-EUDI-Wallet und des eIDAS-Durchführungsgesetzes in Deutschland?"
        )
        self.assertEqual(intent.intent_type, "germany_wallet_implementation_status")
        self.assertTrue(intent.eu_first)
        self.assertIn(SourceKind.NATIONAL_IMPLEMENTATION, intent.preferred_kinds)
        self.assertIn(SourceKind.PROJECT_ARTIFACT, intent.preferred_kinds)
