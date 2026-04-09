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

    def test_business_wallet_long_form_alias_normalizes_to_canonical_term(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "What requirements apply to the European Business Wallet?",
                self.terminology,
            ),
            "What requirements apply to the business wallet?",
        )

    def test_business_wallet_acronym_alias_normalizes_to_canonical_term(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "What requirements apply to the EBW?",
                self.terminology,
            ),
            "What requirements apply to the business wallet?",
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

    def test_rpac_alias_requires_wallet_or_certificate_context(self) -> None:
        question = "What does RPAC mean in our internal provisioning stack?"
        self.assertEqual(normalize_query_terms(question, self.terminology), question)
        self.assertEqual(
            explain_query_term_normalization(question, self.terminology),
            [],
        )

    def test_rpac_alias_normalizes_with_wallet_context(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "Does a wallet-relying party need an RPAC for onboarding?",
                self.terminology,
            ),
            "Does a wallet-relying party need an access certificate for onboarding?",
        )

    def test_wrpac_and_wrprc_aliases_normalize_with_wallet_context(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "Compare the wallet-relying party WRPAC and WRPRC obligations.",
                self.terminology,
            ),
            (
                "Compare the wallet-relying party access certificate and "
                "registration certificate obligations."
            ),
        )

    def test_pid_alias_requires_domain_context(self) -> None:
        question = "How should we store a PID in the image-processing pipeline?"
        self.assertEqual(normalize_query_terms(question, self.terminology), question)
        self.assertEqual(
            explain_query_term_normalization(question, self.terminology),
            [],
        )

    def test_pid_alias_normalizes_in_wallet_context(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "How should a wallet issuer validate PID attestation inputs?",
                self.terminology,
            ),
            "How should a wallet issuer validate person identification data attestation inputs?",
        )

    def test_qeaa_alias_normalizes_in_wallet_context(self) -> None:
        self.assertEqual(
            normalize_query_terms(
                "How should the wallet validate QEAA attestation attributes?",
                self.terminology,
            ),
            "How should the wallet validate qualified electronic attestation of attributes attestation attributes?",
        )

    def test_pid_provider_alias_wins_before_generic_pid_alias(self) -> None:
        self.assertEqual(
            explain_query_term_normalization(
                "How should a wallet handle a PID provider registration flow?",
                self.terminology,
            ),
            [
                AppliedTermNormalization(
                    "pid provider",
                    "provider of person identification data",
                )
            ],
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
