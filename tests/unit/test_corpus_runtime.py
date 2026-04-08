from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eubw_researcher.corpus import load_or_build_ingestion_bundle, write_source_catalog
from eubw_researcher.models import SourceCatalog, SourceCatalogEntry, SourceKind, SourceRoleLevel


class CorpusRuntimeTests(unittest.TestCase):
    def _build_real_catalog(self, root: Path) -> Path:
        corpus_root = root / "artifacts" / "real_corpus"
        source_root = corpus_root / "sources"
        source_root.mkdir(parents=True, exist_ok=True)

        def source_file(name: str, content: str) -> Path:
            path = source_root / name
            path.write_text(content, encoding="utf-8")
            return path

        catalog = SourceCatalog(
            entries=[
                SourceCatalogEntry(
                    source_id="regulation_source",
                    title="Regulation Source",
                    source_kind=SourceKind.REGULATION,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="EU",
                    publication_status="official_journal",
                    publication_date=None,
                    local_path=source_file(
                        "regulation.md",
                        "# Article 1 Regulation Rule\n\nThe regulation sets the governing rule.\n",
                    ),
                    canonical_url="https://example.test/regulation",
                    anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                ),
                SourceCatalogEntry(
                    source_id="implementing_source",
                    title="Implementing Source",
                    source_kind=SourceKind.IMPLEMENTING_ACT,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="EU",
                    publication_status="official_journal",
                    publication_date=None,
                    local_path=source_file(
                        "implementing.md",
                        "# Article 2 Implementing Rule\n\nThe implementing act provides annex detail.\n",
                    ),
                    canonical_url="https://example.test/implementing",
                    anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                ),
                SourceCatalogEntry(
                    source_id="standard_vci",
                    title="OpenID4VCI Standard",
                    source_kind=SourceKind.TECHNICAL_STANDARD,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="international",
                    publication_status="standard",
                    publication_date=None,
                    local_path=source_file(
                        "vci.md",
                        "# Section 1 OpenID4VCI\n\nAuthorization server and token endpoint.\n",
                    ),
                    canonical_url="https://example.test/vci",
                    anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                ),
                SourceCatalogEntry(
                    source_id="standard_vp",
                    title="OpenID4VP Standard",
                    source_kind=SourceKind.TECHNICAL_STANDARD,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="international",
                    publication_status="standard",
                    publication_date=None,
                    local_path=source_file(
                        "vp.md",
                        "# Section 2 OpenID4VP\n\nWallet metadata and presentation request.\n",
                    ),
                    canonical_url="https://example.test/vp",
                    anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                ),
                SourceCatalogEntry(
                    source_id="arf_source",
                    title="Architecture and Reference Framework",
                    source_kind=SourceKind.PROJECT_ARTIFACT,
                    source_role_level=SourceRoleLevel.MEDIUM,
                    jurisdiction="EU",
                    publication_status="profile",
                    publication_date=None,
                    local_path=source_file(
                        "arf.md",
                        "# Section 3 ARF\n\nDeployment profile guidance.\n",
                    ),
                    canonical_url="https://example.test/arf",
                    anchorability_hints=["markdown_headings", "section_level"],
                ),
                SourceCatalogEntry(
                    source_id="rp_registration_api",
                    title="Relying Party Registration API",
                    source_kind=SourceKind.PROJECT_ARTIFACT,
                    source_role_level=SourceRoleLevel.MEDIUM,
                    jurisdiction="EU",
                    publication_status="technical_spec",
                    publication_date=None,
                    local_path=source_file(
                        "rp_registration.md",
                        "# Section 4 Registration API\n\nRegistration information for relying parties.\n",
                    ),
                    canonical_url="https://example.test/rp-registration",
                    anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                ),
                SourceCatalogEntry(
                    source_id="rp_information_set",
                    title="Relying Party Information Set",
                    source_kind=SourceKind.PROJECT_ARTIFACT,
                    source_role_level=SourceRoleLevel.MEDIUM,
                    jurisdiction="EU",
                    publication_status="technical_spec",
                    publication_date=None,
                    local_path=source_file(
                        "rp_information.md",
                        "# Section 5 Information Set\n\nInformation to be registered for relying parties.\n",
                    ),
                    canonical_url="https://example.test/rp-information",
                    anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                ),
            ]
        )
        catalog_path = corpus_root / "curated_catalog.json"
        write_source_catalog(catalog, catalog_path)
        return catalog_path

    def test_real_corpus_bundle_cache_is_reused_and_coverage_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog_path = self._build_real_catalog(Path(tmp_dir))

            _, bundle, coverage_report, corpus_state_id = load_or_build_ingestion_bundle(catalog_path)

            self.assertEqual(len(bundle.documents), 7)
            self.assertTrue(coverage_report.passed)
            self.assertTrue(corpus_state_id)
            cache_dir = catalog_path.parent / "cache"
            self.assertTrue((cache_dir / "normalized_bundle.pkl").exists())

            with patch("eubw_researcher.corpus.runtime.ingest_catalog", side_effect=AssertionError("cache should be reused")):
                _, cached_bundle, cached_report, cached_state_id = load_or_build_ingestion_bundle(catalog_path)

            self.assertEqual(len(cached_bundle.documents), 7)
            self.assertTrue(cached_report.passed)
            self.assertEqual(cached_state_id, corpus_state_id)

    def test_corpus_coverage_gate_reports_missing_required_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_root = Path(tmp_dir) / "artifacts" / "real_corpus"
            source_root = corpus_root / "sources"
            source_root.mkdir(parents=True, exist_ok=True)
            only_regulation = source_root / "regulation.md"
            only_regulation.write_text(
                "# Article 1 Regulation Rule\n\nThe regulation sets the governing rule.\n",
                encoding="utf-8",
            )
            catalog = SourceCatalog(
                entries=[
                    SourceCatalogEntry(
                        source_id="regulation_source",
                        title="Regulation Source",
                        source_kind=SourceKind.REGULATION,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=only_regulation,
                        canonical_url="https://example.test/regulation",
                        anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                    )
                ]
            )
            catalog_path = corpus_root / "curated_catalog.json"
            write_source_catalog(catalog, catalog_path)

            _, _, coverage_report, _ = load_or_build_ingestion_bundle(catalog_path)

            self.assertFalse(coverage_report.passed)
            missing_families = {
                family.family_id for family in coverage_report.families if family.missing
            }
            self.assertIn("current_technical_standards", missing_families)

    def test_corpus_coverage_tracks_germany_families_when_germany_sources_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            corpus_root = root / "artifacts" / "real_corpus"
            source_root = corpus_root / "sources"
            source_root.mkdir(parents=True, exist_ok=True)

            def source_file(name: str, content: str) -> Path:
                path = source_root / name
                path.write_text(content, encoding="utf-8")
                return path

            catalog = SourceCatalog(
                entries=[
                    SourceCatalogEntry(
                        source_id="regulation_source",
                        title="Regulation Source",
                        source_kind=SourceKind.REGULATION,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=source_file("regulation.md", "# Article 1\n\nRule.\n"),
                        canonical_url="https://example.test/regulation",
                        anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="implementing_source",
                        title="Implementing Source",
                        source_kind=SourceKind.IMPLEMENTING_ACT,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=source_file("implementing.md", "# Article 2\n\nAnnex.\n"),
                        canonical_url="https://example.test/implementing",
                        anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="standard_vci",
                        title="OpenID4VCI Standard",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        publication_status="standard",
                        publication_date=None,
                        local_path=source_file("vci.md", "# Section 1\n\nVCI.\n"),
                        canonical_url="https://example.test/vci",
                        anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="standard_vp",
                        title="OpenID4VP Standard",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        publication_status="standard",
                        publication_date=None,
                        local_path=source_file("vp.md", "# Section 2\n\nVP.\n"),
                        canonical_url="https://example.test/vp",
                        anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="arf_source",
                        title="Architecture and Reference Framework",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="profile",
                        publication_date=None,
                        local_path=source_file("arf.md", "# Section 3\n\nARF.\n"),
                        canonical_url="https://example.test/arf",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="rp_registration_api",
                        title="Relying Party Registration API",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="technical_spec",
                        publication_date=None,
                        local_path=source_file("rp_registration.md", "# Section 4\n\nRP API.\n"),
                        canonical_url="https://example.test/rp-registration",
                        anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="rp_information_set",
                        title="Relying Party Information Set",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="technical_spec",
                        publication_date=None,
                        local_path=source_file("rp_information.md", "# Section 5\n\nRP info.\n"),
                        canonical_url="https://example.test/rp-information",
                        anchorability_hints=["markdown_headings", "expect_anchors", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="de_law_bmv_eidas",
                        title="BMV eIDAS Durchfuehrungsgesetz",
                        source_kind=SourceKind.NATIONAL_IMPLEMENTATION,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="DE",
                        publication_status="draft",
                        publication_date=None,
                        local_path=source_file("de_law.md", "# Gesetz\n\nWallet draft.\n"),
                        canonical_url="https://example.test/de-law",
                        anchorability_hints=["markdown_headings"],
                    ),
                    SourceCatalogEntry(
                        source_id="de_parliament_wallet_status",
                        title="Bundestag Drucksache EUDI Wallet",
                        source_kind=SourceKind.NATIONAL_IMPLEMENTATION,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="DE",
                        publication_status="briefing",
                        publication_date=None,
                        local_path=source_file("de_parliament.md", "# Drucksache\n\nStatus.\n"),
                        canonical_url="https://example.test/de-parliament",
                        anchorability_hints=["markdown_headings"],
                    ),
                    SourceCatalogEntry(
                        source_id="de_sprind_eudi_wallet",
                        title="SPRIND EUDI Wallet",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="DE",
                        publication_status="project",
                        publication_date=None,
                        local_path=source_file("de_sprind.md", "# SPRIND\n\nPrototype.\n"),
                        canonical_url="https://example.test/de-sprind",
                        anchorability_hints=["markdown_headings"],
                    ),
                    SourceCatalogEntry(
                        source_id="de_wallet_implementation_note",
                        title="Deutschland EUDI Wallet Umsetzung",
                        source_kind=SourceKind.NATIONAL_IMPLEMENTATION,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="DE",
                        publication_status="guidance",
                        publication_date=None,
                        local_path=source_file("de_wallet_note.md", "# Umsetzung\n\nWallet delivery.\n"),
                        canonical_url="https://example.test/de-wallet",
                        anchorability_hints=["markdown_headings"],
                    ),
                ]
            )
            catalog_path = corpus_root / "curated_catalog.json"
            write_source_catalog(catalog, catalog_path)

            _, _, coverage_report, _ = load_or_build_ingestion_bundle(catalog_path)

            families = {family.family_id: family for family in coverage_report.families}
            self.assertIn("germany_legislative_or_legal_sources", families)
            self.assertIn("germany_wallet_delivery_sources", families)
            self.assertFalse(families["germany_legislative_or_legal_sources"].missing)
            self.assertFalse(families["germany_wallet_delivery_sources"].missing)


if __name__ == "__main__":
    unittest.main()
