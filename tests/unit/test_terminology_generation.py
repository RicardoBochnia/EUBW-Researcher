from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from eubw_researcher.config import load_terminology_config
from eubw_researcher.config.terminology_generation import (
    build_generated_terminology,
    render_generated_terminology,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _mapping_by_canonical(
    mappings: list[dict[str, Any]],
    canonical_term: str,
) -> dict[str, Any]:
    return next(mapping for mapping in mappings if mapping["canonical_term"] == canonical_term)


def _alias_terms(mapping: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for alias in mapping["aliases"]:
        if isinstance(alias, dict):
            terms.append(alias["term"])
        else:
            terms.append(alias)
    return terms


class TerminologyGenerationTests(unittest.TestCase):
    def _write_archive_catalog(
        self,
        root: Path,
        documents: dict[str, str],
    ) -> Path:
        archive_root = root / "archive"
        sources_root = archive_root / "sources"
        sources_root.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, str]] = []
        for index, (filename, text) in enumerate(documents.items(), start=1):
            document_path = sources_root / filename
            document_path.write_text(text, encoding="utf-8")
            rows.append(
                {
                    "source_id": f"archive_{index}",
                    "local_path": f"sources/{filename}",
                }
            )

        catalog_path = archive_root / "catalog.json"
        catalog_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return catalog_path

    def _rich_documents(self) -> dict[str, str]:
        return {
            "doc_a.md": (
                "# Terminology A\n\n"
                "The European Business Wallet (EBW) profile describes the Business Wallet "
                "and a wallet-relying party registration process. "
                "A wallet-relying party access certificate (WRPAC) may be paired with a "
                "wallet-relying party registration certificate (WRPRC). "
                "In some onboarding notes, a wallet-relying party also refers to an RPAC. "
                "The provider of person identification data (PID provider) validates person "
                "identification data (PID). "
                "The wallet also processes a qualified electronic attestation of attributes "
                "(QEAA).\n"
            ),
            "doc_b.md": (
                "# Terminology B\n\n"
                "A European Business Wallet (EBW) can exchange information with a wallet relying party. "
                "That wallet relying party may hold an access certificate and a registration "
                "certificate, a WRPAC, a WRPRC, and in some notes an RPAC. "
                "The PID provider remains a provider of PID and a provider of person identification "
                "data in the wallet issuer flow. "
                "Person identification data (PID) and qualified electronic attestation of "
                "attributes (QEAA) are processed in the EUBW context.\n"
            ),
        }

    def test_build_generated_terminology_activates_expected_alias_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            catalog_path = self._write_archive_catalog(tmp_root, self._rich_documents())

            config_payload, report_payload = build_generated_terminology(
                catalog_path,
                archive_catalog_display_path="fixtures/archive/catalog.json",
            )

            self.assertTrue(config_payload["generator_owned"])
            self.assertEqual(config_payload["policy_version"], "corpus_terminology.v1")
            self.assertEqual(
                config_payload["archive_catalog_path"],
                "fixtures/archive/catalog.json",
            )

            business_wallet = _mapping_by_canonical(
                config_payload["mappings"],
                "business wallet",
            )
            self.assertEqual(
                _alias_terms(business_wallet),
                ["eu business wallet", "eubw", "European Business Wallet", "EBW"],
            )
            self.assertNotIn("EU Business Wallet", _alias_terms(business_wallet))

            access_certificate = _mapping_by_canonical(
                config_payload["mappings"],
                "access certificate",
            )
            self.assertIn("access cert", _alias_terms(access_certificate))
            self.assertIn("WRPAC", _alias_terms(access_certificate))
            self.assertIn("RPAC", _alias_terms(access_certificate))
            rpac_alias = next(
                alias
                for alias in access_certificate["aliases"]
                if isinstance(alias, dict) and alias["term"] == "RPAC"
            )
            self.assertIn("wallet-relying party", rpac_alias["context_aliases"])
            self.assertIn("relying party", rpac_alias["context_aliases"])
            self.assertNotIn("access", rpac_alias["context_aliases"])

            pid_mapping = _mapping_by_canonical(
                config_payload["mappings"],
                "person identification data",
            )
            self.assertEqual(len(pid_mapping["aliases"]), 1)
            self.assertEqual(pid_mapping["aliases"][0]["term"], "PID")

            qeaa_mapping = _mapping_by_canonical(
                config_payload["mappings"],
                "qualified electronic attestation of attributes",
            )
            self.assertEqual(qeaa_mapping["aliases"][0]["term"], "QEAA")

            rendered = render_generated_terminology(config_payload)
            terminology_path = tmp_root / "terminology.json"
            terminology_path.write_text(rendered, encoding="utf-8")
            terminology = load_terminology_config(terminology_path)
            self.assertTrue(terminology.generator_owned)
            self.assertEqual(
                [mapping.canonical_term for mapping in terminology.mappings],
                [mapping["canonical_term"] for mapping in config_payload["mappings"]],
            )

            pid_report = next(
                family
                for family in report_payload["families"]
                if family["canonical_term"] == "person identification data"
            )
            self.assertTrue(pid_report["included_in_config"])
            self.assertTrue(
                any(
                    candidate["term"] == "PID" and candidate["activated"]
                    for candidate in pid_report["candidate_aliases"]
                )
            )

    def test_build_generated_terminology_skips_unbacked_acronym_only_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            catalog_path = self._write_archive_catalog(
                tmp_root,
                {
                    "doc.md": (
                        "# Sparse corpus\n\n"
                        "This note only mentions the Business Wallet and a wallet relying party.\n"
                    )
                },
            )

            config_payload, report_payload = build_generated_terminology(catalog_path)

            self.assertNotIn(
                "person identification data",
                [mapping["canonical_term"] for mapping in config_payload["mappings"]],
            )
            self.assertNotIn(
                "qualified electronic attestation of attributes",
                [mapping["canonical_term"] for mapping in config_payload["mappings"]],
            )
            pid_report = next(
                family
                for family in report_payload["families"]
                if family["canonical_term"] == "person identification data"
            )
            self.assertFalse(pid_report["included_in_config"])

    def test_build_generated_terminology_rejects_non_list_archive_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            archive_root.mkdir(parents=True, exist_ok=True)
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps({"source_id": "invalid"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must contain a JSON list"):
                build_generated_terminology(catalog_path)

    def test_build_generated_terminology_reports_invalid_archive_rows_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            sources_root = archive_root / "sources"
            sources_root.mkdir(parents=True, exist_ok=True)
            (sources_root / "doc.md").write_text(
                "# Terminology\n\nThe Business Wallet mentions a wallet relying party.\n",
                encoding="utf-8",
            )
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        "not-an-object",
                        {"source_id": "missing_path"},
                        {"local_path": "sources/doc.md"},
                        {"source_id": "valid", "local_path": "sources/doc.md"},
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )

            config_payload, report_payload = build_generated_terminology(catalog_path)

            self.assertTrue(config_payload["mappings"])
            skipped_reasons = [item["reason"] for item in report_payload["archive_skipped"]]
            self.assertTrue(
                any("expected object" in reason for reason in skipped_reasons)
            )
            self.assertTrue(
                any(
                    "missing source_id or local_path in archive catalog row" == reason
                    for reason in skipped_reasons
                )
            )

    def test_duplicate_catalog_rows_for_same_file_do_not_fake_multi_source_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_root = tmp_root / "archive"
            sources_root = archive_root / "sources"
            sources_root.mkdir(parents=True, exist_ok=True)
            document_path = sources_root / "business_wallet_note.md"
            document_path.write_text(
                (
                    "# Business Wallet Note\n\n"
                    "The European Business Wallet (EBW) profile describes the Business Wallet.\n"
                ),
                encoding="utf-8",
            )
            catalog_path = archive_root / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "archive_a",
                            "local_path": "sources/business_wallet_note.md",
                        },
                        {
                            "source_id": "archive_b",
                            "local_path": "sources/business_wallet_note.md",
                        },
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )

            config_payload, report_payload = build_generated_terminology(catalog_path)

            business_wallet = _mapping_by_canonical(
                config_payload["mappings"],
                "business wallet",
            )
            self.assertEqual(
                _alias_terms(business_wallet),
                ["eu business wallet", "eubw"],
            )

            business_wallet_report = next(
                family
                for family in report_payload["families"]
                if family["canonical_term"] == "business wallet"
            )
            ebw_candidate = next(
                candidate
                for candidate in business_wallet_report["candidate_aliases"]
                if candidate["term"] == "EBW"
            )
            long_form_candidate = next(
                candidate
                for candidate in business_wallet_report["candidate_aliases"]
                if candidate["term"] == "European Business Wallet"
            )
            self.assertEqual(ebw_candidate["archive_source_count"], 1)
            self.assertFalse(ebw_candidate["activated"])
            self.assertEqual(long_form_candidate["archive_source_count"], 1)
            self.assertFalse(long_form_candidate["activated"])
            self.assertEqual(report_payload["archive_source_count"], 1)
            self.assertEqual(len(report_payload["archive_deduplicated"]), 1)
            self.assertEqual(
                report_payload["archive_deduplicated"][0]["source_id"],
                "archive_b",
            )

    def test_update_terminology_script_check_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_catalog_path = self._write_archive_catalog(tmp_root, self._rich_documents())
            output_path = tmp_root / "terminology.json"
            report_path = tmp_root / "terminology_report.json"

            generate_completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "update_terminology_from_corpus.py"),
                    "--archive-catalog",
                    str(archive_catalog_path),
                    "--output",
                    str(output_path),
                    "--report",
                    str(report_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(str(output_path), generate_completed.stdout)
            self.assertTrue(output_path.exists())
            self.assertTrue(report_path.exists())
            self.assertTrue(load_terminology_config(output_path).generator_owned)

            check_completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "update_terminology_from_corpus.py"),
                    "--archive-catalog",
                    str(archive_catalog_path),
                    "--output",
                    str(output_path),
                    "--report",
                    str(report_path),
                    "--check",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(str(output_path), check_completed.stdout)
            self.assertTrue(report_path.exists())
            initial_report = report_path.read_text(encoding="utf-8")

            output_path.write_text(
                output_path.read_text(encoding="utf-8").replace(
                    '"policy_version": "corpus_terminology.v1"',
                    '"policy_version": "stale_policy"',
                    1,
                ),
                encoding="utf-8",
            )
            stale_check = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "update_terminology_from_corpus.py"),
                    "--archive-catalog",
                    str(archive_catalog_path),
                    "--output",
                    str(output_path),
                    "--report",
                    str(report_path),
                    "--check",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(stale_check.returncode, 1)
            self.assertIn("out of date", stale_check.stderr)
            self.assertEqual(report_path.read_text(encoding="utf-8"), initial_report)

    def test_update_terminology_script_check_does_not_create_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_catalog_path = self._write_archive_catalog(tmp_root, self._rich_documents())
            output_path = tmp_root / "terminology.json"
            report_path = tmp_root / "nested" / "terminology_report.json"

            generate_completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "update_terminology_from_corpus.py"),
                    "--archive-catalog",
                    str(archive_catalog_path),
                    "--output",
                    str(output_path),
                    "--report",
                    str(report_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(str(output_path), generate_completed.stdout)
            report_path.unlink()
            report_path.parent.rmdir()

            check_completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "update_terminology_from_corpus.py"),
                    "--archive-catalog",
                    str(archive_catalog_path),
                    "--output",
                    str(output_path),
                    "--report",
                    str(report_path),
                    "--check",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(str(output_path), check_completed.stdout)
            self.assertFalse(report_path.exists())
            self.assertFalse(report_path.parent.exists())

    @unittest.skipUnless(
        (REPO_ROOT / "artifacts" / "real_corpus" / "archive").exists(),
        "Real corpus archive is not available in this workspace.",
    )
    def test_real_corpus_generator_check_keeps_committed_config_current(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "update_terminology_from_corpus.py"),
                "--check",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        terminology = load_terminology_config(REPO_ROOT / "configs" / "terminology.yaml")
        mapping_by_name = {
            mapping.canonical_term: mapping
            for mapping in terminology.mappings
        }
        self.assertIn("business wallet", mapping_by_name)
        self.assertIn("person identification data", mapping_by_name)
        self.assertIn("qualified electronic attestation of attributes", mapping_by_name)
        self.assertIn("access certificate", mapping_by_name)
        self.assertIn("registration certificate", mapping_by_name)
        self.assertIn("EBW", mapping_by_name["business wallet"].aliases)
        self.assertIn("WRPAC", mapping_by_name["access certificate"].aliases)
        self.assertIn("WRPRC", mapping_by_name["registration certificate"].aliases)


if __name__ == "__main__":
    unittest.main()
