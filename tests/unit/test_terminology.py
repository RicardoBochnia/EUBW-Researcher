from __future__ import annotations

import unittest

from eubw_researcher.retrieval import (
    explain_query_term_normalization,
    normalize_query_terms,
)


class TerminologyNormalizationTests(unittest.TestCase):
    def test_stable_alias_normalizes_to_canonical_term(self) -> None:
        self.assertEqual(
            normalize_query_terms("What requirements apply to the EUBW?"),
            "What requirements apply to the business wallet?",
        )

    def test_benign_wording_variant_normalizes_deterministically(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "What information must a wallet relying party provide during registration?"
            ),
            "What information must a wallet-relying party provide during registration?",
        )

    def test_ambiguous_term_is_left_unchanged(self) -> None:
        question = "What registration rules apply to each party?"
        self.assertEqual(normalize_query_terms(question), question)

    def test_unrelated_text_is_unchanged(self) -> None:
        question = "Give me an overview of Union rules for company supervision."
        self.assertEqual(normalize_query_terms(question), question)

    def test_access_cert_alias_requires_wallet_specific_context(self) -> None:
        question = "How should we rotate an access cert for internal API clients?"
        self.assertEqual(normalize_query_terms(question), question)
        self.assertEqual(explain_query_term_normalization(question), [])

    def test_applied_mappings_are_inspectable_and_deterministic(self) -> None:
        self.assertEqual(
            explain_query_term_normalization(
                "Does the EUBW wallet relying party need an authorisation server and access cert?"
            ),
            [
                ("eubw", "business wallet"),
                ("wallet relying party", "wallet-relying party"),
                ("authorisation server", "authorization server"),
                ("access cert", "access certificate"),
            ],
        )
