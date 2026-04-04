from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import List, Optional

from eubw_researcher.answering import build_provisional_grouping, supports_provisional_grouping
from eubw_researcher.models import ClaimTarget, ClaimType, QueryIntent, SourceKind, SourceRoleLevel


def _intent(*, labels: List[Optional[str]]) -> QueryIntent:
    return QueryIntent(
        question="Synthetic grouping question?",
        intent_type="wallet_requirements_summary",
        eu_first=True,
        claim_targets=[
            ClaimTarget(
                target_id=f"claim_{index}",
                claim_text=f"Synthetic claim {index}",
                claim_type=ClaimType.SYNTHESIS,
                required_source_role_level=SourceRoleLevel.HIGH,
                preferred_kinds=[SourceKind.REGULATION],
                scope_terms=["synthetic"],
                primary_terms=["claim"],
                support_groups=[["synthetic"]],
                contradiction_groups=[],
                grouping_label=label,
            )
            for index, label in enumerate(labels, start=1)
        ],
        preferred_kinds=[SourceKind.REGULATION],
    )


def _entry(claim_id: str, *source_ids: str) -> SimpleNamespace:
    return SimpleNamespace(
        claim_id=claim_id,
        citations=[SimpleNamespace(source_id=source_id) for source_id in source_ids],
    )


class ProvisionalGroupingTests(unittest.TestCase):
    def test_supports_provisional_grouping_returns_false_without_labels(self) -> None:
        self.assertFalse(supports_provisional_grouping(_intent(labels=[None, None])))

    def test_supports_provisional_grouping_returns_true_when_any_target_has_label(self) -> None:
        self.assertTrue(supports_provisional_grouping(_intent(labels=[None, "Certificates"])))

    def test_build_provisional_grouping_returns_empty_when_intent_has_no_group_labels(self) -> None:
        groups = build_provisional_grouping(
            _intent(labels=[None]),
            [_entry("claim_1", "source-a")],
        )

        self.assertEqual(groups, [])

    def test_build_provisional_grouping_combines_matching_claims_and_deduplicates_sources(self) -> None:
        groups = build_provisional_grouping(
            _intent(labels=["Certificates", "Certificates"]),
            [
                _entry("claim_1", "source-a", "source-b"),
                _entry("claim_2", "source-b", "source-c"),
            ],
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].label, "Certificates")
        self.assertEqual(groups[0].claim_ids, ["claim_1", "claim_2"])
        self.assertEqual(groups[0].source_ids, ["source-a", "source-b", "source-c"])
        self.assertTrue(groups[0].provisional)

    def test_build_provisional_grouping_sorts_groups_and_skips_unmatched_entries(self) -> None:
        groups = build_provisional_grouping(
            _intent(labels=["Beta", "Alpha"]),
            [
                _entry("claim_2", "source-b"),
                _entry("claim_1", "source-a"),
                _entry("unmatched", "source-z"),
            ],
        )

        self.assertEqual([group.label for group in groups], ["Alpha", "Beta"])
        self.assertEqual(groups[0].claim_ids, ["claim_2"])
        self.assertEqual(groups[1].claim_ids, ["claim_1"])

    def test_build_provisional_grouping_returns_empty_when_supported_but_no_entries_match(self) -> None:
        groups = build_provisional_grouping(
            _intent(labels=["Certificates"]),
            [_entry("different_claim", "source-a")],
        )

        self.assertEqual(groups, [])
