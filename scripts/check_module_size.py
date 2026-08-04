#!/usr/bin/env python3
"""Rule §7.5 — no module over 300 lines, the engine under 100.

The limit is not about aesthetics. A module that outgrows 300 lines has almost
always absorbed a second capability, and once two capabilities share a module
they can no longer be reasoned about, tested, or failed independently — which
is the property the whole architecture is built on.

The engine's 100-line limit is stricter for the same reason, more so: every
line the engine grows is a line every module now depends on.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _guard import repo_root, report, require_paths

MODULE_LIMIT = 300
ENGINE_LIMIT = 100


def code_lines(path: Path) -> int:
    """Lines that are neither blank nor a comment.

    Docstrings still count. Prose that explains a decision earns its place in
    the budget; if a module is at its limit because it is heavily documented,
    that is a real signal that it is doing too much to explain in one file.
    """
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    args = parser.parse_args()

    src = args.root / "src" / "copernus"
    require_paths([src], "src/copernus")

    violations: list[str] = []
    checked = 0

    engine = src / "engine.py"
    if engine.exists():
        checked += 1
        lines = code_lines(engine)
        if lines > ENGINE_LIMIT:
            violations.append(
                f"{engine.relative_to(args.root)}: {lines} lines > {ENGINE_LIMIT} "
                "(§7.5 — the engine stays small; move logic into a module)"
            )

    modules_dir = src / "modules"
    if modules_dir.exists():
        for module in sorted(p for p in modules_dir.iterdir() if p.is_dir()):
            files = sorted(module.rglob("*.py"))
            if not files:
                continue
            checked += len(files)
            total = sum(code_lines(f) for f in files)
            if total > MODULE_LIMIT:
                violations.append(
                    f"{module.relative_to(args.root)}: {total} lines > {MODULE_LIMIT} "
                    "(§7.5 — split it; a module this size holds two capabilities)"
                )

    return report("module size", violations, checked)


if __name__ == "__main__":
    raise SystemExit(main())
