#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _git_value(repo_root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return completed.stdout.strip() or None


def _legacy_reference_files(legacy_root: Path) -> list[Path]:
    if not legacy_root.exists():
        return []
    patterns = [
        "knowledge/claims/*_claim_candidates.jsonl",
        "knowledge/claims/*_claims_draft.jsonl",
        "knowledge/benchmarks/*.jsonl",
        "knowledge/answers/*.json",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(legacy_root.glob(pattern))
    return [path for path in files if path.is_file()]


def build_manifest(
    repo_root: Path,
    *,
    question_pack: Path,
    holdout_pack: Path,
    catalog: Path,
    legacy_root: Path,
) -> dict:
    legacy_files = _legacy_reference_files(legacy_root)
    return {
        "schema_version": "legacy_parity_freeze_manifest.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "commit_sha": _git_value(repo_root, "rev-parse", "HEAD"),
        "git_dirty": bool(_git_value(repo_root, "status", "--short")),
        "question_pack_path": str(question_pack),
        "question_pack_digest": _sha256_file(question_pack),
        "holdout_pack_path": str(holdout_pack),
        "holdout_digest": _sha256_file(holdout_pack),
        "catalog_path": str(catalog),
        "catalog_digest": _sha256_file(catalog) if catalog.is_file() else None,
        "legacy_root": str(legacy_root),
        "legacy_reference_file_count": len(legacy_files),
        "legacy_reference_digest": _sha256_paths(legacy_files),
        "anti_overfit_note": (
            "Aliases, research profiles, source-family rules, and rendering patterns "
            "changed after this freeze must be audited for benchmark-specific risk."
        ),
    }


def main() -> int:
    repo_root = _repo_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--question-pack",
        default="configs/legacy_parity_question_pack.yaml",
    )
    parser.add_argument(
        "--holdout-pack",
        default="configs/migration_question_pack.yaml",
    )
    parser.add_argument(
        "--catalog",
        default="artifacts/real_corpus/curated_catalog.json",
    )
    parser.add_argument(
        "--legacy-root",
        default="/mnt/c/Users/Admin/PycharmProjects/EUBW",
    )
    parser.add_argument(
        "--output",
        default="configs/legacy_parity_freeze_manifest.json",
    )
    args = parser.parse_args()
    manifest = build_manifest(
        repo_root,
        question_pack=(repo_root / args.question_pack).resolve(),
        holdout_pack=(repo_root / args.holdout_pack).resolve(),
        catalog=(repo_root / args.catalog).resolve(),
        legacy_root=Path(args.legacy_root).resolve(),
    )
    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
