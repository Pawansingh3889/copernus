#!/usr/bin/env python3
# This checker makes sure no passwords or secrets sneak into the contract files.
"""Rule §7.4 / constraint C-08 — no secret literal in a contract module.

`contract.py` files describe the shape of a module's inputs and outputs. They
get copied into documentation, pasted into tickets, and dumped wholesale into
LLM context by `concat_codebase.py`. A credential that lands in one travels
further and faster than a credential anywhere else in the tree.

Detection is deliberately narrow: a *secret-looking name assigned a non-empty
string literal*. Flagging every occurrence of the word "password" would fire on
`password: str` — a type annotation, which is exactly what a contract is
supposed to contain — and a guard that cries wolf gets suppressed, at which
point it protects nothing.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

from _guard import repo_root, report, require_paths

SECRET_NAMES = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "connection_string",
    "conn_str",
    "dsn",
    "credential",
)


def looks_secret(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in SECRET_NAMES)


def check_file(path: Path) -> list[str]:
    """Find secret-looking names bound to a non-empty string literal."""
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in ast.walk(tree):
        targets: list[ast.expr] = []
        value: ast.expr | None = None

        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value

        # A bare annotation (`password: str`) has no value and is fine — that
        # is a contract declaring a field, not carrying a secret.
        if value is None or not isinstance(value, ast.Constant):
            continue
        if not isinstance(value.value, str) or not value.value:
            continue

        for target in targets:
            name = target.id if isinstance(target, ast.Name) else None
            if name and looks_secret(name):
                violations.append(
                    f"{path}:{node.lineno} — {name!r} is assigned a string literal. "
                    "Secrets are configuration only (§7.4, C-08)."
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    args = parser.parse_args()

    src = args.root / "src"
    require_paths([src], "src")

    contracts = sorted(src.rglob("contract.py"))
    if not contracts:
        # No contract files yet is a legitimate state early in the project, but
        # say so out loud rather than printing a reassuring "ok".
        print("ok: no secrets in contracts — 0 contract.py files exist yet")
        return 0

    violations: list[str] = []
    for path in contracts:
        violations.extend(check_file(path))

    return report("no secrets in contracts", violations, len(contracts))


if __name__ == "__main__":
    raise SystemExit(main())
