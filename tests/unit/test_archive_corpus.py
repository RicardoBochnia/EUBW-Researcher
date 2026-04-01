from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eubw_researcher.config import load_archive_corpus_config
from eubw_researcher.corpus import build_catalog_from_archive, ingest_catalog
from eubw_researcher.models import AnchorQuality, CitationQuality


REPO_ROOT = Path(__file__).resolve().parents[2]


class ArchiveCorpusTests(unittest.TestCase):
    def test_archive_selection_builds_internal_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            html_path = archive_root / "reference_web" / "sample.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(
                "<html><head><title>Sample Regulation</title></head>"
                "<body><h1>Article 1 Subject matter</h1>"
                "<p>The regulation sets a rule.</p>"
                "<h2>Article 2 Additional rule</h2>"
                "<p>The regulation sets a second rule.</p></body></html>",
                encoding="utf-8",
            )
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "ARCHIVE-1",
                            "title": "Archive Sample",
                            "local_path": "sources/reference_web/sample.html",
                            "source_url": "https://example.test/regulation",
                        }
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
            config_path = tmp_root / "selection.json"
            config_path.write_text(
                json.dumps(
                    {
                        "archive_root": "archive",
                        "archive_catalog": "archive/catalog.json",
                        "sources": [
                            {
                                "archive_source_id": "ARCHIVE-1",
                                "source_id": "sample_regulation",
                                "title": "Sample Regulation",
                                "source_kind": "regulation",
                                "source_role_level": "high",
                                "jurisdiction": "EU",
                                "publication_status": "official_journal",
                                "publication_date": None,
                                "anchorability_hints": [
                                    "markdown_headings",
                                    "expect_anchors",
                                    "article_level",
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            archive_config = load_archive_corpus_config(config_path)
            catalog = build_catalog_from_archive(archive_config)
            bundle = ingest_catalog(catalog)

            self.assertEqual(len(catalog.entries), 1)
            self.assertEqual(bundle.report[0].anchor_quality, AnchorQuality.STRONG)
            self.assertEqual(bundle.report[0].citation_quality, CitationQuality.ANCHOR_GROUNDED)
            self.assertGreaterEqual(bundle.report[0].chunk_count, 2)
            self.assertEqual(
                catalog.entries[0].canonical_url,
                "https://example.test/regulation",
            )

    def test_archive_ingestion_supports_html_xml_and_pdf_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            html_path = archive_root / "sample.html"
            xml_path = archive_root / "sample.xml"
            pdf_path = archive_root / "sample.pdf"
            archive_root.mkdir(parents=True, exist_ok=True)
            html_path.write_text(
                "<html><body><h1>Article 1 HTML Rule</h1><p>HTML source text.</p></body></html>",
                encoding="utf-8",
            )
            xml_path.write_text(
                "<?xml version='1.0'?>"
                "<document><title>XML Rulebook</title><section>Article 2 XML Rule</section>"
                "<paragraph>XML source text.</paragraph></document>",
                encoding="utf-8",
            )
            pdf_path.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog >> endobj\n"
                b"4 0 obj << /Length 60 >>\n"
                b"stream\nBT\n/F1 12 Tf\n72 100 Td\n(Article 3 PDF Rule.) Tj\nET\n"
                b"endstream\nendobj\n"
            )
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        {"source_id": "H", "title": "H", "local_path": "sample.html", "source_url": "https://example.test/h"},
                        {"source_id": "X", "title": "X", "local_path": "sample.xml", "source_url": "https://example.test/x"},
                        {"source_id": "P", "title": "P", "local_path": "sample.pdf", "source_url": "https://example.test/p"},
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
            config_path = tmp_root / "selection.json"
            config_path.write_text(
                json.dumps(
                    {
                        "archive_root": "archive",
                        "archive_catalog": "archive/catalog.json",
                        "sources": [
                            {
                                "archive_source_id": "H",
                                "source_id": "html_source",
                                "title": "HTML Source",
                                "source_kind": "regulation",
                                "source_role_level": "high",
                                "jurisdiction": "EU",
                                "publication_status": "official_journal",
                                "publication_date": None,
                                "anchorability_hints": ["markdown_headings", "expect_anchors", "article_level"],
                            },
                            {
                                "archive_source_id": "X",
                                "source_id": "xml_source",
                                "title": "XML Source",
                                "source_kind": "implementing_act",
                                "source_role_level": "high",
                                "jurisdiction": "EU",
                                "publication_status": "official_journal",
                                "publication_date": None,
                                "anchorability_hints": ["markdown_headings", "expect_anchors", "article_level"],
                            },
                            {
                                "archive_source_id": "P",
                                "source_id": "pdf_source",
                                "title": "PDF Source",
                                "source_kind": "project_artifact",
                                "source_role_level": "medium",
                                "jurisdiction": "EU",
                                "publication_status": "technical_spec",
                                "publication_date": None,
                                "anchorability_hints": ["markdown_headings", "expect_anchors", "article_level"],
                            },
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            bundle = ingest_catalog(build_catalog_from_archive(load_archive_corpus_config(config_path)))
            by_id = {entry.source_id: entry for entry in bundle.report}
            self.assertEqual(by_id["html_source"].normalization_status.value, "success")
            self.assertEqual(by_id["xml_source"].normalization_format, "xml")
            self.assertEqual(by_id["pdf_source"].normalization_format, "pdf")
            self.assertGreaterEqual(by_id["pdf_source"].chunk_count, 1)

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_archive_selection_smoke_builds_ingestable_catalog(self) -> None:
        archive_config = load_archive_corpus_config(
            REPO_ROOT / "configs" / "real_corpus_selection.yaml"
        )
        catalog = build_catalog_from_archive(archive_config)
        bundle = ingest_catalog(catalog)

        self.assertGreaterEqual(len(catalog.entries), 10)
        self.assertEqual(len(bundle.documents), len(catalog.entries))
        self.assertTrue(any(report.chunk_count >= 1 for report in bundle.report))
        self.assertTrue(
            any(report.anchor_quality in (AnchorQuality.STRONG, AnchorQuality.WEAK) for report in bundle.report)
        )
        openid_reports = [
            report
            for report in bundle.report
            if report.source_id in {"openid4vci_1_0_official", "openid4vp_1_0_official"}
        ]
        self.assertTrue(openid_reports)
        self.assertTrue(all(report.chunk_count >= 5 for report in openid_reports))
        self.assertTrue(all(report.anchor_quality == AnchorQuality.STRONG for report in openid_reports))


if __name__ == "__main__":
    unittest.main()
