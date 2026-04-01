from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.corpus import ingest_catalog, load_source_catalog
from eubw_researcher.models import AnchorQuality, CitationQuality, SourceRoleLevel


REPO_ROOT = Path(__file__).resolve().parents[2]


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        catalog = load_source_catalog(
            REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        )
        self.bundle = ingest_catalog(catalog)

    def test_all_sources_have_document_level_citations(self) -> None:
        self.assertEqual(len(self.bundle.documents), 8)
        for document in self.bundle.documents:
            self.assertTrue(document.chunks)
            for chunk in document.chunks:
                self.assertIsNotNone(chunk.citation.document_title)

    def test_anchor_quality_and_role_visibility_are_reported(self) -> None:
        report_by_id = {entry.source_id: entry for entry in self.bundle.report}

        self.assertEqual(report_by_id["openid4vci_draft13"].anchor_quality, AnchorQuality.STRONG)
        self.assertEqual(
            report_by_id["openid4vci_draft13"].citation_quality,
            CitationQuality.ANCHOR_GROUNDED,
        )
        self.assertEqual(
            report_by_id["scientific_review_wallet_certificates"].anchor_quality,
            AnchorQuality.WEAK,
        )
        self.assertEqual(
            report_by_id["scientific_review_wallet_certificates"].citation_quality,
            CitationQuality.DOCUMENT_ONLY,
        )
        self.assertFalse(report_by_id["scientific_review_wallet_certificates"].technical_anchor_failure)
        self.assertEqual(
            report_by_id["ssi_commentary_blog"].citation_quality,
            CitationQuality.DOCUMENT_ONLY,
        )
        self.assertTrue(report_by_id["ssi_commentary_blog"].structure_poor)
        self.assertIn("do not treat", report_by_id["scientific_review_wallet_certificates"].anchor_audit_note)
        self.assertEqual(
            report_by_id["eidas_regulation_business_wallet"].source_role_level,
            SourceRoleLevel.HIGH,
        )


if __name__ == "__main__":
    unittest.main()
