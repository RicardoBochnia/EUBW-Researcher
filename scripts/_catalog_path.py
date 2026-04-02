from __future__ import annotations

from pathlib import Path


def resolve_catalog_path(repo_root: Path, catalog_arg: str | None) -> Path | None:
    if catalog_arg is None:
        return None
    catalog_path = (repo_root / catalog_arg).resolve()
    if not catalog_path.exists():
        raise SystemExit(f"Catalog file not found: {catalog_path}")
    if not catalog_path.is_file():
        raise SystemExit(f"Catalog path is not a file: {catalog_path}")
    return catalog_path
