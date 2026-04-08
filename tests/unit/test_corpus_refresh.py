from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from eubw_researcher.config import load_archive_corpus_config
from eubw_researcher.corpus.refresh import refresh_archive_sources
from eubw_researcher.models import RuntimeConfig


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
                report = refresh_archive_sources(
                    config,
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
                report = refresh_archive_sources(
                    config,
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

    def test_refresh_attempts_known_canonical_url_even_without_allowlist_policy(self) -> None:
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
                self._runtime_config(),
                stage_root=tmp_root / "stage",
                config_path=config_path,
            )

            self.assertEqual(report.failed_sources, 1)
            self.assertEqual(report.results[0].status, "fetch_failed")

    def test_refresh_rejects_unsupported_canonical_url_scheme(self) -> None:
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
                            "source_url": "file:///tmp/not-allowed.html",
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
                self._runtime_config(),
                stage_root=tmp_root / "stage",
                config_path=config_path,
            )

            self.assertEqual(report.failed_sources, 1)
            self.assertEqual(report.results[0].status, "fetch_failed")
            self.assertIn("Unsupported canonical URL scheme", report.results[0].reason)

    def test_refresh_skips_invalid_local_path_outside_archive_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            archive_root.mkdir(parents=True, exist_ok=True)
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "ARCHIVE-1",
                            "title": "Archive Sample",
                            "local_path": "../escape/outside.html",
                            "source_url": "https://example.test/source.html",
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
                self._runtime_config(),
                stage_root=tmp_root / "stage",
                config_path=config_path,
            )

            self.assertEqual(report.results[0].status, "skipped_invalid_local_path")

    def test_refresh_skips_local_path_that_is_not_a_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            local_dir = archive_root / "reference_web" / "sample.html"
            local_dir.mkdir(parents=True, exist_ok=True)
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "ARCHIVE-1",
                            "title": "Archive Sample",
                            "local_path": "sources/reference_web/sample.html",
                            "source_url": "https://example.test/source.html",
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
                self._runtime_config(),
                stage_root=tmp_root / "stage",
                config_path=config_path,
            )

            self.assertEqual(report.results[0].status, "skipped_invalid_local_path")
            self.assertIn("not a regular file", report.results[0].reason)

    def test_refresh_304_fallback_fetches_when_local_digest_no_longer_matches_accepted_digest(self) -> None:
        current_body = b"<html><body><h1>Current</h1></body></html>"
        call_count = {"value": 0}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                call_count["value"] += 1
                if self.headers.get("If-None-Match") == "\"kept-etag\"":
                    self.send_response(304)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("ETag", "\"kept-etag\"")
                self.end_headers()
                self.wfile.write(current_body)

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
                local_path.write_text("<html><body>tampered</body></html>", encoding="utf-8")
                catalog_path = archive_root / "catalog.json"
                catalog_path.write_text(
                    json.dumps(
                        [
                            {
                                "source_id": "ARCHIVE-1",
                                "title": "Archive Sample",
                                "local_path": "sources/reference_web/sample.html",
                                "source_url": f"http://127.0.0.1:{server.server_port}/sample.html",
                                "sha256": "previous-accepted-digest",
                                "refresh_etag": "\"kept-etag\"",
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
                    self._runtime_config(),
                    stage_root=tmp_root / "stage",
                    config_path=config_path,
                )

                self.assertEqual(call_count["value"], 2)
                self.assertEqual(report.results[0].status, "staged_update")
                self.assertEqual(Path(report.results[0].stage_path).read_bytes(), current_body)
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_apply_updates_refresh_metadata_for_current_source(self) -> None:
        same_body = b"<html><body><h1>Same</h1></body></html>"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("ETag", "\"current-etag\"")
                self.send_header("Last-Modified", "Fri, 03 Apr 2026 11:00:00 GMT")
                self.end_headers()
                self.wfile.write(same_body)

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
                local_path.write_bytes(same_body)
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
                report = refresh_archive_sources(
                    config,
                    self._runtime_config(),
                    stage_root=tmp_root / "stage",
                    config_path=config_path,
                    apply_updates=True,
                )

                self.assertEqual(report.results[0].status, "current")
                updated_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                self.assertEqual(updated_catalog[0]["refresh_etag"], "\"current-etag\"")
                self.assertEqual(updated_catalog[0]["refresh_last_modified"], "Fri, 03 Apr 2026 11:00:00 GMT")
                self.assertTrue(updated_catalog[0]["refresh_checked_at"])
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_stages_successor_candidate_without_applying_even_with_apply_flag(self) -> None:
        current_body = b"<html><body><h1>Current</h1></body></html>"
        successor_body = b"<html><body><h1>Final successor</h1></body></html>"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/current.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("ETag", "\"current-etag\"")
                    self.end_headers()
                    self.wfile.write(current_body)
                    return
                if self.path == "/successor.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(successor_body)
                    return
                self.send_response(404)
                self.end_headers()

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
                local_path.write_bytes(current_body)
                catalog_path = archive_root / "catalog.json"
                catalog_path.write_text(
                    json.dumps(
                        [
                            {
                                "source_id": "ARCHIVE-1",
                                "title": "Archive Sample",
                                "local_path": "sources/reference_web/sample.html",
                                "source_url": f"http://127.0.0.1:{server.server_port}/current.html",
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
                                    "publication_status": "draft",
                                    "document_status": "draft",
                                    "publication_date": None,
                                    "successor_candidate_urls": [
                                        f"http://127.0.0.1:{server.server_port}/successor.html"
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                config = load_archive_corpus_config(config_path)
                report = refresh_archive_sources(
                    config,
                    self._runtime_config(),
                    stage_root=tmp_root / "stage",
                    config_path=config_path,
                    apply_updates=True,
                )

                result = report.results[0]
                self.assertEqual(result.status, "staged_successor")
                self.assertFalse(result.applied)
                self.assertEqual(
                    result.selected_successor_candidate_url,
                    f"http://127.0.0.1:{server.server_port}/successor.html",
                )
                self.assertEqual(result.matching_successor_candidate_urls, [result.selected_successor_candidate_url])
                self.assertEqual(Path(result.stage_path).read_bytes(), successor_body)
                self.assertEqual(local_path.read_bytes(), current_body)
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_marks_ambiguous_successor_candidates(self) -> None:
        current_body = b"<html><body><h1>Current</h1></body></html>"
        successor_a = b"<html><body><h1>Successor A</h1></body></html>"
        successor_b = b"<html><body><h1>Successor B</h1></body></html>"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/current.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(current_body)
                    return
                if self.path == "/successor-a.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(successor_a)
                    return
                if self.path == "/successor-b.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(successor_b)
                    return
                self.send_response(404)
                self.end_headers()

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
                local_path.write_bytes(current_body)
                catalog_path = archive_root / "catalog.json"
                catalog_path.write_text(
                    json.dumps(
                        [
                            {
                                "source_id": "ARCHIVE-1",
                                "title": "Archive Sample",
                                "local_path": "sources/reference_web/sample.html",
                                "source_url": f"http://127.0.0.1:{server.server_port}/current.html",
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
                                    "publication_status": "draft",
                                    "document_status": "draft",
                                    "publication_date": None,
                                    "successor_candidate_urls": [
                                        f"http://127.0.0.1:{server.server_port}/successor-a.html",
                                        f"http://127.0.0.1:{server.server_port}/successor-b.html"
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                config = load_archive_corpus_config(config_path)
                report = refresh_archive_sources(
                    config,
                    self._runtime_config(),
                    stage_root=tmp_root / "stage",
                    config_path=config_path,
                )

                result = report.results[0]
                self.assertEqual(result.status, "ambiguous_successor_candidates")
                self.assertEqual(
                    result.matching_successor_candidate_urls,
                    [
                        f"http://127.0.0.1:{server.server_port}/successor-a.html",
                        f"http://127.0.0.1:{server.server_port}/successor-b.html",
                    ],
                )
                self.assertIsNone(result.selected_successor_candidate_url)
                self.assertIsNone(result.stage_path)
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_cli_returns_nonzero_when_fetches_fail(self) -> None:
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
                            "source_url": "http://127.0.0.1:1/unreachable.html",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            config_path = tmp_root / "selection.json"
            config_path.write_text(
                json.dumps(
                    {
                        "archive_root": str(archive_root),
                        "archive_catalog": str(catalog_path),
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
            runtime_path = tmp_root / "runtime.json"
            runtime_path.write_text(
                json.dumps(
                    {
                        "logging": {"level": "INFO"},
                        "retrieval": {
                            "top_k": 5,
                            "lexical_weight": 1.0,
                            "semantic_weight": 1.0,
                            "min_combined_score": 0.0,
                            "semantic_expansions": {},
                            "web_timeout_seconds": 1,
                            "web_discovery_max_depth": 1,
                            "web_discovery_max_pages": 5,
                            "web_discovery_max_candidates_per_kind": 5,
                            "web_max_admitted_per_domain": 5,
                            "web_max_admitted_per_run": 10,
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    "scripts/refresh_real_corpus.py",
                    "--config",
                    str(config_path),
                    "--runtime-config",
                    str(runtime_path),
                    "--stage-dir",
                    str(tmp_root / "stage"),
                    "--report",
                    str(tmp_root / "refresh_report.json"),
                    "--report-markdown",
                    str(tmp_root / "refresh_report.md"),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("failed source fetch", result.stderr)


if __name__ == "__main__":
    unittest.main()
