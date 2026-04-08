from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.config import load_terminology_config
from eubw_researcher.models import AppliedTermNormalization
from eubw_researcher.retrieval import (
    explain_query_term_normalization,
    normalize_query_terms,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class TerminologyNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.terminology = load_terminology_config(REPO_ROOT / "configs" / "terminology.yaml")

    def test_stable_alias_normalizes_to_canonical_term(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "What requirements apply to the EUBW?",
                self.terminology,
            ),
            "What requirements apply to the business wallet?",
        )

    def test_benign_wording_variant_normalizes_deterministically(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "What information must a wallet relying party provide during registration?",
                self.terminology,
            ),
            "What information must a wallet-relying party provide during registration?",
        )

    def test_ambiguous_term_is_left_unchanged(self) -> None:
        question = "What registration rules apply to each party?"
        self.assertEqual(normalize_query_terms(question, self.terminology), question)

    def test_unrelated_text_is_unchanged(self) -> None:
        question = "Give me an overview of Union rules for company supervision."
        self.assertEqual(normalize_query_terms(question, self.terminology), question)

    def test_access_cert_alias_requires_wallet_specific_context(self) -> None:
        question = "How should we rotate an access cert for internal API clients?"
        self.assertEqual(normalize_query_terms(question, self.terminology), question)
        self.assertEqual(
            explain_query_term_normalization(question, self.terminology),
            [],
        )

    def test_access_cert_alias_normalizes_with_wallet_specific_context(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "What national guidance exists for Business Wallet access cert handling?",
                self.terminology,
            ),
            "What national guidance exists for Business Wallet access certificate handling?",
        )

    def test_applied_mappings_are_inspectable_and_deterministic(self) -> None:
        self.assertEqual(
            explain_query_term_normalization(
                "Does the EUBW wallet relying party need an authorisation server and access cert?",
                self.terminology,
            ),
            [
                AppliedTermNormalization("eubw", "business wallet"),
                AppliedTermNormalization("wallet relying party", "wallet-relying party"),
                AppliedTermNormalization("authorisation server", "authorization server"),
                AppliedTermNormalization("access cert", "access certificate"),
            ],
        )

    def test_applied_mappings_are_reported_in_textual_order(self) -> None:
        self.assertEqual(
            explain_query_term_normalization(
                "Does the authorisation server help the EUBW wallet relying party?",
                self.terminology,
            ),
            [
                AppliedTermNormalization("authorisation server", "authorization server"),
                AppliedTermNormalization("eubw", "business wallet"),
                AppliedTermNormalization("wallet relying party", "wallet-relying party"),
            ],
        )
