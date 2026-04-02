from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eubw_researcher.corpus import (
    build_corpus_manifest,
    build_corpus_coverage_report,
    build_corpus_refresh_summary,
    compute_corpus_state_id,
    ingest_catalog,
    load_corpus_manifest,
    load_corpus_refresh_summary,
    write_source_catalog,
)
from eubw_researcher.models import (
    CorpusManifest,
    CorpusManifestSource,
    SourceCatalog,
    SourceCatalogEntry,
    SourceKind,
    SourceOrigin,
    SourceRoleLevel,
)


class CorpusFreshnessTests(unittest.TestCase):
    def _write_source(self, root: Path, name: str, content: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _manifest_for_catalog(self, catalog_path: Path, catalog: SourceCatalog):
        bundle = ingest_catalog(catalog)
        initial_manifest = build_corpus_manifest(catalog_path, catalog, bundle=bundle)
        coverage_report = build_corpus_coverage_report(
            catalog_path,
            bundle,
            initial_manifest.corpus_state_id,
        )
        return build_corpus_manifest(
            catalog_path,
            catalog,
            bundle=bundle,
            coverage_report=coverage_report,
        )

    def test_refresh_summary_reports_source_and_coverage_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_root = Path(tmp_dir) / "artifacts" / "real_corpus"
            source_root = corpus_root / "sources"
            catalog_path = corpus_root / "curated_catalog.json"

            original_catalog = SourceCatalog(
                entries=[
                    SourceCatalogEntry(
                        source_id="regulation_source",
                        title="Regulation Source",
                        source_kind=SourceKind.REGULATION,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "regulation.md",
                            "# Article 1\n\nOriginal governing text.\n",
                        ),
                        canonical_url="https://example.test/regulation",
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
                        local_path=self._write_source(
                            source_root,
                            "vci.md",
                            "# Section 1\n\nVCI content.\n",
                        ),
                        canonical_url="https://example.test/vci",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="standard_vp",
                        title="OpenID4VP Standard",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        publication_status="standard",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "vp.md",
                            "# Section 2\n\nVP content.\n",
                        ),
                        canonical_url="https://example.test/vp",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="arf_source",
                        title="Architecture and Reference Framework",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="profile",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "arf.md",
                            "# Section 3\n\nARF guidance.\n",
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
                        local_path=self._write_source(
                            source_root,
                            "rp_registration.md",
                            "# Section 4\n\nRegistration information.\n",
                        ),
                        canonical_url="https://example.test/rp-registration",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="rp_information_set",
                        title="Relying Party Information Set",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="technical_spec",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "rp_information.md",
                            "# Section 5\n\nInformation to be registered.\n",
                        ),
                        canonical_url="https://example.test/rp-information",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="implementing_source",
                        title="Implementing Source",
                        source_kind=SourceKind.IMPLEMENTING_ACT,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "implementing.md",
                            "# Article 2\n\nImplementing text.\n",
                        ),
                        canonical_url="https://example.test/implementing",
                        anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                    ),
                ]
            )
            write_source_catalog(original_catalog, catalog_path)
            previous_manifest = self._manifest_for_catalog(catalog_path, original_catalog)

            updated_catalog = SourceCatalog(
                entries=[
                    SourceCatalogEntry(
                        source_id="regulation_source",
                        title="Regulation Source",
                        source_kind=SourceKind.REGULATION,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "regulation.md",
                            "# Article 1\n\nUpdated governing text.\n",
                        ),
                        canonical_url="https://example.test/regulation",
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
                        local_path=self._write_source(
                            source_root,
                            "vci.md",
                            "# Section 1\n\nVCI content.\n",
                        ),
                        canonical_url="https://example.test/vci",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="arf_source",
                        title="Architecture and Reference Framework",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="profile",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "arf.md",
                            "# Section 3\n\nARF guidance.\n",
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
                        local_path=self._write_source(
                            source_root,
                            "rp_registration.md",
                            "# Section 4\n\nRegistration information.\n",
                        ),
                        canonical_url="https://example.test/rp-registration",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="rp_information_set",
                        title="Relying Party Information Set",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="technical_spec",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "rp_information.md",
                            "# Section 5\n\nInformation to be registered.\n",
                        ),
                        canonical_url="https://example.test/rp-information",
                        anchorability_hints=["markdown_headings", "section_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="implementing_source",
                        title="Implementing Source",
                        source_kind=SourceKind.IMPLEMENTING_ACT,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="EU",
                        publication_status="official_journal",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "implementing.md",
                            "# Article 2\n\nImplementing text.\n",
                        ),
                        canonical_url="https://example.test/implementing",
                        anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                    ),
                    SourceCatalogEntry(
                        source_id="official_web_mirror",
                        title="Official Web Mirror",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        publication_status="official_site",
                        publication_date=None,
                        local_path=self._write_source(
                            source_root,
                            "official_web.html",
                            "<html><body><h1>Official Web Mirror</h1><p>Updated official source.</p></body></html>",
                        ),
                        canonical_url="https://example.test/official-web",
                        source_origin=SourceOrigin.WEB,
                        anchorability_hints=["html_headings"],
                    ),
                ]
            )
            write_source_catalog(updated_catalog, catalog_path)
            current_manifest = self._manifest_for_catalog(catalog_path, updated_catalog)

            summary = build_corpus_refresh_summary(current_manifest, previous_manifest)

            self.assertEqual(summary.refresh_status, "refreshed")
            self.assertEqual(summary.previous_corpus_state_id, previous_manifest.corpus_state_id)
            self.assertEqual({item.source_id for item in summary.removed_sources}, {"standard_vp"})
            self.assertEqual({item.source_id for item in summary.added_sources}, {"official_web_mirror"})
            self.assertEqual({item.source_id for item in summary.changed_web_sources}, {"official_web_mirror"})
            updated_by_id = {item.source_id: item for item in summary.updated_sources}
            self.assertIn("regulation_source", updated_by_id)
            self.assertIn("content_digest", updated_by_id["regulation_source"].changed_fields)
            coverage_delta = {
                item.family_id: item for item in summary.coverage_deltas
            }["current_technical_standards"]
            self.assertEqual(coverage_delta.previous_admitted_count, 2)
            self.assertEqual(coverage_delta.current_admitted_count, 1)
            self.assertFalse(coverage_delta.previous_missing)
            self.assertTrue(coverage_delta.current_missing)

    def test_state_id_and_refresh_summary_ignore_absolute_path_only_changes(self) -> None:
        previous_source = CorpusManifestSource(
            source_id="same_source",
            title="Same Source",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            jurisdiction="EU",
            publication_status="official_journal",
            publication_date=None,
            source_origin=SourceOrigin.LOCAL,
            canonical_url="https://example.test/source",
            local_path="/tmp/checkout-a/source.md",
            anchorability_hints=["markdown_headings"],
            admission_reason="test",
            content_digest="abc123",
            byte_size=42,
        )
        current_source = CorpusManifestSource(
            source_id="same_source",
            title="Same Source",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            jurisdiction="EU",
            publication_status="official_journal",
            publication_date=None,
            source_origin=SourceOrigin.LOCAL,
            canonical_url="https://example.test/source",
            local_path="/tmp/checkout-b/source.md",
            anchorability_hints=["markdown_headings"],
            admission_reason="test",
            content_digest="abc123",
            byte_size=42,
        )

        previous_manifest = CorpusManifest(
            catalog_path="/tmp/catalog.json",
            corpus_state_id=compute_corpus_state_id([previous_source]),
            generated_at="2026-04-02T00:00:00+00:00",
            selection_config_path=None,
            sources=[previous_source],
        )
        current_manifest = CorpusManifest(
            catalog_path="/tmp/catalog.json",
            corpus_state_id=compute_corpus_state_id([current_source]),
            generated_at="2026-04-02T00:00:00+00:00",
            selection_config_path=None,
            sources=[current_source],
        )

        self.assertEqual(previous_manifest.corpus_state_id, current_manifest.corpus_state_id)
        summary = build_corpus_refresh_summary(current_manifest, previous_manifest)
        self.assertEqual(summary.refresh_status, "unchanged")
        self.assertFalse(summary.updated_sources)

    def test_compute_corpus_state_id_is_order_independent(self) -> None:
        source_a = CorpusManifestSource(
            source_id="a_source",
            title="A Source",
            source_kind=SourceKind.REGULATION,
            source_role_level=SourceRoleLevel.HIGH,
            jurisdiction="EU",
            publication_status="official_journal",
            publication_date=None,
            source_origin=SourceOrigin.LOCAL,
            canonical_url="https://example.test/a",
            local_path="/tmp/a.md",
            anchorability_hints=["markdown_headings"],
            content_digest="aaa",
            byte_size=1,
        )
        source_b = CorpusManifestSource(
            source_id="b_source",
            title="B Source",
            source_kind=SourceKind.TECHNICAL_STANDARD,
            source_role_level=SourceRoleLevel.HIGH,
            jurisdiction="international",
            publication_status="standard",
            publication_date=None,
            source_origin=SourceOrigin.LOCAL,
            canonical_url="https://example.test/b",
            local_path="/tmp/b.md",
            anchorability_hints=["markdown_headings"],
            content_digest="bbb",
            byte_size=2,
        )

        self.assertEqual(
            compute_corpus_state_id([source_a, source_b]),
            compute_corpus_state_id([source_b, source_a]),
        )

    def test_invalid_manifest_and_refresh_summary_json_return_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            manifest_path = temp_root / "corpus_manifest.json"
            refresh_summary_path = temp_root / "corpus_refresh_summary.json"
            manifest_path.write_text("{", encoding="utf-8")
            refresh_summary_path.write_text("{", encoding="utf-8")

            self.assertIsNone(load_corpus_manifest(manifest_path))
            self.assertIsNone(load_corpus_refresh_summary(refresh_summary_path))

            manifest_path.write_text(
                json.dumps(
                    {
                        "catalog_path": str((temp_root / "catalog.json").resolve()),
                        "corpus_state_id": "state-1234",
                        "generated_at": "2026-04-02T00:00:00+00:00",
                        "selection_config_path": None,
                        "sources": [],
                        "coverage_passed": True,
                        "coverage_families": [],
                    }
                ),
                encoding="utf-8",
            )
            refresh_summary_path.write_text(
                json.dumps(
                    {
                        "catalog_path": str((temp_root / "catalog.json").resolve()),
                        "corpus_state_id": "state-1234",
                        "previous_corpus_state_id": None,
                        "generated_at": "2026-04-02T00:00:00+00:00",
                        "refresh_status": "initial_build",
                        "selection_config_path": None,
                        "added_sources": [],
                        "removed_sources": [],
                        "updated_sources": [],
                        "changed_web_sources": [],
                        "coverage_deltas": [],
                    }
                ),
                encoding="utf-8",
            )

            self.assertIsNotNone(load_corpus_manifest(manifest_path))
            self.assertIsNotNone(load_corpus_refresh_summary(refresh_summary_path))


if __name__ == "__main__":
    unittest.main()
