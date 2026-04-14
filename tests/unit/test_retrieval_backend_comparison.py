from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "run_retrieval_backend_comparison.py"


def _load_script_module():
    original_sys_path = list(sys.path)
    try:
        sys.path.insert(0, str(MODULE_PATH.parent))
        module_spec = importlib.util.spec_from_file_location(
            "run_retrieval_backend_comparison",
            MODULE_PATH,
        )
        assert module_spec is not None
        assert module_spec.loader is not None
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = original_sys_path


retrieval_backend_comparison = _load_script_module()


class RetrievalBackendComparisonTests(unittest.TestCase):
    def test_evaluate_runtime_marks_missing_target_as_miss(self) -> None:
        with patch(
            "eubw_researcher.retrieval.analyze_query",
            return_value=SimpleNamespace(intent_type="synthetic_intent"),
        ), patch(
            "eubw_researcher.retrieval.build_retrieval_plan",
            return_value=SimpleNamespace(
                target_queries=[],
                steps=[SimpleNamespace(step_id="synthetic_step")],
                normalized_question="fallback query",
            ),
        ), patch(
            "eubw_researcher.retrieval.retrieve_candidates_with_trace",
        ) as retrieve_mock:
            result = retrieval_backend_comparison._evaluate_runtime(
                question="Synthetic question?",
                target_id="missing-target",
                expected_source_ids=["source-1"],
                expected_intent_type="synthetic_intent",
                runtime_config=SimpleNamespace(local_retrieval_backend="sqlite_fts"),
                hierarchy=object(),
                terminology=object(),
                bundle=object(),
                catalog_path=Path("/tmp/catalog.json"),
                corpus_state_id="synthetic-state",
            )

        self.assertFalse(result["target_present_in_plan"])
        self.assertFalse(result["hit"])
        self.assertEqual(result["evaluated_query"], "fallback query")
        retrieve_mock.assert_not_called()

    def test_summary_blocks_promotion_when_candidate_route_fails(self) -> None:
        summary = retrieval_backend_comparison._summarize_case_reports(
            [
                {
                    "delta": "improved",
                    "baseline": {
                        "hit": False,
                        "intent_matches_expected": True,
                        "target_present_in_plan": True,
                    },
                    "candidate": {
                        "hit": True,
                        "intent_matches_expected": True,
                        "target_present_in_plan": True,
                    },
                },
                {
                    "delta": "unchanged",
                    "baseline": {
                        "hit": False,
                        "intent_matches_expected": True,
                        "target_present_in_plan": True,
                    },
                    "candidate": {
                        "hit": False,
                        "intent_matches_expected": True,
                        "target_present_in_plan": False,
                    },
                },
            ]
        )

        self.assertEqual(summary["improvements"], 1)
        self.assertEqual(summary["candidate_route_failures"], 1)
        self.assertEqual(summary["recommendation"], "keep_baseline_default")
