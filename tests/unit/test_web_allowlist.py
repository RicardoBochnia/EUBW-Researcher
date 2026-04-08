from __future__ import annotations

from dataclasses import replace
import json
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from eubw_researcher.config import load_runtime_config, load_web_allowlist
from eubw_researcher.models import (
    DiscoveryEntrypoint,
    SourceKind,
    SourceRoleLevel,
    WebAllowlistConfig,
    WebDomainPolicy,
)
from eubw_researcher.web import validate_domain
from eubw_researcher.web.fetch import (
    _admissible_document_policy,
    _discover_candidate_urls,
    _followable_discovery_link,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class WebAllowlistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.allowlist = load_web_allowlist(REPO_ROOT / "configs" / "web_allowlist.yaml")

    def test_validate_domain_accepts_allowlisted_domain_and_rejects_other_domain(self) -> None:
        self.assertTrue(validate_domain("https://openid.net/specs/openid-4-vp", self.allowlist))
        self.assertFalse(validate_domain("https://vendor.example/blog", self.allowlist))
        self.assertTrue(self.allowlist.discovery_entrypoints_for_kind(SourceKind.TECHNICAL_STANDARD))
        technical_policy = self.allowlist.policy_for_domain("openid.net")
        self.assertIsNotNone(technical_policy)
        self.assertTrue(technical_policy.crawl_path_prefixes)
        self.assertTrue(technical_policy.admission_path_prefixes)

    def test_discovery_entrypoints_for_kind_returns_only_matching_policy_urls(self) -> None:
        self.assertEqual(
            [
                entrypoint.url_template
                for entrypoint in self.allowlist.discovery_entrypoints_for_kind(
                    SourceKind.TECHNICAL_STANDARD
                )
            ],
            ["https://openid.net/specs/"],
        )
        self.assertEqual(
            sorted(
                entrypoint.url_template
                for entrypoint in self.allowlist.discovery_entrypoints_for_kind(
                    SourceKind.PROJECT_ARTIFACT
                )
            ),
            sorted(
                [
                    "https://commission.europa.eu/topics/digital-economy-and-society/european-digital-identity_en",
                    "https://digital-strategy.ec.europa.eu/en/policies/eudi-wallet-implementation",
                    "https://docs.eudi.dev/latest/",
                    "https://eudi-walletconsortium.org/",
                    "https://eudi.dev/latest/technical-specifications/",
                    "https://eu-digital-identity-wallet.github.io/eudi-doc-architecture-and-reference-framework/latest/",
                ]
            ),
        )
        self.assertEqual(
            [
                (entrypoint.url_template, entrypoint.strategy)
                for entrypoint in self.allowlist.discovery_entrypoints_for_kind(
                    SourceKind.REGULATION
                )
            ],
            [
                (
                    "https://eur-lex.europa.eu/search.html?text={query}&lang=en&type=quick",
                    "official_search",
                )
            ],
        )

    def test_admissible_document_policy_enforces_path_prefixes_and_blocked_keywords(self) -> None:
        policy = self.allowlist.policy_for_domain("openid.net")
        self.assertIsNotNone(policy)
        assert policy is not None

        self.assertIsNotNone(
            _admissible_document_policy(
                "https://openid.net/specs/openid-4-verifiable-presentations-1_0.html",
                policy,
                self.allowlist,
            )
        )
        self.assertIsNone(
            _admissible_document_policy(
                "https://openid.net/news/openid4vp-update",
                policy,
                self.allowlist,
            )
        )
        self.assertIsNone(
            _admissible_document_policy(
                "https://openid.net/specification/openid4vp",
                policy,
                self.allowlist,
            )
        )
        self.assertIsNone(
            _admissible_document_policy(
                "https://openid.net/certification/openid4vp",
                policy,
                self.allowlist,
            )
        )

    def test_followable_discovery_link_requires_explicit_cross_domain_permission(self) -> None:
        allowlist = WebAllowlistConfig(
            allowed_domains=["example.test", "cdn.example.test", "other.example.test"],
            domain_policies=[
                WebDomainPolicy(
                    domain="example.test",
                    source_kind=SourceKind.TECHNICAL_STANDARD,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="international",
                    discovery_entrypoints=[
                        DiscoveryEntrypoint(
                            entrypoint_id="example_specs",
                            url_template="https://example.test/specs/",
                            strategy="index_crawl",
                        )
                    ],
                    crawl_path_prefixes=["/specs/"],
                    admission_path_prefixes=["/specs/"],
                    allowed_cross_domain_domains=["cdn.example.test"],
                ),
                WebDomainPolicy(
                    domain="cdn.example.test",
                    source_kind=SourceKind.TECHNICAL_STANDARD,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="international",
                    crawl_path_prefixes=["/mirror/"],
                    admission_path_prefixes=["/mirror/"],
                ),
                WebDomainPolicy(
                    domain="other.example.test",
                    source_kind=SourceKind.TECHNICAL_STANDARD,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="international",
                    crawl_path_prefixes=["/mirror/"],
                    admission_path_prefixes=["/mirror/"],
                ),
            ],
        )
        policy = allowlist.policy_for_domain("example.test")
        self.assertIsNotNone(policy)
        assert policy is not None

        self.assertTrue(
            _followable_discovery_link(
                "https://cdn.example.test/mirror/openid4vp.html",
                policy,
                allowlist,
            )
        )
        self.assertFalse(
            _followable_discovery_link(
                "https://other.example.test/mirror/openid4vp.html",
                policy,
                allowlist,
            )
        )

    def test_discovery_caps_selected_candidates_and_records_discovery_only_events(self) -> None:
        policy = self.allowlist.policy_for_domain("openid.net")
        self.assertIsNotNone(policy)
        assert policy is not None

        runtime = replace(
            load_runtime_config(REPO_ROOT / "configs" / "runtime.yaml"),
            web_discovery_max_pages=1,
            web_discovery_max_depth=2,
            web_discovery_max_candidates_per_kind=2,
        )

        discovery_html = b"""
        <html><body>
        <a href="/specs/openid4vp-wallet-metadata.html">OpenID wallet metadata specification</a>
        <a href="/specs/openid4vci-token-endpoint.html">OpenID token endpoint specification</a>
        <a href="/specs/registration-overview.html">Registration overview</a>
        <a href="/news/ignore-me.html">News item</a>
        </body></html>
        """

        with patch(
            "eubw_researcher.web.fetch._request_url",
            return_value=(discovery_html, "text/html; charset=utf-8"),
        ):
            selected_urls, records = _discover_candidate_urls(
                sub_question="Compare OpenID4VCI and OpenID4VP on token endpoint and wallet metadata handling.",
                discovery_query="OpenID4VCI OpenID4VP token endpoint wallet metadata",
                entrypoint=policy.discovery_entrypoints[0],
                policy=policy,
                allowlist=self.allowlist,
                runtime_config=runtime,
            )

        self.assertEqual(len(selected_urls), 2)
        self.assertTrue(all(url.startswith("https://openid.net/specs/") for url in selected_urls))
        self.assertEqual(
            [record.record_type for record in records].count("discovery"),
            1,
        )
        self.assertEqual(
            [record.record_type for record in records].count("discovered_link"),
            2,
        )

    def test_policy_lookup_is_exact_host_only(self) -> None:
        self.assertIsNone(self.allowlist.policy_for_domain("docs.openid.net"))
        self.assertIsNone(self.allowlist.policy_for_domain_and_kind("docs.eudi.dev", SourceKind.TECHNICAL_STANDARD))
        self.assertIsNotNone(
            self.allowlist.policy_for_domain_and_kind(
                "docs.eudi.dev",
                SourceKind.PROJECT_ARTIFACT,
            )
        )
        self.assertIsNone(
            self.allowlist.policy_for_domain_and_kind(
                "sub.docs.eudi.dev",
                SourceKind.PROJECT_ARTIFACT,
            )
        )

    def test_policy_lookup_can_select_multiple_policies_for_same_host_by_kind(self) -> None:
        allowlist = WebAllowlistConfig(
            allowed_domains=["example.test"],
            domain_policies=[
                WebDomainPolicy(
                    domain="example.test",
                    source_kind=SourceKind.REGULATION,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="EU",
                    policy_id="example_regulation",
                    admission_path_prefixes=["/legal/"],
                ),
                WebDomainPolicy(
                    domain="example.test",
                    source_kind=SourceKind.IMPLEMENTING_ACT,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="EU",
                    policy_id="example_implementing_act",
                    admission_path_prefixes=["/acts/"],
                ),
            ],
        )

        self.assertEqual(len(allowlist.policies_for_domain("example.test")), 2)
        self.assertEqual(
            allowlist.policy_for_domain_and_kind("example.test", SourceKind.REGULATION).policy_id,
            "example_regulation",
        )
        self.assertEqual(
            allowlist.policy_for_domain_and_kind("example.test", SourceKind.IMPLEMENTING_ACT).policy_id,
            "example_implementing_act",
        )

    def test_web_domain_policy_migrates_legacy_fields_into_new_config_shape(self) -> None:
        policy = WebDomainPolicy(
            domain="example.test",
            source_kind=SourceKind.TECHNICAL_STANDARD,
            source_role_level=SourceRoleLevel.HIGH,
            jurisdiction="international",
            discovery_urls=["https://example.test/specs/"],
            allowed_path_prefixes=["/specs/"],
        )

        self.assertEqual(
            [(entry.entrypoint_id, entry.url_template, entry.strategy) for entry in policy.discovery_entrypoints],
            [("example.test:technical_standard:legacy:1", "https://example.test/specs/", "index_crawl")],
        )
        self.assertEqual(policy.crawl_path_prefixes, ["/specs/"])
        self.assertEqual(policy.admission_path_prefixes, ["/specs/"])

    def test_loader_rejects_official_search_entrypoint_without_query_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "web_allowlist.json"
            config_path.write_text(
                json.dumps(
                    {
                        "allowed_domains": ["eur-lex.europa.eu"],
                        "domain_policies": [
                            {
                                "policy_id": "invalid_official_search",
                                "domain": "eur-lex.europa.eu",
                                "source_kind": "regulation",
                                "source_role_level": "high",
                                "jurisdiction": "EU",
                                "seed_urls": [],
                                "discovery_entrypoints": [
                                    {
                                        "entrypoint_id": "broken_search",
                                        "url_template": "https://eur-lex.europa.eu/search.html?lang=en&type=quick",
                                        "strategy": "official_search",
                                    }
                                ],
                                "crawl_path_prefixes": ["/legal-content/"],
                                "admission_path_prefixes": ["/legal-content/", "/eli/"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"official_search entrypoint 'broken_search' must contain \{query\}",
            ):
                load_web_allowlist(config_path)
