from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _discover_suite(repo_root: Path, relative_dir: str) -> unittest.TestSuite:
    return unittest.defaultTestLoader.discover(
        start_dir=str(repo_root / relative_dir),
        pattern="test*.py",
        top_level_dir=str(repo_root),
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))
    suite = unittest.TestSuite(
        [
            _discover_suite(repo_root, "tests"),
            _discover_suite(repo_root, "tests_closeout"),
        ]
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
