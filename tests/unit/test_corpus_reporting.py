from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.corpus.reporting import (
    build_corpus_state_snapshot,
    render_corpus_coverage_summary_md,
    render_corpus_selection_summary_md,
)
from eubw_researcher.models import (
    CorpusCoverageFamily,
    CorpusCoverageReport,
    SourceCatalog,
    SourceCatalogEntry,
    SourceKind,
    SourceRoleLevel,
)


def _make_catalog() -> SourceCatalog:
    return SourceCatalog(
        entries=[
            SourceCatalogEntry(
                source_id="regulation_a",
                title="Regulation A",
                source_kind=SourceKind.REGULATION,
                source_role_level=SourceRoleLevel.HIGH,
                jurisdiction="EU",
                publication_status="official_journal",
                publication_date=None,
                local_path=None,
                canonical_url=None,
                admission_reason="Primary governing act",
            ),
            SourceCatalogEntry(
                source_id="implementing_b",
                title="Implementing Act B",
                source_kind=SourceKind.IMPLEMENTING_ACT,
                source_role_level=SourceRoleLevel.HIGH,
                jurisdiction="EU",
                publication_status="official_journal",
                publication_date=None,
                local_path=None,
                canonical_url=None,
                admission_reason="Annex detail",
            ),
            SourceCatalogEntry(
                source_id="standard_c",
                title="Technical Standard C",
                source_kind=SourceKind.TECHNICAL_STANDARD,
                source_role_level=SourceRoleLevel.HIGH,
                jurisdiction="international",
                publication_status="standard",
                publication_date=None,
                local_path=None,
                canonical_url=None,
                admission_reason=None,
            ),
            SourceCatalogEntry(
                source_id="artifact_d",
                title="Project Artifact D",
                source_kind=SourceKind.PROJECT_ARTIFACT,
                source_role_level=SourceRoleLevel.MEDIUM,
                jurisdiction="EU",
                publication_status="living_document",
                publication_date=None,
                local_path=None,
                canonical_url=None,
                admission_reason="ARF reference",
            ),
        ]
    )


def _make_coverage_report(passed: bool = True) -> CorpusCoverageReport:
    families = [
        CorpusCoverageFamily(
            family_id="governing_eu_regulation",
            minimum_count=1,
            admitted_count=1,
            admitted_source_ids=["regulation_a"],
            missing=False,
        ),
        CorpusCoverageFamily(
            family_id="implementing_act_or_annex",
            minimum_count=1,
            admitted_count=0 if not passed else 1,
            admitted_source_ids=[] if not passed else ["implementing_b"],
            missing=not passed,
        ),
    ]
    return CorpusCoverageReport(
        catalog_path="/some/path/curated_catalog.json",
        corpus_state_id="abc123def456",
        generation_timestamp="2026-01-01T00:00:00+00:00",
        admitted_source_counts_by_kind={"regulation": 1, "implementing_act": 1 if passed else 0},
        families=families,
        passed=passed,
    )


class TestRenderCorpusSelectionSummaryMd(unittest.TestCase):
    def setUp(self):
        self.catalog = _make_catalog()
        self.output = render_corpus_selection_summary_md(self.catalog)

    def test_contains_header(self):
        self.assertIn("# Corpus Selection Summary", self.output)

    def test_contains_total_count(self):
        self.assertIn("**Total sources:** 4", self.output)

    def test_contains_source_titles(self):
        self.assertIn("Regulation A", self.output)
        self.assertIn("Implementing Act B", self.output)
        self.assertIn("Technical Standard C", self.output)
        self.assertIn("Project Artifact D", self.output)

    def test_contains_kind_labels(self):
        self.assertIn("regulation", self.output)
        self.assertIn("implementing_act", self.output)
        self.assertIn("technical_standard", self.output)
        self.assertIn("project_artifact", self.output)

    def test_high_rank_section_before_medium(self):
        high_pos = self.output.index("High-rank")
        medium_pos = self.output.index("Medium-rank")
        self.assertLess(high_pos, medium_pos)

    def test_contains_admission_reason(self):
        self.assertIn("Primary governing act", self.output)
        self.assertIn("ARF reference", self.output)

    def test_no_timestamp(self):
        import re
        self.assertFalse(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", self.output))


class TestRenderCorpusCoverageSummaryMd(unittest.TestCase):
    def test_pass_output(self):
        report = _make_coverage_report(passed=True)
        output = render_corpus_coverage_summary_md(report)
        self.assertIn("# Corpus Coverage Summary", output)
        self.assertIn("abc123def456", output)
        self.assertIn("PASS", output)
        self.assertIn("governing_eu_regulation", output)
        self.assertIn("implementing_act_or_annex", output)

    def test_fail_output(self):
        report = _make_coverage_report(passed=False)
        output = render_corpus_coverage_summary_md(report)
        self.assertIn("FAIL", output)

    def test_no_timestamp(self):
        report = _make_coverage_report()
        output = render_corpus_coverage_summary_md(report)
        # generation_timestamp from the report must not bleed into the md
        self.assertNotIn("2026-01-01T00:00:00", output)


class TestBuildCorpusStateSnapshot(unittest.TestCase):
    def setUp(self):
        self.catalog = _make_catalog()
        self.snapshot = build_corpus_state_snapshot(
            self.catalog,
            corpus_state_id="abc123",
            catalog_path=Path("/repo/artifacts/real_corpus/curated_catalog.json"),
        )

    def test_required_keys_present(self):
        for key in ("corpus_state_id", "catalog_path", "total_sources",
                    "counts_by_kind", "counts_by_role_level", "source_ids"):
            self.assertIn(key, self.snapshot)

    def test_no_generation_timestamp(self):
        self.assertNotIn("generation_timestamp", self.snapshot)

    def test_total_sources(self):
        self.assertEqual(self.snapshot["total_sources"], 4)

    def test_counts_by_kind(self):
        self.assertEqual(self.snapshot["counts_by_kind"]["regulation"], 1)
        self.assertEqual(self.snapshot["counts_by_kind"]["implementing_act"], 1)
        self.assertEqual(self.snapshot["counts_by_kind"]["technical_standard"], 1)
        self.assertEqual(self.snapshot["counts_by_kind"]["project_artifact"], 1)
        self.assertNotIn("commentary", self.snapshot["counts_by_kind"])

    def test_counts_by_role_level(self):
        self.assertEqual(self.snapshot["counts_by_role_level"]["high"], 3)
        self.assertEqual(self.snapshot["counts_by_role_level"]["medium"], 1)
        self.assertNotIn("low", self.snapshot["counts_by_role_level"])

    def test_source_ids_sorted(self):
        ids = self.snapshot["source_ids"]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(set(ids), {"regulation_a", "implementing_b", "standard_c", "artifact_d"})

    def test_counts_by_kind_key_order(self):
        # Keys must follow SourceKind enum declaration order, not lexicographic
        from eubw_researcher.models import SourceKind
        expected_order = [k.value for k in SourceKind if k.value in self.snapshot["counts_by_kind"]]
        self.assertEqual(list(self.snapshot["counts_by_kind"].keys()), expected_order)

    def test_counts_by_role_level_key_order(self):
        keys = list(self.snapshot["counts_by_role_level"].keys())
        # high must come before medium
        self.assertLess(keys.index("high"), keys.index("medium"))

    def test_deterministic(self):
        snapshot2 = build_corpus_state_snapshot(
            self.catalog,
            corpus_state_id="abc123",
            catalog_path=Path("/repo/artifacts/real_corpus/curated_catalog.json"),
        )
        self.assertEqual(self.snapshot, snapshot2)


if __name__ == "__main__":
    unittest.main()
