#!/usr/bin/env python3
# This checker fails the build if the tests cover too little of any module's code.
"""Per-module coverage floors, declared in pyproject.toml.

A single global `--cov-fail-under=80` is a weaker check than it looks. Coverage
is an average, and averages hide their worst component: a thoroughly tested
pure core carries an untested I/O layer over the line, and the number stays
green for precisely the file you were unsure about.

Floors are per-path instead, under `[tool.copernus.coverage_floors]`. Services are
pure functions with no I/O — they have no excuse, and they floor at 100.

Run `coverage json` (or `pytest --cov --cov-report=json`) first; this reads
`coverage.json`.
"""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

from _guard import fail, repo_root

DEFAULT_REPORT = "coverage.json"


def load_floors(pyproject: Path) -> dict[str, int]:
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return config.get("tool", {}).get("copernus", {}).get("coverage_floors", {})


def normalise(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    pyproject = args.root / "pyproject.toml"
    if not pyproject.exists():
        fail("pyproject.toml not found — cannot read coverage floors.")

    floors = load_floors(pyproject)
    if not floors:
        fail(
            "No [tool.copernus.coverage_floors] declared in pyproject.toml.",
            "Declare a floor per module rather than relying on a global average.",
        )

    report_path = args.report or (args.root / DEFAULT_REPORT)
    if not report_path.exists():
        fail(
            f"{report_path} not found — this guard cannot run.",
            "Run: uv run pytest --cov --cov-report=json",
        )

    data = json.loads(report_path.read_text(encoding="utf-8"))
    measured = {normalise(path): entry for path, entry in data.get("files", {}).items()}

    violations: list[str] = []
    for target, floor in sorted(floors.items()):
        key = normalise(target)
        entry = measured.get(key)
        if entry is None:
            # A floor naming a file coverage never saw is a broken floor. It
            # would otherwise sit in the config looking protective forever.
            violations.append(f"{target}: declared a floor of {floor}% but was never measured")
            continue

        actual = entry["summary"]["percent_covered"]
        if actual + 1e-9 < floor:
            violations.append(f"{target}: {actual:.1f}% < {floor}% floor")

    if violations:
        print(f"FAIL: coverage floors — {len(violations)} violation(s):")
        for violation in violations:
            print(f"  {violation}")
        return 1

    print(f"ok: coverage floors — {len(floors)} module(s) at or above floor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
