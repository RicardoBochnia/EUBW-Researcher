from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eubw_researcher.config import (
    load_research_profiles,
    load_runtime_config,
    load_source_governance,
    load_terminology_config,
)
from eubw_researcher.corpus import (
    load_or_build_ingestion_bundle,
    load_source_catalog,
    write_source_catalog,
)
from eubw_researcher.knowledge.query_expansion import expand_query
from eubw_researcher.knowledge import (
    KnowledgeService,
    build_dynamic_claim_targets,
    build_reading_artifacts,
    build_research_profile_trace,
    selected_evidence_candidates,
    verification_allows_answer_use,
)
from eubw_researcher.knowledge.legacy_import import import_legacy_knowledge
from eubw_researcher.models import (
    AnchorQuality,
    BindingLevel,
    CandidateClaimRecord,
    CandidateClaimStatus,
    Citation,
    CitationQuality,
    ClaimState,
    ClaimType,
    ClaimVerificationRecord,
    ConceptRecord,
    EvidenceTier,
    OpenIssueRecord,
    IngestionBundle,
    RelationGraphEdge,
    SourceCatalog,
    SourceCatalogEntry,
    SourceChunk,
    SourceDocument,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
    VerificationCheckDecision,
    VerificationDecisionStatus,
    dataclass_to_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class AgenticKnowledgeMigrationTests(unittest.TestCase):
    def _synthetic_document(
        self,
        *,
        source_id: str,
        title: str,
        text: str,
        source_role_level: SourceRoleLevel = SourceRoleLevel.MEDIUM,
        source_kind: SourceKind = SourceKind.PROJECT_ARTIFACT,
        anchor_label: str = "Section 1",
    ) -> SourceDocument:
        entry = SourceCatalogEntry(
            source_id=source_id,
            title=title,
            source_kind=source_kind,
            source_role_level=source_role_level,
            jurisdiction="EU",
            publication_status="fixture",
            publication_date=None,
            local_path=None,
            canonical_url=None,
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
            anchor_label=anchor_label,
        )
        chunk = SourceChunk(
            source_id=source_id,
            chunk_id=f"{source_id}::section",
            title=title,
            source_kind=source_kind,
            source_role_level=source_role_level,
            source_origin=SourceOrigin.LOCAL,
            jurisdiction="EU",
            text=text,
            citation=citation,
            anchor_quality=AnchorQuality.STRONG,
            extracted_anchor_label=anchor_label,
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

    def _synthetic_bundle(self, *documents: SourceDocument) -> IngestionBundle:
        return IngestionBundle(
            catalog=SourceCatalog(entries=[document.entry for document in documents]),
            documents=list(documents),
            report=[],
        )

    def test_catalog_roundtrip_preserves_governance_fields_and_changes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            corpus_root = root / "artifacts" / "real_corpus"
            source_root = corpus_root / "sources"
            source_root.mkdir(parents=True)
            source_path = source_root / "source.md"
            source_path.write_text("# Section 1\n\nWallet provider portability evidence.\n", encoding="utf-8")
            catalog_path = corpus_root / "curated_catalog.json"
            catalog = SourceCatalog(
                entries=[
                    SourceCatalogEntry(
                        source_id="legacy_runtime_source",
                        title="Legacy Runtime Source",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="technical_spec",
                        publication_date="2026-01-01",
                        local_path=source_path,
                        canonical_url="https://example.test/source",
                        evidence_tier=EvidenceTier.B,
                        binding_level=BindingLevel.OFFICIAL_NON_BINDING,
                        archive_source_id="SRC-W-LEGACY",
                        legacy_source_ids=["SRC-W-TEC-35"],
                        version_date="2026-01-02",
                        effective_date="2026-01-03",
                        content_digest="sha256:abc",
                        locator_strategy="markdown_headings",
                        governance_metadata={"admission": "fixture"},
                    )
                ]
            )
            write_source_catalog(catalog, catalog_path)

            loaded = load_source_catalog(catalog_path)
            loaded_entry = loaded.entries[0]
            self.assertEqual(loaded_entry.evidence_tier, EvidenceTier.B)
            self.assertEqual(loaded_entry.binding_level, BindingLevel.OFFICIAL_NON_BINDING)
            self.assertEqual(loaded_entry.archive_source_id, "SRC-W-LEGACY")
            self.assertEqual(loaded_entry.legacy_source_ids, ["SRC-W-TEC-35"])
            self.assertEqual(loaded_entry.effective_date, "2026-01-03")
            self.assertEqual(loaded_entry.locator_strategy, "markdown_headings")

            _, _, _, state_a = load_or_build_ingestion_bundle(catalog_path)
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            payload["sources"][0]["binding_level"] = "non_binding"
            catalog_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            _, _, _, state_b = load_or_build_ingestion_bundle(catalog_path)

            self.assertNotEqual(state_a, state_b)

    def test_legacy_import_uses_in_repo_fixture_without_external_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "imported"
            report = import_legacy_knowledge(
                REPO_ROOT / "tests" / "fixtures" / "legacy_knowledge",
                output_root,
            )

            self.assertEqual(report.claims_imported, 2)
            self.assertEqual(report.chunks_imported, 1)
            self.assertEqual(report.relations_imported, 1)
            self.assertEqual(report.open_issues_imported, 1)
            self.assertEqual(report.benchmark_questions_imported, 1)
            imported_claims = json.loads((output_root / "candidate_claims.json").read_text(encoding="utf-8"))
            statuses_by_claim = {claim["claim_id"]: claim["status"] for claim in imported_claims}
            self.assertEqual(statuses_by_claim["CLM-LEGACY-001"], "draft")
            self.assertEqual(statuses_by_claim["CLM-LEGACY-APPROVED"], "candidate")
            self.assertEqual(imported_claims[0]["binding_level"], "official_non_binding")
            imported_chunks = json.loads((output_root / "chunks.json").read_text(encoding="utf-8"))
            self.assertEqual(imported_chunks[0]["chunk_id"], "CH-LEGACY-001")
            imported_benchmarks = json.loads((output_root / "benchmark_questions.json").read_text(encoding="utf-8"))
            self.assertEqual(imported_benchmarks[0]["migration_status"], "reference_only")
            self.assertTrue((output_root / "import_report.json").is_file())

    def test_knowledge_service_returns_evidence_only_clusters_with_navigation(self) -> None:
        catalog_path = REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        _, bundle, _, _ = load_or_build_ingestion_bundle(catalog_path)
        service = KnowledgeService(bundle)

        clusters, trace, hierarchy = service.build_evidence_clusters(
            "How should wallet provider portability handle evidence?"
        )

        self.assertTrue(clusters)
        self.assertTrue(trace.steps)
        self.assertTrue(hierarchy.source_ids_by_role)
        first_record = clusters[0].records[0]
        self.assertTrue(first_record.source_id)
        self.assertTrue(first_record.chunk_id)
        passage = service.open_passage(first_record.source_id, first_record.locator)
        self.assertIsNotNone(passage)
        adjacent = service.open_adjacent_passages(first_record.source_id, first_record.locator)
        self.assertTrue(adjacent)
        serialized = dataclass_to_dict(clusters)
        self.assertIn("binding_level", serialized[0]["records"][0])

    def test_trust_mark_boundary_retrieval_opens_core_source(self) -> None:
        catalog_path = REPO_ROOT / "artifacts" / "real_corpus" / "curated_catalog.json"
        _, bundle, _, _ = load_or_build_ingestion_bundle(catalog_path)
        terminology = load_terminology_config(REPO_ROOT / "configs" / "terminology.yaml")
        service = KnowledgeService(bundle, terminology=terminology)
        question = (
            "Wann muesste ein Wallet-Provider ein sichtbares Wallet-Vertrauenszeichen "
            "entfernen, und was sagt das darueber aus, ob damit auch Relying Parties "
            "oder Attestation Provider bewertet werden?"
        )

        clusters, _, _ = service.build_evidence_clusters(question)
        diagnostics = service.retrieval_diagnostics() or {}
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.knowledge_composer_vnext.yaml")
        targets, selected_evidence = build_dynamic_claim_targets(clusters, max_targets=4)
        verification = [
            ClaimVerificationRecord(
                claim_id=target.target_id,
                claim_type=ClaimType.SYNTHESIS,
                verification_result=ClaimState.INTERPRETIVE,
                decision_reason="fixture",
                source_ids=target.source_ids,
                answer_use_allowed=True,
            )
            for target in targets
        ]
        reading_plan, opened_passages, matrix = build_reading_artifacts(
            question=question,
            clusters=clusters,
            selected_evidence=selected_evidence,
            claim_verification=verification,
            runtime_config=runtime,
        )

        self.assertTrue(
            any(
                candidate["source_id"] == "ec_ts01_wallet_trust_mark"
                for candidate in diagnostics.get("top_source_candidates", [])
            )
        )
        self.assertIn(
            "ec_ts01_wallet_trust_mark",
            {item.source_id for item in reading_plan.items},
        )
        self.assertTrue(
            any(
                passage.source_id == "ec_ts01_wallet_trust_mark"
                and passage.locator
                and ("1.1" in passage.locator or "1.2" in passage.locator)
                for passage in opened_passages
            )
        )
        self.assertTrue(
            any("ec_ts01_wallet_trust_mark" in record.source_ids for record in matrix.records)
        )

    def test_source_title_beats_generic_role_terms(self) -> None:
        title_source = self._synthetic_document(
            source_id="medium_trust_mark_source",
            title="Visible Wallet Trust Mark Removal Guidance",
            text="This medium-rank source defines when the visible mark must be withdrawn.",
            source_role_level=SourceRoleLevel.MEDIUM,
        )
        generic = self._synthetic_document(
            source_id="generic_high_rank_wallet_roles",
            title="Generic Wallet Provider Duties",
            text=(
                "Wallet provider relying party attestation wallet provider relying party "
                "attestation wallet provider relying party attestation."
            ),
            source_role_level=SourceRoleLevel.HIGH,
            source_kind=SourceKind.REGULATION,
        )
        service = KnowledgeService(self._synthetic_bundle(generic, title_source))

        clusters, _, _ = service.build_evidence_clusters(
            "Wann muss das sichtbare Wallet-Vertrauenszeichen entfernt werden?"
        )

        self.assertIn(
            "medium_trust_mark_source",
            {source_id for cluster in clusters[:2] for source_id in cluster.source_ids},
        )

    def test_german_english_domain_expansion_for_retrieval(self) -> None:
        expansion = expand_query("Richtige Immabescheinigung und sichtbares Vertrauenszeichen entfernen")

        self.assertIn("trust mark", expansion.all_terms)
        self.assertIn("remove", expansion.all_terms)
        self.assertIn("selection", expansion.all_terms)
        self.assertIn("student", expansion.all_terms)

    def test_knowledge_service_exposes_agent_navigation_primitives(self) -> None:
        catalog_path = REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        _, bundle, _, _ = load_or_build_ingestion_bundle(catalog_path)
        first_chunk = bundle.documents[0].chunks[0]
        claim = CandidateClaimRecord(
            claim_id="CLM-NAV-001",
            normalized_statement="Wallet provider portability requires audit evidence.",
            source_ids=[first_chunk.source_id],
            chunk_ids=[first_chunk.chunk_id],
            locators=[first_chunk.extracted_anchor_label or first_chunk.chunk_id],
            topic="portability",
            evidence_tier=EvidenceTier.B,
            binding_level=BindingLevel.OFFICIAL_NON_BINDING,
            status=CandidateClaimStatus.CANDIDATE,
        )
        service = KnowledgeService(
            bundle,
            candidate_claims=[claim],
            relation_edges=[
                RelationGraphEdge(
                    edge_id="REL-NAV-001",
                    relation_type="qualifies",
                    source_id=claim.claim_id,
                    target_id="CLM-NAV-002",
                    evidence_source_ids=[first_chunk.source_id],
                )
            ],
            open_issues=[
                OpenIssueRecord(
                    issue_id="ISS-NAV-001",
                    issue_statement="Provider portability semantics remain partly delegated.",
                    reason_open="Technical migration details are not final in this fixture.",
                    affected_claim_ids=[claim.claim_id],
                    affected_answer_facets=["portability"],
                )
            ],
            concepts=[
                ConceptRecord(
                    concept_id="concept_portability",
                    canonical_label="portability",
                    aliases=["provider migration"],
                    linked_claim_ids=[claim.claim_id],
                    linked_chunk_ids=[first_chunk.chunk_id],
                    linked_source_ids=[first_chunk.source_id],
                )
            ],
        )

        self.assertEqual(service.search_claims("provider portability")[0].claim_id, claim.claim_id)
        self.assertEqual(service.get_claim_evidence(claim.claim_id).candidate_claim_ids, [claim.claim_id])
        self.assertEqual(service.trace_concept("provider migration").concept_id, "concept_portability")
        self.assertEqual(service.expand_relations([claim.claim_id])[0].edge_id, "REL-NAV-001")
        self.assertEqual(service.get_open_issues([claim.claim_id])[0].issue_id, "ISS-NAV-001")
        self.assertEqual(service.compare_sources([claim.claim_id])[0]["source_id"], first_chunk.source_id)
        clusters, _, _ = service.build_evidence_clusters("provider portability audit")
        explanation = service.explain_result(clusters[0].cluster_id)
        self.assertEqual(explanation["result_type"], "evidence_cluster")

    def test_strict_verification_blocks_failed_answer_use_checks(self) -> None:
        record = ClaimVerificationRecord(
            claim_id="CLM-VERIFY-001",
            claim_type=ClaimType.SYNTHESIS,
            verification_result=ClaimState.INTERPRETIVE,
            decision_reason="fixture",
            answer_use_allowed=True,
            checks=[
                VerificationCheckDecision(
                    check_id="source_exists_in_catalog",
                    status=VerificationDecisionStatus.PASS,
                    reason="fixture",
                ),
                VerificationCheckDecision(
                    check_id="locator_resolvable",
                    status=VerificationDecisionStatus.FAIL,
                    reason="fixture",
                ),
            ],
        )

        self.assertTrue(verification_allows_answer_use(record, strict=False))
        self.assertFalse(verification_allows_answer_use(record, strict=True))

    def test_strict_verification_allows_qualified_metadata_checks(self) -> None:
        record = ClaimVerificationRecord(
            claim_id="CLM-VERIFY-QUALIFIED",
            claim_type=ClaimType.SYNTHESIS,
            verification_result=ClaimState.INTERPRETIVE,
            decision_reason="fixture",
            answer_use_allowed=True,
            checks=[
                VerificationCheckDecision(
                    check_id="source_exists_in_catalog",
                    status=VerificationDecisionStatus.PASS,
                    reason="fixture",
                ),
                VerificationCheckDecision(
                    check_id="source_hash_or_version_matches_catalog",
                    status=VerificationDecisionStatus.QUALIFIED,
                    reason="fixture",
                ),
            ],
        )

        self.assertTrue(verification_allows_answer_use(record, strict=True))

    def test_dynamic_targets_turn_clusters_into_selected_retrieval_candidates(self) -> None:
        catalog_path = REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        _, bundle, _, _ = load_or_build_ingestion_bundle(catalog_path)
        service = KnowledgeService(bundle)
        clusters, _, _ = service.build_evidence_clusters("registration access audit")

        targets, selected_evidence = build_dynamic_claim_targets(clusters, max_targets=2)
        selected_candidates = selected_evidence_candidates(bundle, selected_evidence)

        self.assertTrue(targets)
        self.assertEqual(len(targets), len(selected_evidence))
        self.assertEqual(len(selected_candidates), len(selected_evidence))
        self.assertEqual(targets[0].target_id, selected_evidence[0].claim_id)
        self.assertEqual(targets[0].source_ids, [selected_evidence[0].source_id])
        self.assertEqual(selected_candidates[0].chunk.chunk_id, selected_evidence[0].chunk_id)
        self.assertGreaterEqual(
            len({record.cluster_id for record in selected_evidence}),
            min(2, len(clusters)),
        )

    def test_runtime_config_loads_disabled_knowledge_service_defaults(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.scan.yaml")

        self.assertFalse(runtime.knowledge_service_enabled)
        self.assertFalse(runtime.knowledge_service_emit_clusters)
        self.assertEqual(runtime.knowledge_service_discovery_mode, "shadow")
        self.assertTrue(runtime.knowledge_service_strict_verification_required)

    def test_runtime_config_can_enable_knowledge_shadow_mode(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.knowledge_shadow.yaml")

        self.assertTrue(runtime.knowledge_service_enabled)
        self.assertTrue(runtime.knowledge_service_emit_clusters)
        self.assertEqual(runtime.knowledge_service_discovery_mode, "shadow")
        self.assertTrue(runtime.knowledge_service_strict_verification_required)

    def test_runtime_config_can_enable_knowledge_assistive_mode(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.knowledge_assistive.yaml")

        self.assertTrue(runtime.knowledge_service_enabled)
        self.assertTrue(runtime.knowledge_service_emit_clusters)
        self.assertEqual(runtime.knowledge_service_discovery_mode, "assistive")
        self.assertTrue(runtime.knowledge_service_strict_verification_required)
        self.assertEqual(runtime.answer_composer_mode, "classic")

    def test_runtime_config_can_enable_composer_vnext_reading_loop(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.knowledge_composer_vnext.yaml")

        self.assertTrue(runtime.knowledge_service_enabled)
        self.assertEqual(runtime.knowledge_service_discovery_mode, "assistive")
        self.assertTrue(runtime.knowledge_service_reading_loop_enabled)
        self.assertEqual(runtime.answer_composer_mode, "vnext")

    def test_research_profiles_activate_from_generic_concepts(self) -> None:
        catalog_path = REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        _, bundle, _, _ = load_or_build_ingestion_bundle(catalog_path)
        service = KnowledgeService(bundle)
        clusters, _, _ = service.build_evidence_clusters("How does wallet provider portability work?")
        profiles = load_research_profiles(REPO_ROOT / "configs" / "research_profiles.yaml")

        trace = build_research_profile_trace(
            "How does wallet provider portability work?",
            profiles,
            clusters,
        )

        self.assertIsNotNone(trace)
        self.assertIn(
            "lifecycle_status",
            {activation.profile_id for activation in trace.activations},
        )

    def test_reading_loop_builds_plan_opened_passages_and_synthesis_matrix(self) -> None:
        catalog_path = REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        _, bundle, _, _ = load_or_build_ingestion_bundle(catalog_path)
        service = KnowledgeService(bundle)
        clusters, _, _ = service.build_evidence_clusters("provider portability audit")
        targets, selected_evidence = build_dynamic_claim_targets(clusters, max_targets=2)
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.knowledge_composer_vnext.yaml")
        verification = [
            ClaimVerificationRecord(
                claim_id=targets[0].target_id,
                claim_type=ClaimType.SYNTHESIS,
                verification_result=ClaimState.INTERPRETIVE,
                decision_reason="fixture",
                source_ids=[selected_evidence[0].source_id],
                chunk_ids=[selected_evidence[0].chunk_id],
                answer_use_allowed=True,
            )
        ]

        reading_plan, opened_passages, matrix = build_reading_artifacts(
            question="provider portability audit",
            clusters=clusters,
            selected_evidence=selected_evidence,
            claim_verification=verification,
            runtime_config=runtime,
        )

        self.assertTrue(reading_plan.items)
        self.assertTrue(opened_passages)
        self.assertTrue(matrix.records)
        self.assertTrue(matrix.records[0].statement.startswith("Passage supports:"))
        self.assertIn(matrix.records[0].answer_role, {"core_answer_support", "source_role_context", "background"})
        self.assertTrue(matrix.records[0].caveats)

    def test_source_governance_config_loads_claim_type_rules(self) -> None:
        governance = load_source_governance(REPO_ROOT / "configs" / "source_governance.yaml")

        self.assertEqual(governance.policy_version, "source_governance.v1")
        obligation_rule = governance.claim_type_compatibility[ClaimType.OBLIGATION]
        self.assertIn(BindingLevel.BINDING, obligation_rule.allowed_binding_levels)
        self.assertTrue(obligation_rule.binding_required_for_current_law)


if __name__ == "__main__":
    unittest.main()
