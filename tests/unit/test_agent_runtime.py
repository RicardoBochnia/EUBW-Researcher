from __future__ import annotations

import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.agent_runtime import (
    AGENT_RUNTIME_CONTRACT_VERSION,
    AgentRuntimeFacade,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class AgentRuntimeFacadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = SimpleNamespace(
            rendered_answer="Confirmed:\nSynthetic answer.",
            corpus_coverage_report=None,
        )
        self.pipeline = SimpleNamespace(answer_question=lambda question: self.result)

    def _runtime_patches(self, *, write_bundle_side_effect=None):
        stack = ExitStack()
        stack.enter_context(
            patch(
                "eubw_researcher.agent_runtime.load_runtime_config",
                return_value=object(),
            )
        )
        stack.enter_context(
            patch(
                "eubw_researcher.agent_runtime.load_source_hierarchy",
                return_value=object(),
            )
        )
        stack.enter_context(
            patch(
                "eubw_researcher.agent_runtime.load_web_allowlist",
                return_value=object(),
            )
        )
        stack.enter_context(
            patch(
                "eubw_researcher.agent_runtime.load_or_build_ingestion_bundle",
                return_value=(None, object(), None, "synthetic-state"),
            )
        )
        stack.enter_context(
            patch(
                "eubw_researcher.agent_runtime.ResearchPipeline",
                return_value=self.pipeline,
            )
        )
        write_bundle = stack.enter_context(
            patch(
                "eubw_researcher.agent_runtime.write_artifact_bundle",
                side_effect=write_bundle_side_effect,
            )
        )
        return stack, write_bundle

    def test_answer_question_returns_stable_contract_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            stack, write_bundle = self._runtime_patches()
            with stack:
                runtime = AgentRuntimeFacade(REPO_ROOT)
                response = runtime.answer_question(
                    "Synthetic question?",
                    catalog_path="tests/fixtures/catalog/source_catalog.yaml",
                    output_dir=tmp_dir,
                )

        self.assertEqual(response.runtime_contract_version, AGENT_RUNTIME_CONTRACT_VERSION)
        self.assertEqual(response.mode, "answer_question")
        self.assertEqual(response.question, "Synthetic question?")
        self.assertEqual(response.corpus_state_id, "synthetic-state")
        self.assertEqual(response.output_dir, str(Path(tmp_dir).resolve()))
        self.assertEqual(response.final_answer_path, str(Path(tmp_dir).resolve() / "final_answer.txt"))
        self.assertEqual(response.rendered_answer, "Confirmed:\nSynthetic answer.")
        write_bundle.assert_called_once()

    def test_write_reviewable_artifact_bundle_lists_written_artifacts(self) -> None:
        def _write_bundle(output_dir, *_args, **_kwargs) -> None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "final_answer.txt").write_text("Synthetic answer\n", encoding="utf-8")
            (output_dir / "approved_ledger.json").write_text("[]\n", encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp_dir:
            stack, _write_bundle_mock = self._runtime_patches(
                write_bundle_side_effect=_write_bundle
            )
            with stack:
                runtime = AgentRuntimeFacade(REPO_ROOT)
                response = runtime.write_reviewable_artifact_bundle(
                    "Synthetic question?",
                    catalog_path="tests/fixtures/catalog/source_catalog.yaml",
                    output_dir=tmp_dir,
                )

        self.assertEqual(response.runtime_contract_version, AGENT_RUNTIME_CONTRACT_VERSION)
        self.assertEqual(response.mode, "write_reviewable_artifact_bundle")
        self.assertEqual(response.output_dir, str(Path(tmp_dir).resolve()))
        self.assertEqual(response.final_answer_path, str(Path(tmp_dir).resolve() / "final_answer.txt"))
        self.assertEqual(response.artifacts, ["approved_ledger.json", "final_answer.txt"])


if __name__ == "__main__":
    unittest.main()
