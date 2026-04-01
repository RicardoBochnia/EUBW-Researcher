from __future__ import annotations

import unittest
from pathlib import Path

from eubw_researcher.config import load_web_allowlist
from eubw_researcher.models import SourceKind
from eubw_researcher.web import validate_domain


REPO_ROOT = Path(__file__).resolve().parents[2]


class WebAllowlistTests(unittest.TestCase):
    def test_validate_domain_accepts_allowlisted_domain_and_rejects_other_domain(self) -> None:
        allowlist = load_web_allowlist(REPO_ROOT / "configs" / "web_allowlist.yaml")
        self.assertTrue(validate_domain("https://openid.net/specs/openid-4-vp", allowlist))
        self.assertFalse(validate_domain("https://vendor.example/blog", allowlist))
        self.assertTrue(allowlist.discovery_urls_for_kind(SourceKind.TECHNICAL_STANDARD))
        technical_policy = allowlist.policy_for_domain("openid.net")
        self.assertIsNotNone(technical_policy)
        self.assertTrue(technical_policy.allowed_path_prefixes)
