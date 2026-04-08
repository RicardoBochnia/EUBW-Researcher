from __future__ import annotations

from _test_runner import run_suites


def main() -> int:
    return run_suites("tests/integration")


if __name__ == "__main__":
    raise SystemExit(main())
