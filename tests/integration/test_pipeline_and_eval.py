from __future__ import annotations

import json
import shlex
import subprocess
import sys
import threading
import tempfile
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from eubw_researcher.config import (
    load_archive_corpus_config,
    load_runtime_config,
    load_source_hierarchy,
    load_web_allowlist,
)
from eubw_researcher.corpus import (
    build_catalog_from_archive,
    ingest_catalog,
    load_source_catalog,
    write_source_catalog,
)
from eubw_researcher.evaluation import run_all_scenarios
from eubw_researcher.evaluation.runner import write_artifact_bundle
from eubw_researcher.models import (
    ClaimState,
    ScenarioVerdict,
    SourceCatalog,
    SourceCatalogEntry,
    SourceKind,
    SourceRoleLevel,
    WebAllowlistConfig,
    WebDomainPolicy,
)
from eubw_researcher.pipeline import ResearchPipeline


REPO_ROOT = Path(__file__).resolve().parents[2]


def _minimal_pdf_bytes(*lines: str) -> bytes:
    operations = ["BT", "/F1 12 Tf"]
    y_position = 720
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        operations.append(f"72 {y_position} Td ({escaped}) Tj")
        y_position -= 24
    operations.append("ET")
    stream = "\n".join(operations).encode("latin-1")
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >> endobj\n"
        + f"4 0 obj << /Length {len(stream)} >>\n".encode("latin-1")
        + b"stream\n"
        + stream
        + b"\nendstream\nendobj\n"
        + b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )


class PipelineAndEvalIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime = load_runtime_config(REPO_ROOT / "configs" / "runtime.yaml")
        hierarchy = load_source_hierarchy(REPO_ROOT / "configs" / "source_hierarchy.yaml")
        allowlist = load_web_allowlist(REPO_ROOT / "configs" / "web_allowlist.yaml")
        catalog = load_source_catalog(
            REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        )
        bundle = ingest_catalog(catalog)
        self.pipeline = ResearchPipeline(
            runtime_config=runtime,
            hierarchy=hierarchy,
            allowlist=allowlist,
            ingestion_bundle=bundle,
        )
        self.catalog = catalog
        self.runtime = runtime
        self.hierarchy = hierarchy
        self.allowlist = allowlist

    def _build_real_corpus_pipeline(self) -> tuple[ResearchPipeline, object]:
        archive_config = load_archive_corpus_config(
            REPO_ROOT / "configs" / "real_corpus_selection.yaml"
        )
        real_catalog = build_catalog_from_archive(archive_config)
        real_bundle = ingest_catalog(real_catalog)
        pipeline = ResearchPipeline(
            runtime_config=self.runtime,
            hierarchy=self.hierarchy,
            allowlist=self.allowlist,
            ingestion_bundle=real_bundle,
        )
        return pipeline, real_catalog

    def _ensure_default_real_catalog(self) -> Path:
        catalog_path = REPO_ROOT / "artifacts" / "real_corpus" / "curated_catalog.json"
        if catalog_path.exists():
            return catalog_path
        _, real_catalog = self._build_real_corpus_pipeline()
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        write_source_catalog(real_catalog, catalog_path)
        return catalog_path

    def _build_bounded_test_catalog(self, root: Path) -> Path:
        """Create a minimal real-corpus-shaped catalog for coverage-gate tests."""
        corpus_root = root / "artifacts" / "real_corpus"
        source_root = corpus_root / "sources"
        source_root.mkdir(parents=True, exist_ok=True)
        regulation_path = source_root / "regulation.md"
        regulation_path.write_text(
            "# Article 1 Business Wallet compliance record\n\n"
            "The Business Wallet provider keeps a compliance record.\n",
            encoding="utf-8",
        )
        catalog = SourceCatalog(
            entries=[
                SourceCatalogEntry(
                    source_id="synthetic_regulation",
                    title="Synthetic Regulation Source",
                    source_kind=SourceKind.REGULATION,
                    source_role_level=SourceRoleLevel.HIGH,
                    jurisdiction="EU",
                    publication_status="official_journal",
                    publication_date=None,
                    local_path=regulation_path,
                    canonical_url="https://example.test/synthetic-regulation",
                    anchorability_hints=["markdown_headings", "expect_anchors", "article_level"],
                )
            ]
        )
        catalog_path = corpus_root / "curated_catalog.json"
        write_source_catalog(catalog, catalog_path)
        return catalog_path

    def test_scenario_c_returns_confirmed_standard_based_answer(self) -> None:
        result = self.pipeline.answer_question(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
        )

        self.assertEqual(len(result.approved_entries), 2)
        self.assertTrue(
            all(entry.final_claim_state == ClaimState.CONFIRMED for entry in result.approved_entries)
        )
        self.assertIn("Confirmed:", result.rendered_answer)
        self.assertIn("OpenID for Verifiable Credential Issuance 1.0 Draft 13", result.rendered_answer)
        self.assertIn("OpenID for Verifiable Presentations 1.0 Draft 18", result.rendered_answer)
        self.assertNotIn("SSI Commentary Blog on Authorization Servers", result.rendered_answer)

    def test_all_configured_eval_scenarios_now_produce_passing_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for scenario_id, verdict in run_all_scenarios(
                repo_root=REPO_ROOT,
                output_dir=Path(tmp_dir),
            ):
                scenario_dir = Path(tmp_dir) / scenario_id
                self.assertTrue(verdict.passed, msg=f"{scenario_id}: {verdict.checks}")
                self.assertTrue(any(check.startswith("intent_type:") for check in verdict.checks))
                self.assertTrue((scenario_dir / "ledger_entries.json").exists())
                self.assertTrue((scenario_dir / "approved_ledger.json").exists())
                self.assertTrue((scenario_dir / "verdict.json").exists())
                self.assertTrue((scenario_dir / "web_fetch_records.json").exists())
                self.assertTrue((scenario_dir / "manual_review.json").exists())
                self.assertTrue((scenario_dir / "manual_review_report.md").exists())
                self.assertTrue((scenario_dir / "pinpoint_evidence.json").exists())
                self.assertTrue((scenario_dir / "answer_alignment.json").exists())
                self.assertTrue((scenario_dir / "blind_validation_report.json").exists())
                self.assertTrue((scenario_dir / "ingestion_report.json").exists())
                if scenario_id == "primary_success_scenario":
                    self.assertTrue((scenario_dir / "provisional_grouping.json").exists())

    def test_missed_governing_source_creates_gap_record_and_visible_blocked_state(self) -> None:
        filtered_catalog = load_source_catalog(
            REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
        )
        filtered_catalog.entries = [
            entry
            for entry in filtered_catalog.entries
            if entry.source_id != "eidas_regulation_business_wallet"
        ]
        filtered_bundle = ingest_catalog(filtered_catalog)
        filtered_pipeline = ResearchPipeline(
            runtime_config=self.runtime,
            hierarchy=self.hierarchy,
            allowlist=self.allowlist,
            ingestion_bundle=filtered_bundle,
        )

        result = filtered_pipeline.answer_question(
            "Is the registration certificate mandatory at EU level, or is that delegated to member states?"
        )
        self.assertGreaterEqual(len(result.gap_records), 1)
        self.assertNotIn("Blocked:", result.rendered_answer)
        self.assertNotIn(
            "At EU level, the qualified registration certificate identifies the organisation that uses the business wallet.",
            result.rendered_answer,
        )
        self.assertIn("No approved answer could be composed", result.rendered_answer)
        self.assertTrue(
            any(entry.final_claim_state == ClaimState.BLOCKED for entry in result.ledger_entries)
        )

    def test_open_claim_creates_gap_record_without_rendering_blocked_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            conflicting_standard = tmp_dir_path / "conflicting_openid4vp.md"
            conflicting_standard.write_text(
                "# Conflicting OpenID4VP Profile\n\n"
                "## Section 3.2 Verifier-initiated presentation request\n"
                "The Verifier presentation request must obtain an access token from a Credential Issuer token endpoint before the Wallet flow can proceed.\n",
                encoding="utf-8",
            )
            temp_catalog_path = tmp_dir_path / "catalog.json"
            catalog_payload = {
                "sources": [
                    {
                        "source_id": entry.source_id,
                        "title": entry.title,
                        "source_kind": entry.source_kind.value,
                        "source_role_level": entry.source_role_level.value,
                        "jurisdiction": entry.jurisdiction,
                        "publication_status": entry.publication_status,
                        "publication_date": entry.publication_date,
                        "local_path": str(entry.local_path),
                        "canonical_url": entry.canonical_url,
                        "anchorability_hints": entry.anchorability_hints,
                    }
                    for entry in self.catalog.entries
                ]
            }
            catalog_payload["sources"].append(
                {
                    "source_id": "conflicting_openid4vp_profile",
                    "title": "Conflicting OpenID4VP Profile",
                    "source_kind": "technical_standard",
                    "source_role_level": "high",
                    "jurisdiction": "international",
                    "publication_status": "profile",
                    "publication_date": "2025-07-01",
                    "local_path": str(conflicting_standard),
                    "canonical_url": None,
                    "anchorability_hints": ["markdown_headings", "expect_anchors", "section_level"],
                }
            )
            temp_catalog_path.write_text(json.dumps(catalog_payload, indent=2), encoding="utf-8")
            temp_catalog = load_source_catalog(temp_catalog_path)
            temp_bundle = ingest_catalog(temp_catalog)
            temp_pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=self.allowlist,
                ingestion_bundle=temp_bundle,
            )

            result = temp_pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )
            self.assertTrue(
                any(entry.final_claim_state == ClaimState.OPEN for entry in result.ledger_entries)
            )
            self.assertIn("Open:", result.rendered_answer)
            self.assertTrue(
                any(
                    "Contradictory admissible evidence remains unresolved" in gap.reason_local_evidence_insufficient
                    for gap in result.gap_records
                )
            )

    def test_broad_question_surfaces_non_blocking_first_pass_note(self) -> None:
        result = self.pipeline.answer_question(
            "Give me a broad overview of Union rules for wallet-based access and registration."
        )

        self.assertIn("First-pass note:", result.rendered_answer)
        self.assertIn("Broad question: continue with an EU-first first-pass answer.", result.rendered_answer)

    def test_primary_business_wallet_question_produces_provisional_grouping(self) -> None:
        result = self.pipeline.answer_question(
            "What requirements apply to the Business Wallet, and how can they be provisionally structured?"
        )

        self.assertTrue(result.provisional_grouping)
        self.assertTrue(all(group.provisional for group in result.provisional_grouping))
        self.assertTrue(all(group.claim_ids for group in result.provisional_grouping))
        self.assertTrue(all(group.source_ids for group in result.provisional_grouping))
        self.assertGreaterEqual(len(result.provisional_grouping), 2)

    def test_out_of_distribution_business_wallet_question_still_maps_to_grouped_requirements_path(self) -> None:
        result = self.pipeline.answer_question(
            "Map the Union-level obligations for Business Wallet relying parties and cluster them provisionally for research notes."
        )

        self.assertEqual(result.query_intent.intent_type, "wallet_requirements_summary")
        self.assertTrue(result.provisional_grouping)
        self.assertNotIn("Blocked:", result.rendered_answer)

    def test_gap_driven_web_expansion_fetches_allowlisted_official_source(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = (
                    "<html><head><title>OpenID4VP Official Mirror</title></head>"
                    "<body><h1>Section 3.2 Verifier-initiated presentation request</h1>"
                    "<p>The Verifier sends a presentation request directly to the Wallet.</p>"
                    "<p>This specification does not define a dedicated Authorization Server role for the verifier-initiated presentation flow.</p>"
                    "</body></html>"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            seed_url = f"http://127.0.0.1:{server.server_port}/openid4vp"
            custom_allowlist = WebAllowlistConfig(
                allowed_domains=["127.0.0.1"],
                domain_policies=[
                    WebDomainPolicy(
                        domain="127.0.0.1",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        seed_urls=[seed_url],
                        allowed_path_prefixes=["/"],
                    )
                ],
            )
            filtered_catalog = load_source_catalog(
                REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
            )
            filtered_catalog.entries = [
                entry
                for entry in filtered_catalog.entries
                if entry.source_id != "openid4vp_draft18"
            ]
            filtered_bundle = ingest_catalog(filtered_catalog)
            pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=custom_allowlist,
                ingestion_bundle=filtered_bundle,
            )

            result = pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )

            self.assertGreaterEqual(len(result.web_fetch_records), 1)
            self.assertTrue(any(record.allowed for record in result.web_fetch_records))
            self.assertTrue(all(record.metadata_complete for record in result.web_fetch_records if record.allowed))
            self.assertTrue(
                all(
                    record.content_type and record.content_digest and record.provenance_record
                    for record in result.web_fetch_records
                    if record.record_type == "fetch" and record.allowed
                )
            )
            self.assertTrue(
                any(gap.next_allowed_action == "official_web_search" for gap in result.gap_records)
            )
            self.assertTrue(
                all(gap.local_source_layers_searched for gap in result.gap_records if gap.next_allowed_action == "official_web_search")
            )
            self.assertTrue(
                any(
                    citation.source_origin.value == "web"
                    for entry in result.approved_entries
                    for citation in entry.citations
                )
            )
            self.assertIn("OpenID4VP Official Mirror", result.rendered_answer)
            with tempfile.TemporaryDirectory() as tmp_dir:
                write_artifact_bundle(
                    Path(tmp_dir),
                    result,
                    verdict=ScenarioVerdict(
                        scenario_id="synthetic_web_fetch_review",
                        passed=True,
                        checks=[],
                    ),
                    scenario_id="synthetic_web_fetch_review",
                )
                report_text = (Path(tmp_dir) / "manual_review_report.md").read_text()
                self.assertIn("Approved Fetched-Source Evidence", report_text)
                self.assertIn("digest=`", report_text)
                self.assertIn("provenance=`", report_text)
        finally:
            server.shutdown()
            server.server_close()

    def test_web_discovery_fetches_allowlisted_official_candidate_from_index(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/spec-index":
                    body = (
                        "<html><body>"
                        "<a href='/openid4vp-final'>OpenID4VP Final Specification</a>"
                        "</body></html>"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                else:
                    body = (
                        "<html><head><title>OpenID4VP Final Specification</title></head>"
                        "<body><h1>Section 3.2 Verifier-initiated presentation request</h1>"
                        "<p>The Verifier sends a presentation request directly to the Wallet.</p>"
                        "</body></html>"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            discovery_url = f"http://127.0.0.1:{server.server_port}/spec-index"
            custom_allowlist = WebAllowlistConfig(
                allowed_domains=["127.0.0.1"],
                domain_policies=[
                    WebDomainPolicy(
                        domain="127.0.0.1",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        discovery_urls=[discovery_url],
                        allowed_path_prefixes=["/openid4vp", "/spec"],
                    )
                ],
            )
            filtered_catalog = load_source_catalog(
                REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
            )
            filtered_catalog.entries = [
                entry
                for entry in filtered_catalog.entries
                if entry.source_id != "openid4vp_draft18"
            ]
            pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=custom_allowlist,
                ingestion_bundle=ingest_catalog(filtered_catalog),
            )

            result = pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )

            self.assertTrue(any(record.record_type == "discovery" for record in result.web_fetch_records))
            self.assertTrue(any(record.record_type == "discovered_link" for record in result.web_fetch_records))
            discovery_gaps = [
                gap for gap in result.gap_records if gap.next_allowed_action == "official_web_search"
            ]
            self.assertTrue(discovery_gaps)
            self.assertTrue(any(gap.web_discovery_urls_attempted for gap in discovery_gaps))
            self.assertTrue(any(gap.web_fetch_urls_attempted for gap in discovery_gaps))
            self.assertTrue(
                any(
                    record.record_type == "discovered_link"
                    and record.discovered_from
                    and record.discovered_from.endswith("/spec-index")
                    for record in result.web_fetch_records
                )
            )
            self.assertTrue(
                any(citation.source_origin.value == "web" for entry in result.approved_entries for citation in entry.citations)
            )
        finally:
            server.shutdown()
            server.server_close()

    def test_web_expansion_prefers_same_rank_seed_over_lower_rank_seed(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/openid4vp":
                    body = (
                        "<html><head><title>OpenID4VP Official Mirror</title></head>"
                        "<body><h1>Section 3.2 Verifier-initiated presentation request</h1>"
                        "<p>The Verifier sends a presentation request directly to the Wallet.</p>"
                        "</body></html>"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                else:
                    body = (
                        "# Lower rank project note\n\n"
                        "The verifier flow may use intermediary deployment patterns.\n"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            standard_url = f"http://127.0.0.1:{server.server_port}/openid4vp"
            project_url = f"http://localhost:{server.server_port}/project-note"
            custom_allowlist = WebAllowlistConfig(
                allowed_domains=["127.0.0.1", "localhost"],
                domain_policies=[
                    WebDomainPolicy(
                        domain="127.0.0.1",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        seed_urls=[standard_url],
                        allowed_path_prefixes=["/openid4vp"],
                    ),
                    WebDomainPolicy(
                        domain="localhost",
                        source_kind=SourceKind.PROJECT_ARTIFACT,
                        source_role_level=SourceRoleLevel.MEDIUM,
                        jurisdiction="EU",
                        seed_urls=[project_url],
                        allowed_path_prefixes=["/project-note"],
                    ),
                ],
            )
            filtered_catalog = load_source_catalog(
                REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
            )
            filtered_catalog.entries = [
                entry
                for entry in filtered_catalog.entries
                if entry.source_id != "openid4vp_draft18"
            ]
            pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=custom_allowlist,
                ingestion_bundle=ingest_catalog(filtered_catalog),
            )

            result = pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )

            allowed_kinds = {record.source_kind for record in result.web_fetch_records if record.allowed}
            self.assertEqual(allowed_kinds, {SourceKind.TECHNICAL_STANDARD})
            self.assertNotIn("project note", result.rendered_answer.lower())
        finally:
            server.shutdown()
            server.server_close()

    def test_web_expansion_normalizes_fetched_pdf_content(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = _minimal_pdf_bytes(
                    "Section 3.2 Verifier-initiated presentation request",
                    "The Verifier sends a presentation request directly to the Wallet.",
                    "This specification does not define a dedicated Authorization Server role for the verifier-initiated presentation flow.",
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            pdf_url = f"http://127.0.0.1:{server.server_port}/spec.pdf"
            custom_allowlist = WebAllowlistConfig(
                allowed_domains=["127.0.0.1"],
                domain_policies=[
                    WebDomainPolicy(
                        domain="127.0.0.1",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        seed_urls=[pdf_url],
                        allowed_path_prefixes=["/spec.pdf"],
                    )
                ],
            )
            filtered_catalog = load_source_catalog(
                REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
            )
            filtered_catalog.entries = [
                entry
                for entry in filtered_catalog.entries
                if entry.source_id != "openid4vp_draft18"
            ]
            pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=custom_allowlist,
                ingestion_bundle=ingest_catalog(filtered_catalog),
            )

            result = pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )

            self.assertTrue(any(record.metadata_complete for record in result.web_fetch_records if record.allowed))
            self.assertTrue(
                any(
                    citation.source_origin.value == "web"
                    for entry in result.approved_entries
                    for citation in entry.citations
                )
            )
            self.assertIn("Interpretive:", result.rendered_answer)
            self.assertTrue(
                any(
                    report.source_id.startswith("web::technical_standard::")
                    and report.normalization_format == "pdf"
                    for report in result.ingestion_report
                )
            )
        finally:
            server.shutdown()
            server.server_close()

    def test_web_expansion_records_explicit_normalization_failure_for_malformed_pdf(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = b"%PDF-1.7 fake pdf"
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            pdf_url = f"http://127.0.0.1:{server.server_port}/broken-spec.pdf"
            custom_allowlist = WebAllowlistConfig(
                allowed_domains=["127.0.0.1"],
                domain_policies=[
                    WebDomainPolicy(
                        domain="127.0.0.1",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        seed_urls=[pdf_url],
                        allowed_path_prefixes=["/broken-spec.pdf"],
                    )
                ],
            )
            filtered_catalog = load_source_catalog(
                REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
            )
            filtered_catalog.entries = [
                entry
                for entry in filtered_catalog.entries
                if entry.source_id != "openid4vp_draft18"
            ]
            pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=custom_allowlist,
                ingestion_bundle=ingest_catalog(filtered_catalog),
            )

            result = pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )

            self.assertEqual(len(result.web_fetch_records), 1)
            self.assertFalse(result.web_fetch_records[0].metadata_complete)
            self.assertIn("Normalization failed", result.web_fetch_records[0].reason)
            self.assertFalse(
                any(
                    citation.source_origin.value == "web"
                    for entry in result.approved_entries
                    for citation in entry.citations
                )
            )
        finally:
            server.shutdown()
            server.server_close()

    def test_web_expansion_normalizes_fetched_xml_content(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = (
                    "<?xml version='1.0'?>"
                    "<document><title>OpenID4VP Official XML</title>"
                    "<section>Section 3.2 Verifier-initiated presentation request</section>"
                    "<paragraph>The Verifier sends a presentation request directly to the Wallet.</paragraph>"
                    "<paragraph>This specification does not define a dedicated Authorization Server role for the verifier-initiated presentation flow.</paragraph>"
                    "</document>"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            xml_url = f"http://127.0.0.1:{server.server_port}/openid4vp.xml"
            custom_allowlist = WebAllowlistConfig(
                allowed_domains=["127.0.0.1"],
                domain_policies=[
                    WebDomainPolicy(
                        domain="127.0.0.1",
                        source_kind=SourceKind.TECHNICAL_STANDARD,
                        source_role_level=SourceRoleLevel.HIGH,
                        jurisdiction="international",
                        seed_urls=[xml_url],
                        allowed_path_prefixes=["/openid4vp.xml"],
                    )
                ],
            )
            filtered_catalog = load_source_catalog(
                REPO_ROOT / "tests" / "fixtures" / "catalog" / "source_catalog.yaml"
            )
            filtered_catalog.entries = [
                entry
                for entry in filtered_catalog.entries
                if entry.source_id != "openid4vp_draft18"
            ]
            pipeline = ResearchPipeline(
                runtime_config=self.runtime,
                hierarchy=self.hierarchy,
                allowlist=custom_allowlist,
                ingestion_bundle=ingest_catalog(filtered_catalog),
            )

            result = pipeline.answer_question(
                "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
            )

            self.assertTrue(any(record.metadata_complete for record in result.web_fetch_records if record.allowed))
            self.assertTrue(
                any(
                    citation.source_origin.value == "web"
                    for entry in result.approved_entries
                    for citation in entry.citations
                )
            )
            self.assertTrue(
                any(
                    report.source_id.startswith("web::technical_standard::")
                    and report.normalization_format == "xml"
                    for report in result.ingestion_report
                )
            )
        finally:
            server.shutdown()
            server.server_close()

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_corpus_archive_can_drive_a_live_pipeline_slice(self) -> None:
        pipeline, real_catalog = self._build_real_corpus_pipeline()

        result = pipeline.answer_question(
            "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?"
        )

        self.assertGreaterEqual(len(real_catalog.entries), 10)
        self.assertTrue(result.ledger_entries)
        self.assertEqual(
            [entry.final_claim_state for entry in result.approved_entries],
            [ClaimState.CONFIRMED, ClaimState.OPEN],
        )
        self.assertNotIn("Interpretive:", result.rendered_answer)
        self.assertTrue(
            all(
                citation.source_role_level.value == "high"
                for entry in result.approved_entries
                for citation in entry.citations
            )
        )
        self.assertIn("OpenID", result.rendered_answer)

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_corpus_eval_gate_runs_the_full_review_suite(self) -> None:
        self._ensure_default_real_catalog()
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_all_scenarios(
                repo_root=REPO_ROOT,
                output_dir=Path(tmp_dir),
                catalog_path=REPO_ROOT / "artifacts" / "real_corpus" / "curated_catalog.json",
            )
            for scenario_id, verdict in results:
                scenario_dir = Path(tmp_dir) / scenario_id
                self.assertTrue(verdict.passed, msg=f"{scenario_id}: {verdict.checks}")
                self.assertTrue(any(check.startswith("intent_type:") for check in verdict.checks))
                self.assertTrue((scenario_dir / "retrieval_plan.json").exists())
                self.assertTrue((scenario_dir / "gap_records.json").exists())
                self.assertTrue((scenario_dir / "approved_ledger.json").exists())
                self.assertTrue((scenario_dir / "web_fetch_records.json").exists())
                self.assertTrue((scenario_dir / "final_answer.txt").exists())
                self.assertTrue((scenario_dir / "manual_review.json").exists())
                self.assertTrue((scenario_dir / "manual_review_report.md").exists())
                self.assertTrue((scenario_dir / "pinpoint_evidence.json").exists())
                self.assertTrue((scenario_dir / "answer_alignment.json").exists())
                self.assertTrue((scenario_dir / "blind_validation_report.json").exists())
                self.assertTrue((scenario_dir / "ingestion_report.json").exists())
                self.assertTrue((scenario_dir / "corpus_coverage_report.json").exists())
                if scenario_id == "primary_success_scenario":
                    self.assertIn("manual_review_accept:ok", verdict.checks)
                    self.assertTrue((scenario_dir / "provisional_grouping.json").exists())
                if scenario_id == "scenario_b_registration_certificate_mandatory":
                    self.assertIn("manual_review_accept:ok", verdict.checks)
                if scenario_id == "scenario_d_certificate_topology_anchor":
                    self.assertIn("manual_review_accept:ok", verdict.checks)
                    self.assertTrue((scenario_dir / "facet_coverage.json").exists())
                    self.assertIn("pinpoint_evidence_artifact:ok", verdict.checks)
                    self.assertIn("answer_alignment:ok", verdict.checks)
                    self.assertIn("blind_validation:ok", verdict.checks)

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_corpus_registration_information_question_uses_ebw_specific_intent(self) -> None:
        pipeline, _ = self._build_real_corpus_pipeline()

        result = pipeline.answer_question(
            "What information must a wallet-relying party provide during relying party registration?"
        )

        self.assertEqual(result.query_intent.intent_type, "relying_party_registration_information")
        self.assertIn(ClaimState.CONFIRMED, [entry.final_claim_state for entry in result.approved_entries])
        self.assertIn(
            ClaimState.INTERPRETIVE,
            [entry.final_claim_state for entry in result.approved_entries],
        )
        self.assertIn("Annex I", result.rendered_answer)
        self.assertIn("Interpretive:", result.rendered_answer)
        self.assertNotIn(
            "The answer requires EU-level regulatory support before national or project material.",
            result.rendered_answer,
        )
        self.assertTrue(
            all(citation.source_id in {"celex_32025R0848_fulltext_en", "celex_32024R1183_fulltext_en"}
                for entry in result.approved_entries
                for citation in entry.citations
            )
        )

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_corpus_certificate_question_uses_ebw_specific_intent(self) -> None:
        pipeline, _ = self._build_real_corpus_pipeline()

        result = pipeline.answer_question(
            "What is the difference between a wallet-relying party registration certificate and a wallet-relying party access certificate?"
        )

        self.assertEqual(result.query_intent.intent_type, "relying_party_certificate_requirements")
        self.assertEqual(
            [entry.final_claim_state for entry in result.approved_entries],
            [ClaimState.CONFIRMED, ClaimState.CONFIRMED, ClaimState.CONFIRMED],
        )
        self.assertIn("ANNEX IV", result.rendered_answer)
        self.assertIn("ANNEX V", result.rendered_answer)
        self.assertNotIn("Interpretive:", result.rendered_answer)

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_corpus_topology_anchor_question_uses_dedicated_intent_and_facet_artifact(self) -> None:
        pipeline, _ = self._build_real_corpus_pipeline()
        question = (
            "Gibt es abgeleitete Access bzw. Registration Certificates? Also kann eine "
            "Wallet-Relying-Party mehrere solcher Zertifikate besitzen oder gibt es nur "
            "Hauptzertifikat fuer die Ganze Organisation?"
        )

        result = pipeline.answer_question(question)

        self.assertEqual(result.query_intent.intent_type, "certificate_topology_analysis")
        self.assertIsNotNone(result.facet_coverage_report)
        self.assertTrue(result.facet_coverage_report.all_addressed())
        self.assertIn("Not explicitly defined:", result.rendered_answer)
        self.assertIn("organisation-level certificate", result.rendered_answer)
        self.assertIn("Interpretive:", result.rendered_answer)
        self.assertIn("Open:", result.rendered_answer)
        self.assertIn("Evidence (medium-rank project support):", result.rendered_answer)
        self.assertTrue(
            any(
                citation.source_id == "eudi_discussion_topic_x_rp_registration"
                for entry in result.approved_entries
                for citation in entry.citations
            )
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            write_artifact_bundle(
                Path(tmp_dir),
                result,
                verdict=ScenarioVerdict(
                    scenario_id="synthetic_topology_direct_run",
                    passed=True,
                    checks=[],
                ),
                scenario_id="synthetic_topology_direct_run",
                catalog_path=REPO_ROOT / "artifacts" / "real_corpus" / "curated_catalog.json",
                corpus_state_id="synthetic-state",
            )
            self.assertTrue((Path(tmp_dir) / "facet_coverage.json").exists())
            self.assertTrue((Path(tmp_dir) / "pinpoint_evidence.json").exists())
            self.assertTrue((Path(tmp_dir) / "answer_alignment.json").exists())
            self.assertTrue((Path(tmp_dir) / "blind_validation_report.json").exists())

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_answer_question_cli_default_catalog_writes_reviewable_artifacts(self) -> None:
        self._ensure_default_real_catalog()
        with tempfile.TemporaryDirectory() as tmp_dir:
            command = [
                sys.executable,
                str(REPO_ROOT / "scripts" / "answer_question.py"),
                "What requirements apply to the Business Wallet, and how can they be provisionally structured?",
                "--output-dir",
                tmp_dir,
            ]
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue(
                ("Confirmed:" in completed.stdout) or ("Interpretive:" in completed.stdout)
            )
            for filename in [
                "retrieval_plan.json",
                "gap_records.json",
                "web_fetch_records.json",
                "ingestion_report.json",
                "ledger_entries.json",
                "approved_ledger.json",
                "manual_review.json",
                "manual_review_report.md",
                "pinpoint_evidence.json",
                "answer_alignment.json",
                "blind_validation_report.json",
                "corpus_coverage_report.json",
                "final_answer.txt",
                "provisional_grouping.json",
            ]:
                self.assertTrue((Path(tmp_dir) / filename).exists(), msg=filename)

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_run_eval_cli_uses_separate_default_output_dirs_for_fixture_and_real_corpus(self) -> None:
        self._ensure_default_real_catalog()
        fixture_dir = REPO_ROOT / "artifacts" / "eval_runs" / "scenario_c_protocol_authorization_server"
        real_dir = (
            REPO_ROOT
            / "artifacts"
            / "eval_runs_real_corpus"
            / "scenario_c_protocol_authorization_server"
        )

        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "run_eval.py"),
                "--scenario",
                "scenario_c_protocol_authorization_server",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertTrue((fixture_dir / "verdict.json").exists())

        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "run_eval.py"),
                "--scenario",
                "scenario_c_protocol_authorization_server",
                "--catalog",
                "artifacts/real_corpus/curated_catalog.json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertTrue((real_dir / "verdict.json").exists())
        self.assertTrue((fixture_dir / "verdict.json").exists())

    def test_cli_scripts_reject_missing_catalog_path_with_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_catalog = (
                Path(tmp_dir)
                / "artifacts"
                / "real_corpus"
                / "curated_catalog.json"
            )
            commands = {
                "answer_question.py": [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "answer_question.py"),
                    "What requirements apply to the Business Wallet, and how can they be provisionally structured?",
                    "--catalog",
                    str(missing_catalog),
                ],
                "run_eval.py": [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "run_eval.py"),
                    "--scenario",
                    "scenario_c_protocol_authorization_server",
                    "--catalog",
                    str(missing_catalog),
                ],
                "run_scenario_d_closeout.py": [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "run_scenario_d_closeout.py"),
                    "--catalog",
                    str(missing_catalog),
                    "--validator-command",
                    f"{shlex.quote(sys.executable)} -c \"print('noop')\"",
                ],
            }

            for script_name, command in commands.items():
                with self.subTest(script=script_name):
                    completed = subprocess.run(
                        command,
                        cwd=REPO_ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("Catalog file not found:", completed.stderr)
                    self.assertIn(str(missing_catalog.resolve()), completed.stderr)

    def test_run_eval_cli_fails_real_corpus_coverage_gate_with_bounded_synthetic_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            catalog_path = self._build_bounded_test_catalog(tmp_root)
            scenarios_path = tmp_root / "synthetic_scenarios.json"
            scenarios_path.write_text(
                json.dumps(
                    {
                        "scenarios": [
                            {
                                "scenario_id": "synthetic_real_corpus_backstop",
                                "question": "What does the regulation say about the Business Wallet compliance record?",
                                "expectation": "Synthetic bounded real-corpus coverage gate backstop."
                            }
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            output_dir = tmp_root / "eval_runs_real_corpus"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "run_eval.py"),
                    "--scenario",
                    "synthetic_real_corpus_backstop",
                    "--catalog",
                    str(catalog_path),
                    "--scenarios-config",
                    str(scenarios_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            scenario_dir = output_dir / "synthetic_real_corpus_backstop"
            self.assertTrue(
                scenario_dir.is_dir(),
                msg=(
                    f"Expected scenario directory not found: {scenario_dir}\n"
                    f"stdout:\n{completed.stdout}\n"
                    f"stderr:\n{completed.stderr}"
                ),
            )
            verdict_path = scenario_dir / "verdict.json"
            coverage_path = scenario_dir / "corpus_coverage_report.json"
            self.assertTrue(
                verdict_path.is_file(),
                msg=(
                    f"Expected verdict artifact not found: {verdict_path}\n"
                    f"stdout:\n{completed.stdout}\n"
                    f"stderr:\n{completed.stderr}"
                ),
            )
            self.assertTrue(
                coverage_path.is_file(),
                msg=(
                    f"Expected coverage artifact not found: {coverage_path}\n"
                    f"stdout:\n{completed.stdout}\n"
                    f"stderr:\n{completed.stderr}"
                ),
            )
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            self.assertFalse(verdict["passed"])
            self.assertIn("corpus_coverage_gate:fail", verdict["checks"])
            self.assertFalse(coverage["passed"])
