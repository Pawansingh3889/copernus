"""Guard: a document's "Last updated" header must not predate its own last commit.

ARCHITECTURE.md §7.8 requires the design documents to be updated with every
structural change. That rule was written as prose and immediately rotted: all
three documents carried "29 March 2026" while their commits were four months
later. A rule that depends on someone remembering is a rule that fails quietly.

This makes it mechanical. For each governed document, compare the date in its
header against the date of the most recent commit touching that file. A header
older than the file's own history means the document changed and the header did
not — which is exactly the drift §7.8 exists to prevent.

Deliberately *not* checked: that the header equals today. A document that has
not changed should not need its header bumped, and demanding that would train
people to edit the field without reading the document.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

from _guard import fail, repo_root, report, require_paths

# Documents that assert §7.8 over themselves.
GOVERNED = ("ARCHITECTURE.md", "ROADMAP.md")

HEADER = re.compile(r"^>\s*\*\*Last updated:\*\*\s*(.+?)\s*$", re.MULTILINE)

# "29 March 2026" and "2026-03-29" are both allowed; anything else is a parse
# failure, which is a violation rather than a skip.
FORMATS = ("%d %B %Y", "%Y-%m-%d")


def parse_header_date(raw: str) -> date | None:
    for fmt in FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def last_commit_date(path: Path, root: Path) -> date | None:
    """Date of the most recent commit touching `path`, or None if never committed."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", path.name],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    stamp = result.stdout.strip()
    if result.returncode != 0 or not stamp:
        return None
    return datetime.strptime(stamp, "%Y-%m-%d").date()


def check_file(path: Path, root: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = HEADER.search(text)
    if not match:
        return [f"{path.name}: no '**Last updated:**' header — §7.8 cannot be checked"]

    header_date = parse_header_date(match.group(1))
    if header_date is None:
        return [
            f"{path.name}: unparseable date {match.group(1)!r} "
            f"(want '1 January 2026' or '2026-01-01')"
        ]

    committed = last_commit_date(path, root)
    if committed is None:
        # Never committed: nothing to compare against, and saying "ok" would be
        # a guard reporting success without having checked anything.
        return [f"{path.name}: no commit history for this file — cannot verify freshness"]

    if header_date < committed:
        return [
            f"{path.name}: header says {header_date}, last commit was {committed} — "
            f"the document changed and the header did not (§7.8)"
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    args = parser.parse_args()

    docs = require_paths([args.root / name for name in GOVERNED], "governed documents")

    if not (args.root / ".git").exists():
        fail(
            "not a git repository — this guard compares against commit history.",
            "Refusing to report success without having checked anything.",
        )

    violations: list[str] = []
    for path in docs:
        violations.extend(check_file(path, args.root))

    return report("doc freshness", violations, len(docs))


if __name__ == "__main__":
    raise SystemExit(main())
