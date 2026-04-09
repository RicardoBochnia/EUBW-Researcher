from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from eubw_researcher.config import (
    load_runtime_config,
    load_source_hierarchy,
    load_terminology_config,
    load_web_allowlist,
)
from eubw_researcher.corpus import ingest_catalog, load_source_catalog
from eubw_researcher.models import ClaimState, SourceKind, SourceOrigin
from eubw_researcher.pipeline import ResearchPipeline


REPO_ROOT = Path(__file__).resolve().parents[2]


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.yaml")
        hierarchy = load_source_hierarchy(REPO_ROOT / "configs" / "source_hierarchy.yaml")
        terminology = load_terminology_config(REPO_ROOT / "configs" / "terminology.yaml")
        allowlist = load_web_allowlist(REPO_ROOT / "configs" / "web_allowlist.yaml")
        catalog = load_source_catalog(
            REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        )
        self.pipeline = ResearchPipeline(
            runtime_config=runtime,
            hierarchy=hierarchy,
            allowlist=allowlist,
            ingestion_bundle=ingest_catalog(catalog),
            terminology=terminology,
        )

    def test_allowed_web_kinds_does_not_fall_back_to_lower_rank_when_same_rank_is_already_local(self) -> None:
        target = SimpleNamespace(
            preferred_kinds=[SourceKind.TECHNICAL_STANDARD, SourceKind.PROJECT_ARTIFACT],
            required_source_role_level=self.pipeline.hierarchy.role_for(SourceKind.TECHNICAL_STANDARD),
        )
        ledger_entry = SimpleNamespace(
            final_claim_state=ClaimState.OPEN,
            supporting_evidence=[
                SimpleNamespace(
                    source_kind=SourceKind.TECHNICAL_STANDARD,
                    source_origin=SourceOrigin.LOCAL,
                )
            ],
            contradicting_evidence=[],
            governing_evidence=[],
        )

        allowed_kinds = self.pipeline._allowed_web_kinds(target, ledger_entry)

        self.assertEqual(allowed_kinds, [])
