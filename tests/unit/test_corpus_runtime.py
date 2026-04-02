from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import eubw_researcher.corpus.runtime as corpus_runtime
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

    def test_real_corpus_state_id_reuses_current_manifest_without_rehashing_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog_path = self._build_real_catalog(Path(tmp_dir))

            _, _, _, corpus_state_id = load_or_build_ingestion_bundle(catalog_path)
            manifest_path = catalog_path.parent / "corpus_manifest.json"
            manifest_path.write_text(
                (
                    "{\n"
                    f'  "catalog_path": "{str(catalog_path.resolve())}",\n'
                    f'  "corpus_state_id": "{corpus_state_id}",\n'
                    f'  "generated_at": "{datetime.now(timezone.utc).isoformat()}",\n'
                    '  "selection_config_path": null,\n'
                    '  "sources": [],\n'
                    '  "coverage_passed": true,\n'
                    '  "coverage_families": []\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            with patch("eubw_researcher.corpus.runtime._catalog_state_id", side_effect=AssertionError("manifest state id should be reused")):
                _, _, _, cached_state_id = load_or_build_ingestion_bundle(catalog_path)

            self.assertEqual(cached_state_id, corpus_state_id)

    def test_real_corpus_state_id_ignores_manifest_for_other_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            catalog_path = self._build_real_catalog(temp_root)
            manifest_path = catalog_path.parent / "corpus_manifest.json"
            other_catalog_path = (temp_root / "other" / "catalog.json").resolve()
            manifest_path.write_text(
                (
                    "{\n"
                    f'  "catalog_path": "{str(other_catalog_path)}",\n'
                    '  "corpus_state_id": "wrong-state-id",\n'
                    f'  "generated_at": "{datetime.now(timezone.utc).isoformat()}",\n'
                    '  "selection_config_path": null,\n'
                    '  "sources": [],\n'
                    '  "coverage_passed": true,\n'
                    '  "coverage_families": []\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            catalog = corpus_runtime.load_source_catalog(catalog_path)

            self.assertIsNone(corpus_runtime._load_cached_corpus_state_id(catalog_path, catalog))

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

    def test_real_corpus_state_id_is_stable_when_only_file_mtime_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            catalog_path = self._build_real_catalog(Path(tmp_dir))
            regulation_path = catalog_path.parent / "sources" / "regulation.md"

            _, _, _, corpus_state_id = load_or_build_ingestion_bundle(catalog_path)
            regulation_content = regulation_path.read_text(encoding="utf-8")
            regulation_path.write_text(regulation_content, encoding="utf-8")

            with patch("eubw_researcher.corpus.runtime.ingest_catalog", side_effect=AssertionError("cache should be reused")):
                _, _, _, cached_state_id = load_or_build_ingestion_bundle(catalog_path)

            self.assertEqual(cached_state_id, corpus_state_id)


if __name__ == "__main__":
    unittest.main()
