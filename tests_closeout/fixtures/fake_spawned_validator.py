from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="pass")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    return parser.parse_args()


def _base_payload() -> dict:
    return {
        "passed": True,
        "context_inherited": False,
        "artifacts_used": [
            "final_answer.txt",
            "approved_ledger.json",
            "facet_coverage.json",
            "pinpoint_evidence.json",
            "answer_alignment.json",
            "manual_review_report.md",
        ],
        "raw_document_reads": [],
        "raw_document_dependency": "none",
        "product_output_self_sufficient": True,
        "summary": "Validator reused the Scenario D bundle successfully.",
        "validator_answer": "Synthetic validator answer.",
    }


def main() -> int:
    args = parse_args()
    request = json.loads(Path(args.input).read_text(encoding="utf-8"))
    payload = _base_payload()
    payload["notes"] = f"Validated bundle {request['bundle_dir']}."
    if args.sleep_seconds:
        time.sleep(args.sleep_seconds)

    if args.mode == "minor_confirmation":
        payload["raw_document_dependency"] = "minor_confirmation"
        payload["raw_document_reads"] = [
            {
                "source_id": "synthetic-source",
                "document_path": None,
                "purpose": "spot-check cited article",
                "classification": "minor_confirmation",
            }
        ]
    elif args.mode == "inherited_context":
        payload["context_inherited"] = True
        payload["summary"] = "Validator reported inherited context."
    elif args.mode == "central_reconstruction":
        payload["raw_document_dependency"] = "central_reconstruction"
        payload["passed"] = False
        payload["product_output_self_sufficient"] = False
        payload["summary"] = "Validator needed central reconstruction."
    elif args.mode == "assert_bundle_ready":
        bundle_dir = Path(request["bundle_dir"])
        missing = [
            name
            for name in request["required_artifacts"]
            if not (bundle_dir / name).exists()
        ]
        if missing:
            payload["passed"] = False
            payload["product_output_self_sufficient"] = False
            payload["raw_document_dependency"] = "central_reconstruction"
            payload["summary"] = "Bundle was missing required artifacts: " + ", ".join(missing)
        else:
            payload["summary"] = "Bundle was ready before validator execution."
    elif args.mode == "string_bools":
        payload["passed"] = "true"
        payload["context_inherited"] = "false"
        payload["product_output_self_sufficient"] = "true"
    elif args.mode == "echo_request":
        payload["notes"] = json.dumps(request, sort_keys=True)
    elif args.mode == "invalid_json":
        Path(args.output).write_text("{invalid", encoding="utf-8")
        return 0
    elif args.mode == "partial_json":
        Path(args.output).write_text('{"passed": true', encoding="utf-8")
        return 0
    elif args.mode == "no_output":
        return 0
    elif args.mode == "nonzero":
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return 3

    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
