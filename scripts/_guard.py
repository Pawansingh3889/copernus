"""Shared helpers for the guard scripts.

Every guard here obeys one rule that is easy to state and easy to get wrong:

    **A guard that cannot run must fail, not pass.**

The anti-pattern is a checker that exits 0 when its target directory is missing
or its tool is not installed. The run goes green having checked nothing, and
nobody finds out until the thing it was guarding against reaches production.
`require_paths()` exists to make the correct behaviour the easy one.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def require_paths(paths: Iterable[Path], what: str) -> list[Path]:
    """Return the paths, or exit non-zero if there are none.

    Called by every guard before it starts checking. No silent skips.
    """
    found = [p for p in paths if p.exists()]
    if not found:
        fail(
            f"{what} not found — this guard cannot run.",
            "A check that silently skips reports success without having run.",
        )
    return found


def fail(*lines: str) -> None:
    for line in lines:
        print(f"FAIL: {line}", file=sys.stderr)
    raise SystemExit(1)


def report(name: str, violations: list[str], checked: int) -> int:
    """Print the outcome and return the exit code."""
    if violations:
        print(f"FAIL: {name} — {len(violations)} violation(s):", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        return 1
    print(f"ok: {name} — {checked} file(s) checked")
    return 0
