from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class AgentRuntimeIntegrationTests(unittest.TestCase):
    def test_agent_answer_wrapper_writes_bundle_and_returns_json_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "agent_answer_question.py"),
                    "What is the difference between OpenID4VCI and OpenID4VP regarding the authorization server?",
                    "--catalog",
                    "tests/fixtures/catalog/source_catalog.yaml",
                    "--output-dir",
                    tmp_dir,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["runtime_contract_version"], "option_a_agent_runtime_v1")
            self.assertEqual(payload["mode"], "answer_question")
            self.assertEqual(Path(payload["output_dir"]), Path(tmp_dir).resolve())
            self.assertTrue((Path(tmp_dir) / "final_answer.txt").exists())
            self.assertIn("authorization server", payload["rendered_answer"].lower())

    def test_agent_eval_wrapper_returns_json_summary_and_writes_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "agent_run_eval.py"),
                    "--scenario",
                    "scenario_c_protocol_authorization_server",
                    "--output-dir",
                    tmp_dir,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["runtime_contract_version"], "option_a_agent_runtime_v1")
            self.assertEqual(payload["mode"], "run_named_evaluation")
            self.assertEqual(len(payload["results"]), 1)
            self.assertEqual(
                payload["results"][0]["scenario_id"],
                "scenario_c_protocol_authorization_server",
            )
            self.assertTrue(payload["results"][0]["passed"])
            self.assertTrue(
                (Path(tmp_dir) / "scenario_c_protocol_authorization_server" / "verdict.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
