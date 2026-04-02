from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eubw_researcher.evaluation.real_question_pack import (
    default_real_question_pack_output_dir,
    run_real_question_pack,
)


class RealQuestionPackRunnerTests(unittest.TestCase):
    def _write_pack_config(self, root: Path) -> Path:
        pack_path = root / "pack.json"
        pack_path.write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "synthetic_question",
                            "title": "Synthetic Question",
                            "question": "Synthetic question?",
                            "review_focus": "Synthetic review focus.",
                            "expected_intent_type": "synthetic_intent",
                            "tags": ["synthetic"],
                            "review_prompts": ["Is the bundle usable?"],
                        }
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return pack_path

    def _fake_response(self, output_dir: Path) -> SimpleNamespace:
        result = SimpleNamespace(
            query_intent=SimpleNamespace(intent_type="synthetic_intent"),
            approved_entries=[object(), object()],
            gap_records=[object()],
            web_fetch_records=[object(), object()],
            provisional_grouping=[],
            corpus_coverage_report=object(),
        )
        return SimpleNamespace(
            contract_version="option_a_runtime.v1",
            catalog_path=(output_dir.parents[3] / "artifacts" / "real_corpus" / "curated_catalog.json").resolve(),
            corpus_state_id="synthetic-state",
            output_dir=output_dir.resolve(),
            result=result,
        )

    def test_default_output_dir_uses_timestamped_run_id(self) -> None:
        repo_root = Path("/tmp/repo")
        fixed_now = datetime(2026, 4, 3, 10, 15, 30, tzinfo=timezone.utc)

        with patch(
            "eubw_researcher.evaluation.real_question_pack._utcnow",
            return_value=fixed_now,
        ):
            output_dir = default_real_question_pack_output_dir(repo_root)

        self.assertEqual(
            output_dir,
            Path("/tmp/repo/artifacts/real_question_pack_runs/20260403T101530Z"),
        )

    def test_runner_writes_manifest_with_review_signals_and_no_benchmark_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)
            output_dir = repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run"
            fixed_now = datetime(2026, 4, 3, 10, 15, 30, tzinfo=timezone.utc)

            def _write_bundle(question: str, bundle_dir: Path, *, catalog_path=None):
                bundle_dir.mkdir(parents=True, exist_ok=True)
                for artifact_name in [
                    "retrieval_plan.json",
                    "gap_records.json",
                    "web_fetch_records.json",
                    "ingestion_report.json",
                    "ledger_entries.json",
                    "approved_ledger.json",
                    "final_answer.txt",
                    "pinpoint_evidence.json",
                    "answer_alignment.json",
                    "blind_validation_report.json",
                    "manual_review.json",
                    "manual_review_report.md",
                    "corpus_coverage_report.json",
                ]:
                    (bundle_dir / artifact_name).write_text("{}", encoding="utf-8")
                return self._fake_response(bundle_dir)

            fake_report = SimpleNamespace(
                final_judgment="accept",
                usefulness_verdict="accept",
                source_bound_verdict="accept",
                pinpoint_traceability_verdict="accept",
                product_output_self_sufficiency_verdict="needs_follow_up",
            )

            with patch(
                "eubw_researcher.evaluation.real_question_pack._utcnow",
                return_value=fixed_now,
            ), patch(
                "eubw_researcher.evaluation.real_question_pack._git_metadata",
                return_value={
                    "commit": "abc123",
                    "branch": "codex/issue-8-real-question-pack",
                    "dirty": False,
                },
            ), patch(
                "eubw_researcher.evaluation.real_question_pack.ResearchRuntimeFacade"
            ) as facade_cls, patch(
                "eubw_researcher.evaluation.real_question_pack.build_manual_review_report",
                return_value=fake_report,
            ):
                facade_cls.return_value.write_reviewable_artifact_bundle.side_effect = _write_bundle

                run_root, manifest = run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="synthetic_question",
                    output_dir=output_dir,
                    catalog_path=repo_root / "artifacts" / "real_corpus" / "curated_catalog.json",
                )

            manifest_path = run_root / "pack_run_manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(run_root, output_dir.resolve())
            self.assertEqual(manifest.run_id, "synthetic-run")
            self.assertEqual(payload["selected_question_ids"], ["synthetic_question"])
            self.assertEqual(payload["runtime_contract_version"], "option_a_runtime.v1")
            self.assertEqual(payload["git_branch"], "codex/issue-8-real-question-pack")
            self.assertFalse(payload["git_dirty"])
            self.assertEqual(len(payload["question_runs"]), 1)
            self.assertEqual(payload["question_runs"][0]["final_judgment"], "accept")
            self.assertEqual(
                payload["question_runs"][0]["product_output_self_sufficiency_verdict"],
                "needs_follow_up",
            )
            self.assertEqual(payload["question_runs"][0]["missing_artifacts"], [])
            self.assertNotIn("score", payload)
            self.assertNotIn("pass_rate", payload)

    def test_runner_rejects_unknown_question_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            pack_path = self._write_pack_config(repo_root)

            with self.assertRaisesRegex(
                ValueError,
                "Unknown real-question pack question_id: missing",
            ):
                run_real_question_pack(
                    repo_root,
                    pack_path=pack_path,
                    question_id="missing",
                    output_dir=repo_root / "artifacts" / "real_question_pack_runs" / "synthetic-run",
                )


if __name__ == "__main__":
    unittest.main()
