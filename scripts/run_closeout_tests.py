from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(repo_root / "tests_closeout"),
        pattern="test*.py",
        top_level_dir=str(repo_root / "tests_closeout"),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
