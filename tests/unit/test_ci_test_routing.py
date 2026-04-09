from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from eubw_researcher.ci_test_routing import classify_changed_files, changed_files_between


class CiTestRoutingTests(unittest.TestCase):
    def test_docs_only_changes_do_not_request_test_jobs(self) -> None:
        decision = classify_changed_files(
            [
                "README.md",
                "docs/architecture/options/option-a/AGENT_RUNTIME_GUIDE.md",
            ]
        )

        self.assertFalse(decision.run_ci)
        self.assertFalse(decision.run_integration)
        self.assertFalse(decision.run_closeout)

    def test_pyproject_changes_request_all_runtime_suites(self) -> None:
        decision = classify_changed_files(["pyproject.toml"])

        self.assertTrue(decision.run_ci)
        self.assertTrue(decision.run_integration)
        self.assertTrue(decision.run_closeout)

    def test_workflow_only_changes_keep_heavy_suites_off(self) -> None:
        decision = classify_changed_files([".github/workflows/tests.yml"])

        self.assertTrue(decision.run_ci)
        self.assertFalse(decision.run_integration)
        self.assertFalse(decision.run_closeout)

    def test_shared_closeout_dependencies_route_closeout_suite(self) -> None:
        decision = classify_changed_files(
            [
                "src/eubw_researcher/models/__init__.py",
                "src/eubw_researcher/trust.py",
            ]
        )

        self.assertTrue(decision.run_ci)
        self.assertTrue(decision.run_integration)
        self.assertTrue(decision.run_closeout)

    def test_transitive_closeout_runtime_packages_route_closeout_suite(self) -> None:
        decision = classify_changed_files(
            [
                "src/eubw_researcher/answering/composer.py",
                "src/eubw_researcher/config/loader.py",
                "src/eubw_researcher/evidence/ledger.py",
                "src/eubw_researcher/retrieval/planner.py",
                "src/eubw_researcher/web/fetch.py",
            ]
        )

        self.assertTrue(decision.run_ci)
        self.assertTrue(decision.run_integration)
        self.assertTrue(decision.run_closeout)

    def test_integration_fixtures_route_integration_suite(self) -> None:
        decision = classify_changed_files(["tests/fixtures/catalog/source_catalog.yaml"])

        self.assertTrue(decision.run_ci)
        self.assertTrue(decision.run_integration)
        self.assertFalse(decision.run_closeout)

    def test_changed_files_between_uses_merge_base_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Codex Test"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "codex@example.com"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )

            tracked = repo_root / "tracked.txt"
            tracked.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo_root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "base"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "branch", "feature"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )

            tracked.write_text("main update\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "main update"], cwd=repo_root, check=True, capture_output=True)
            main_sha = (
                subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_root,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
            )

            subprocess.run(["git", "checkout", "feature"], cwd=repo_root, check=True, capture_output=True)
            feature_file = repo_root / "feature.txt"
            feature_file.write_text("feature\n", encoding="utf-8")
            subprocess.run(["git", "add", "feature.txt"], cwd=repo_root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "feature change"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            feature_sha = (
                subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_root,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
            )

            changed_files = changed_files_between(main_sha, feature_sha, repo_root=repo_root)

        self.assertEqual(changed_files, ["feature.txt"])
