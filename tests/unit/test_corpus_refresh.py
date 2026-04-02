from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from eubw_researcher.config import load_archive_corpus_config
from eubw_researcher.corpus.refresh import refresh_archive_sources
from eubw_researcher.models import RuntimeConfig, WebAllowlistConfig, WebDomainPolicy


class CorpusRefreshTests(unittest.TestCase):
    def _runtime_config(self) -> RuntimeConfig:
        return RuntimeConfig(
            logging_level="INFO",
            retrieval_top_k=5,
            lexical_weight=1.0,
            semantic_weight=1.0,
            min_combined_score=0.0,
            semantic_expansions={},
            web_timeout_seconds=5,
            web_discovery_max_depth=1,
            web_discovery_max_pages=5,
            web_discovery_max_candidates_per_kind=5,
            web_max_admitted_per_domain=5,
            web_max_admitted_per_run=10,
        )

    def test_refresh_stages_changed_remote_source(self) -> None:
        changed_body = b"<html><body><h1>Updated</h1><p>remote text</p></body></html>"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("ETag", "\"updated-etag\"")
                self.end_headers()
                self.wfile.write(changed_body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_root = Path(tmp_dir)
                archive_root = tmp_root / "archive"
                local_path = archive_root / "reference_web" / "sample.html"
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text("<html><body>old</body></html>", encoding="utf-8")
                catalog_path = archive_root / "catalog.json"
                catalog_path.write_text(
                    json.dumps(
                        [
                            {
                                "source_id": "ARCHIVE-1",
                                "title": "Archive Sample",
                                "local_path": "sources/reference_web/sample.html",
                                "source_url": f"http://127.0.0.1:{server.server_port}/sample.html",
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                config_path = tmp_root / "selection.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "archive_root": "archive",
                            "archive_catalog": "archive/catalog.json",
                            "sources": [
                                {
                                    "archive_source_id": "ARCHIVE-1",
                                    "source_id": "sample_regulation",
                                    "title": "Sample Regulation",
                                    "source_kind": "regulation",
                                    "source_role_level": "high",
                                    "jurisdiction": "EU",
                                    "publication_status": "official_journal",
                                    "publication_date": None,
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                config = load_archive_corpus_config(config_path)
                allowlist = WebAllowlistConfig(
                    allowed_domains=["127.0.0.1"],
                    domain_policies=[
                        WebDomainPolicy(
                            domain="127.0.0.1",
                            source_kind=config.sources[0].source_kind,
                            source_role_level=config.sources[0].source_role_level,
                            jurisdiction="EU",
                            allowed_path_prefixes=["/"],
                        )
                    ],
                )

                report = refresh_archive_sources(
                    config,
                    allowlist,
                    self._runtime_config(),
                    stage_root=tmp_root / "stage",
                    config_path=config_path,
                )

                self.assertEqual(report.changed_sources, 1)
                result = report.results[0]
                self.assertEqual(result.status, "staged_update")
                self.assertTrue(result.stage_path)
                self.assertEqual(Path(result.stage_path).read_bytes(), changed_body)
                self.assertEqual(local_path.read_text(encoding="utf-8"), "<html><body>old</body></html>")
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_apply_updates_archive_and_catalog_metadata(self) -> None:
        new_body = b"<html><body><h1>Applied</h1></body></html>"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("ETag", "\"applied-etag\"")
                self.send_header("Last-Modified", "Fri, 03 Apr 2026 10:00:00 GMT")
                self.end_headers()
                self.wfile.write(new_body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_root = Path(tmp_dir)
                archive_root = tmp_root / "archive"
                local_path = archive_root / "reference_web" / "sample.html"
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text("<html><body>old</body></html>", encoding="utf-8")
                catalog_path = archive_root / "catalog.json"
                catalog_path.write_text(
                    json.dumps(
                        [
                            {
                                "source_id": "ARCHIVE-1",
                                "title": "Archive Sample",
                                "local_path": "sources/reference_web/sample.html",
                                "source_url": f"http://127.0.0.1:{server.server_port}/sample.html",
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                config_path = tmp_root / "selection.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "archive_root": "archive",
                            "archive_catalog": "archive/catalog.json",
                            "sources": [
                                {
                                    "archive_source_id": "ARCHIVE-1",
                                    "source_id": "sample_regulation",
                                    "title": "Sample Regulation",
                                    "source_kind": "regulation",
                                    "source_role_level": "high",
                                    "jurisdiction": "EU",
                                    "publication_status": "official_journal",
                                    "publication_date": None,
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                config = load_archive_corpus_config(config_path)
                allowlist = WebAllowlistConfig(
                    allowed_domains=["127.0.0.1"],
                    domain_policies=[
                        WebDomainPolicy(
                            domain="127.0.0.1",
                            source_kind=config.sources[0].source_kind,
                            source_role_level=config.sources[0].source_role_level,
                            jurisdiction="EU",
                            allowed_path_prefixes=["/"],
                        )
                    ],
                )

                report = refresh_archive_sources(
                    config,
                    allowlist,
                    self._runtime_config(),
                    stage_root=tmp_root / "stage",
                    config_path=config_path,
                    apply_updates=True,
                )

                self.assertEqual(report.applied_sources, 1)
                result = report.results[0]
                self.assertEqual(result.status, "applied_update")
                self.assertEqual(local_path.read_bytes(), new_body)
                updated_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                self.assertEqual(updated_catalog[0]["refresh_etag"], "\"applied-etag\"")
                self.assertEqual(updated_catalog[0]["refresh_last_modified"], "Fri, 03 Apr 2026 10:00:00 GMT")
                self.assertTrue(updated_catalog[0]["sha256"])
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_skips_non_allowlisted_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            local_path = archive_root / "reference_web" / "sample.html"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text("<html><body>old</body></html>", encoding="utf-8")
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "ARCHIVE-1",
                            "title": "Archive Sample",
                            "local_path": "sources/reference_web/sample.html",
                            "source_url": "https://vendor.example/sample.html",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            config_path = tmp_root / "selection.json"
            config_path.write_text(
                json.dumps(
                    {
                        "archive_root": "archive",
                        "archive_catalog": "archive/catalog.json",
                        "sources": [
                            {
                                "archive_source_id": "ARCHIVE-1",
                                "source_id": "sample_regulation",
                                "title": "Sample Regulation",
                                "source_kind": "regulation",
                                "source_role_level": "high",
                                "jurisdiction": "EU",
                                "publication_status": "official_journal",
                                "publication_date": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            config = load_archive_corpus_config(config_path)

            report = refresh_archive_sources(
                config,
                WebAllowlistConfig(allowed_domains=["127.0.0.1"]),
                self._runtime_config(),
                stage_root=tmp_root / "stage",
                config_path=config_path,
            )

            self.assertEqual(report.skipped_sources, 1)
            self.assertEqual(report.results[0].status, "skipped_not_allowlisted")


if __name__ == "__main__":
    unittest.main()
