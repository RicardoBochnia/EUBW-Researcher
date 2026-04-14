from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.config import (
    load_runtime_config,
    load_source_hierarchy,
    load_terminology_config,
)
from eubw_researcher.corpus import ingest_catalog, load_source_catalog
from eubw_researcher.models import (
    AnchorQuality,
    AppliedTermNormalization,
    Citation,
    CitationQuality,
    DocumentStatus,
    IngestionBundle,
    RetrievalPlanStep,
    SourceCatalog,
    SourceCatalogEntry,
    SourceChunk,
    SourceDocument,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
)
from eubw_researcher.retrieval import (
    analyze_query,
    build_retrieval_plan,
    retrieve_candidates,
    retrieve_candidates_with_trace,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.yaml")
        self.hierarchy = load_source_hierarchy(REPO_ROOT / "configs" / "source_hierarchy.yaml")
        self.terminology = load_terminology_config(REPO_ROOT / "configs" / "terminology.yaml")
        catalog = load_source_catalog(
            REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        )
        self.bundle = ingest_catalog(catalog)

    def _build_synthetic_document(
        self,
        *,
        source_id: str,
        chunk_id: str,
        title: str,
        source_kind: SourceKind,
        source_role_level: SourceRoleLevel,
        text: str,
    ) -> SourceDocument:
        entry = SourceCatalogEntry(
            source_id=source_id,
            title=title,
            source_kind=source_kind,
            source_role_level=source_role_level,
            jurisdiction="EU",
            publication_status=None,
            publication_date=None,
            local_path=None,
            canonical_url=None,
            document_status=DocumentStatus.FINAL,
            source_origin=SourceOrigin.LOCAL,
        )
        citation = Citation(
            source_id=source_id,
            document_title=title,
            source_role_level=source_role_level,
            source_kind=source_kind,
            jurisdiction="EU",
            citation_quality=CitationQuality.ANCHOR_GROUNDED,
            document_path=None,
            canonical_url=None,
            document_status=DocumentStatus.FINAL,
            source_origin=SourceOrigin.LOCAL,
            anchor_label="Article 1",
        )
        chunk = SourceChunk(
            source_id=source_id,
            chunk_id=chunk_id,
            title=title,
            source_kind=source_kind,
            source_role_level=source_role_level,
            source_origin=SourceOrigin.LOCAL,
            jurisdiction="EU",
            text=text,
            citation=citation,
            document_status=DocumentStatus.FINAL,
            anchor_quality=AnchorQuality.STRONG,
        )
        return SourceDocument(
            entry=entry,
            text=text,
            chunks=[chunk],
            anchor_quality=AnchorQuality.STRONG,
            structure_poor=False,
            technical_anchor_failure=False,
            anchor_audit=None,
        )

    def _build_synthetic_bundle(self, *documents: SourceDocument) -> IngestionBundle:
        return IngestionBundle(
            catalog=SourceCatalog(entries=[document.entry for document in documents]),
            documents=list(documents),
            report=[],
        )

    def test_analyze_query_classifies_registration_mandatory_question(self) -> None:
        intent = analyze_query(
            "Is the registration certificate mandatory at EU level, or is that delegated to member states?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "registration_certificate_scope")
        self.assertEqual(len(intent.claim_targets), 2)
        self.assertEqual(intent.preferred_kinds[0], SourceKind.REGULATION)

    def test_analyze_query_classifies_primary_business_wallet_requirements_question(self) -> None:
        intent = analyze_query(
            "What requirements apply to the Business Wallet, and how can they be provisionally structured?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertTrue(any(target.grouping_label for target in intent.claim_targets))
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_business_wallet_requirements_route_is_not_shadowed_by_specific_registration_paths(self) -> None:
        intent = analyze_query(
            "What requirements apply to a business wallet relying party?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")

    def test_build_retrieval_plan_uses_hierarchy_config_role_levels(self) -> None:
        intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?",
            self.terminology,
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)
        first_step = plan.steps[0]
        self.assertEqual(first_step.required_kind, SourceKind.TECHNICAL_STANDARD)
        self.assertEqual(first_step.required_source_role_level, SourceRoleLevel.HIGH)

    def test_build_retrieval_plan_preserves_global_hierarchy_for_eu_first_registration_question(self) -> None:
        intent = analyze_query(
            "Is the registration certificate mandatory at EU level, or is that delegated to member states?",
            self.terminology,
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)
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

    def test_build_retrieval_plan_records_local_backend_trace_fields(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.sqlite_fts.yaml")
        intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?",
            self.terminology,
        )

        plan = build_retrieval_plan(intent, self.hierarchy, runtime, self.terminology)

        self.assertEqual(plan.local_retrieval_backend, "sqlite_fts")
        self.assertEqual(
            plan.local_index_candidate_pool,
            runtime.local_index_candidate_pool,
        )

    def test_retrieve_candidates_returns_inspected_top_k_with_threshold_flags(self) -> None:
        intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?",
            self.terminology,
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)
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

    def test_sqlite_fts_filters_per_step_before_candidate_cap(self) -> None:
        runtime = replace(
            self.runtime,
            retrieval_top_k=1,
            min_combined_score=0.0,
            local_retrieval_backend="sqlite_fts",
            local_index_candidate_pool=1,
        )
        step = RetrievalPlanStep(
            step_id="regulation_only",
            required_kind=SourceKind.REGULATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            inspection_depth=1,
            reason="Synthetic regulation step",
        )
        commentary_doc = self._build_synthetic_document(
            source_id="commentary-1",
            chunk_id="commentary-1",
            title="Commentary",
            source_kind=SourceKind.COMMENTARY,
            source_role_level=SourceRoleLevel.HIGH,
            text="access certificate access certificate access certificate",
        )
        regulation_doc = self._build_synthetic_document(
            source_id="regulation-1",
            chunk_id="regulation-1",
            title="Regulation",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="access certificate",
        )
        bundle = self._build_synthetic_bundle(commentary_doc, regulation_doc)

        candidates, trace = retrieve_candidates_with_trace(
            question="access certificate",
            step=step,
            bundle=bundle,
            hierarchy=self.hierarchy,
            runtime_config=runtime,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].chunk.source_kind, SourceKind.REGULATION)
        self.assertEqual(candidates[0].chunk.source_id, "regulation-1")
        self.assertEqual(trace.cache_status, "memory")
        self.assertFalse(trace.fallback_used)

    def test_sqlite_fts_backfills_from_same_step_scan_when_candidate_pool_is_sparse(self) -> None:
        runtime = replace(
            self.runtime,
            retrieval_top_k=2,
            min_combined_score=0.0,
            local_retrieval_backend="sqlite_fts",
            local_index_candidate_pool=2,
        )
        step = RetrievalPlanStep(
            step_id="regulation_backfill",
            required_kind=SourceKind.REGULATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            inspection_depth=2,
            reason="Synthetic regulation step",
        )
        first_doc = self._build_synthetic_document(
            source_id="regulation-1",
            chunk_id="regulation-1",
            title="Regulation One",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="access certificate for wallet relying parties",
        )
        second_doc = self._build_synthetic_document(
            source_id="regulation-2",
            chunk_id="regulation-2",
            title="Regulation Two",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="registration certificate and access certificate",
        )
        bundle = self._build_synthetic_bundle(first_doc, second_doc)

        with patch(
            "eubw_researcher.retrieval.local._load_or_build_sqlite_index",
            return_value=SimpleNamespace(
                cache_status="memory",
                query_step=lambda **_kwargs: ["regulation-1"],
            ),
        ):
            candidates, trace = retrieve_candidates_with_trace(
                question="access certificate",
                step=step,
                bundle=bundle,
                hierarchy=self.hierarchy,
                runtime_config=runtime,
            )

        self.assertEqual({candidate.chunk.source_id for candidate in candidates}, {"regulation-1", "regulation-2"})
        self.assertTrue(trace.fallback_used)
        self.assertEqual(trace.cache_status, "memory")

    def test_sqlite_fts_backfills_semantic_only_candidates_when_match_pool_is_full(self) -> None:
        runtime = replace(
            self.runtime,
            retrieval_top_k=3,
            min_combined_score=0.0,
            local_retrieval_backend="sqlite_fts",
            local_index_candidate_pool=3,
        )
        step = RetrievalPlanStep(
            step_id="regulation_semantic_backfill",
            required_kind=SourceKind.REGULATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            inspection_depth=3,
            reason="Synthetic regulation step",
        )
        weak_exact_a = self._build_synthetic_document(
            source_id="regulation-1",
            chunk_id="regulation-1",
            title="Regulation One",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="metadata",
        )
        weak_exact_b = self._build_synthetic_document(
            source_id="regulation-2",
            chunk_id="regulation-2",
            title="Regulation Two",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="session",
        )
        weak_exact_c = self._build_synthetic_document(
            source_id="regulation-3",
            chunk_id="regulation-3",
            title="Regulation Three",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="wallet",
        )
        semantic_only = self._build_synthetic_document(
            source_id="regulation-4",
            chunk_id="regulation-4",
            title="Regulation Four",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="authorisation authz as issuance",
        )
        bundle = self._build_synthetic_bundle(
            weak_exact_a,
            weak_exact_b,
            weak_exact_c,
            semantic_only,
        )

        with patch(
            "eubw_researcher.retrieval.local._load_or_build_sqlite_index",
            return_value=SimpleNamespace(
                cache_status="memory",
                query_step=lambda **_kwargs: [
                    "regulation-1",
                    "regulation-2",
                    "regulation-3",
                ],
            ),
        ):
            candidates, trace = retrieve_candidates_with_trace(
                question="authorization server credential wallet metadata session",
                step=step,
                bundle=bundle,
                hierarchy=self.hierarchy,
                runtime_config=runtime,
            )

        self.assertEqual(
            [candidate.chunk.source_id for candidate in candidates],
            ["regulation-4", "regulation-1", "regulation-2"],
        )
        self.assertTrue(trace.fallback_used)
        self.assertEqual(trace.cache_status, "memory")

    def test_sqlite_fts_errors_fall_back_to_same_step_scan(self) -> None:
        runtime = replace(
            self.runtime,
            retrieval_top_k=1,
            min_combined_score=0.0,
            local_retrieval_backend="sqlite_fts",
            local_index_candidate_pool=1,
        )
        step = RetrievalPlanStep(
            step_id="regulation_error_fallback",
            required_kind=SourceKind.REGULATION,
            required_source_role_level=SourceRoleLevel.HIGH,
            inspection_depth=1,
            reason="Synthetic regulation step",
        )
        regulation_doc = self._build_synthetic_document(
            source_id="regulation-1",
            chunk_id="regulation-1",
            title="Regulation",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            text="access certificate",
        )
        bundle = self._build_synthetic_bundle(regulation_doc)

        with patch(
            "eubw_researcher.retrieval.local._load_or_build_sqlite_index",
            side_effect=RuntimeError("fts unavailable"),
        ):
            candidates, trace = retrieve_candidates_with_trace(
                question="access certificate",
                step=step,
                bundle=bundle,
                hierarchy=self.hierarchy,
                runtime_config=runtime,
            )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].chunk.source_id, "regulation-1")
        self.assertEqual(trace.cache_status, "error_fallback_scan")
        self.assertTrue(trace.fallback_used)

    def test_analyze_query_classifies_relying_party_registration_information_question(self) -> None:
        intent = analyze_query(
            "What information must a wallet-relying party provide during relying party registration?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "relying_party_registration_information")
        self.assertEqual(len(intent.claim_targets), 2)
        self.assertEqual(intent.preferred_kinds[0], SourceKind.IMPLEMENTING_ACT)

    def test_analyze_query_classifies_relying_party_certificate_question(self) -> None:
        intent = analyze_query(
            "What is the difference between a wallet-relying party registration certificate and a wallet-relying party access certificate?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "relying_party_certificate_requirements")
        self.assertEqual(len(intent.claim_targets), 3)
        self.assertEqual(intent.preferred_kinds[0], SourceKind.IMPLEMENTING_ACT)

    def test_single_certificate_question_does_not_route_to_certificate_comparison(self) -> None:
        intent = analyze_query(
            "What requirements apply to a wallet-relying party access certificate?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "certificate_layer_analysis")
        self.assertNotEqual(intent.intent_type, "relying_party_certificate_requirements")

    def test_analyze_query_classifies_certificate_topology_anchor_question(self) -> None:
        intent = analyze_query(
            "Gibt es abgeleitete Access bzw. Registration Certificates? Also kann eine Wallet-Relying-Party mehrere solcher Zertifikate besitzen oder gibt es nur Hauptzertifikat fuer die Ganze Organisation?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "certificate_topology_analysis")
        self.assertGreaterEqual(len(intent.claim_targets), 5)
        self.assertEqual(intent.answer_pattern, "certificate_topology")
        self.assertIn("derived certificate", intent.undefined_terms)

    def test_analyze_query_generalizes_out_of_distribution_business_wallet_question(self) -> None:
        intent = analyze_query(
            "Map the Union-level obligations for Business Wallet relying parties and cluster them provisionally for research notes.",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_eubw_alias_routes_to_business_wallet_requirements_path(self) -> None:
        intent = analyze_query(
            "What requirements apply to the EUBW, and how can they be provisionally structured?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_ebw_alias_routes_to_business_wallet_requirements_path(self) -> None:
        intent = analyze_query(
            "What requirements apply to the EBW, and how can they be provisionally structured?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        self.assertGreaterEqual(len(intent.claim_targets), 4)

    def test_protocol_paraphrase_stays_on_protocol_comparison_route(self) -> None:
        intent = analyze_query(
            "Compare OpenID4VCI and OpenID4VP on token endpoint use and wallet metadata handling.",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "protocol_authorization_server_comparison")
        self.assertFalse(intent.eu_first)
        self.assertEqual(intent.preferred_kinds, [SourceKind.TECHNICAL_STANDARD])
        self.assertIsNone(intent.answer_pattern)

    def test_build_retrieval_plan_keeps_protocol_questions_non_eu_first(self) -> None:
        intent = analyze_query(
            "Compare OpenID4VCI and OpenID4VP on token endpoint use and wallet metadata handling.",
            self.terminology,
        )
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)
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
            "or is there only a single organisation-level certificate?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "certificate_topology_analysis")
        self.assertEqual(intent.answer_pattern, "certificate_topology")
        self.assertGreaterEqual(len(intent.claim_targets), 5)

    def test_authorisation_spelling_routes_consistently_with_protocol_question(self) -> None:
        canonical_intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?",
            self.terminology,
        )
        normalized_intent = analyze_query(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorisation server?",
            self.terminology,
        )
        self.assertEqual(normalized_intent.intent_type, canonical_intent.intent_type)
        self.assertEqual(normalized_intent.preferred_kinds, canonical_intent.preferred_kinds)
        normalized_plan = build_retrieval_plan(
            normalized_intent,
            self.hierarchy,
            self.runtime,
            self.terminology,
        )
        canonical_plan = build_retrieval_plan(
            canonical_intent,
            self.hierarchy,
            self.runtime,
            self.terminology,
        )
        self.assertEqual(
            [step.required_kind for step in normalized_plan.steps[:4]],
            [step.required_kind for step in canonical_plan.steps[:4]],
        )

    def test_analyze_query_classifies_certificate_layer_guidance_question(self) -> None:
        intent = analyze_query(
            "What national guidance exists for Business Wallet access certificate handling?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "certificate_layer_analysis")
        self.assertEqual(intent.preferred_kinds[0], SourceKind.REGULATION)
        self.assertIn(SourceKind.NATIONAL_IMPLEMENTATION, intent.preferred_kinds)
        self.assertTrue(any(target.grouping_label for target in intent.claim_targets))

    def test_wallet_specific_access_cert_alias_routes_to_certificate_layer_analysis(self) -> None:
        intent = analyze_query(
            "What national guidance exists for Business Wallet access cert handling?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "certificate_layer_analysis")
        self.assertIn(SourceKind.NATIONAL_IMPLEMENTATION, intent.preferred_kinds)

    def test_wrpac_and_wrprc_aliases_route_to_certificate_comparison_path(self) -> None:
        intent = analyze_query(
            "What is the difference between the wallet-relying party WRPAC and WRPRC?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "relying_party_certificate_requirements")
        self.assertEqual(len(intent.claim_targets), 3)

    def test_rpac_alias_without_wallet_context_stays_on_broad_fallback(self) -> None:
        intent = analyze_query(
            "How should our API gateway rotate an RPAC for internal access control?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "broad_regulation_question")

    def test_pid_provider_alias_improves_wallet_query_normalization_without_new_router_branch(self) -> None:
        intent = analyze_query(
            "What requirements apply when a Business Wallet PID provider registers?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "wallet_requirements_summary")
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)
        self.assertEqual(
            plan.normalized_question,
            (
                "What requirements apply when a Business Wallet "
                "provider of person identification data registers?"
            ),
        )
        self.assertTrue(
            any(
                query.applied_term_normalizations
                == [
                    AppliedTermNormalization(
                        "pid provider",
                        "provider of person identification data",
                    )
                ]
                for query in plan.target_queries
            )
        )

    def test_analyze_query_classifies_arf_boundary_question(self) -> None:
        intent = analyze_query(
            "Does the ARF require a verifier authorization server in the presentation flow?",
            self.terminology,
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
            "Give me an overview of Union rules for business wallet supervision.",
            self.terminology,
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
            "How should we rotate an access cert for internal API clients?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "broad_regulation_question")
        self.assertEqual(
            intent.clarification_note,
            "Broad question: continue with an EU-first first-pass answer.",
        )

    def test_unrelated_broad_question_keeps_existing_fallback_route(self) -> None:
        intent = analyze_query(
            "Give me an overview of Union rules for company supervision.",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "broad_regulation_question")
        self.assertEqual(
            intent.clarification_note,
            "Broad question: continue with an EU-first first-pass answer.",
        )

    def test_analyze_query_classifies_germany_wallet_question_with_umlauts(self) -> None:
        intent = analyze_query(
            "Wie ist der Stand der SPRIND-EUDI-Wallet und des eIDAS-Durchführungsgesetzes in Deutschland?",
            self.terminology,
        )
        self.assertEqual(intent.intent_type, "germany_wallet_implementation_status")
        self.assertTrue(intent.eu_first)
        self.assertIn(SourceKind.NATIONAL_IMPLEMENTATION, intent.preferred_kinds)
        self.assertIn(SourceKind.PROJECT_ARTIFACT, intent.preferred_kinds)

    def test_build_retrieval_plan_records_normalized_question_without_hiding_target_queries(self) -> None:
        question = "What requirements apply to the EUBW, and how can they be provisionally structured?"
        intent = analyze_query(question, self.terminology)
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)

        self.assertEqual(plan.question, question)
        self.assertEqual(
            plan.normalized_question,
            "What requirements apply to the business wallet, and how can they be provisionally structured?",
        )
        self.assertEqual(
            plan.question_term_normalizations,
            [AppliedTermNormalization("eubw", "business wallet")],
        )
        self.assertTrue(plan.target_queries)
        self.assertTrue(all(query.target_id for query in plan.target_queries))
        self.assertTrue(any("EUBW" in query.raw_query for query in plan.target_queries))
        self.assertTrue(
            all(
                "business wallet" in query.normalized_query.lower()
                for query in plan.target_queries
            )
        )
        self.assertTrue(
            any(query.raw_query != plan.normalized_question for query in plan.target_queries)
        )

    def test_build_retrieval_plan_records_contextual_target_query_normalization(self) -> None:
        question = "What national guidance exists for Business Wallet access cert handling?"
        intent = analyze_query(question, self.terminology)
        plan = build_retrieval_plan(intent, self.hierarchy, self.runtime, self.terminology)

        self.assertEqual(
            plan.normalized_question,
            "What national guidance exists for Business Wallet access certificate handling?",
        )
        self.assertEqual(
            plan.question_term_normalizations,
            [AppliedTermNormalization("access cert", "access certificate")],
        )
        self.assertTrue(
            any(
                query.applied_term_normalizations
                == [AppliedTermNormalization("access cert", "access certificate")]
                for query in plan.target_queries
            )
        )
