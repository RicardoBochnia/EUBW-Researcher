from __future__ import annotations

import sys
import unittest
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _discover_suite(root: Path, relative_dir: str) -> unittest.TestSuite:
    return unittest.defaultTestLoader.discover(
        start_dir=str(root / relative_dir),
        pattern="test*.py",
        top_level_dir=str(root),
    )


def run_suites(*relative_dirs: str) -> int:
    root = repo_root()
    sys.path.insert(0, str(root / "src"))
    suite = unittest.TestSuite([_discover_suite(root, relative_dir) for relative_dir in relative_dirs])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1
