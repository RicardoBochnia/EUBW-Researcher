from __future__ import annotations

from pathlib import Path
from typing import Optional


def resolve_catalog_path(repo_root: Path, catalog_arg: Optional[str]) -> Optional[Path]:
    """Resolve and validate a CLI catalog path.

    Returns ``None`` when no catalog argument was provided.
    Raises ``SystemExit`` with a clear message when the resolved path does not
    exist or does not point to a file.
    """
    if catalog_arg is None:
        return None
    catalog_path = (repo_root / catalog_arg).resolve()
    if not catalog_path.exists():
        raise SystemExit(f"Catalog file not found: {catalog_path}")
    if not catalog_path.is_file():
        raise SystemExit(f"Catalog path is not a file: {catalog_path}")
    return catalog_path
