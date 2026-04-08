from __future__ import annotations

import unittest

from eubw_researcher.retrieval.text_normalization import (
    normalize_text_for_matching,
    tokenize_normalized_text,
)


class TextNormalizationTests(unittest.TestCase):
    def test_normalize_text_for_matching_transliterates_german_characters(self) -> None:
        self.assertEqual(
            normalize_text_for_matching("Straße Maßnahme Durchführungsgesetz"),
            "strasse massnahme durchfuehrungsgesetz",
        )

    def test_tokenize_normalized_text_uses_transliterated_forms(self) -> None:
        self.assertEqual(
            tokenize_normalized_text("Digitale Identität und EUDI-Brieftasche"),
            ["digitale", "identitaet", "und", "eudi", "brieftasche"],
        )


if __name__ == "__main__":
    unittest.main()
