# Tests that every checker script really catches the mistake it exists to catch.
"""Prove every gate rejects a planted violation.

A guard that has never been observed to fail is decoration. Green output tells
you a script ran and printed something reassuring; it does not tell you the
script would have objected had there been something to object to.

Each test here builds a small fake repository in `tmp_path`, plants exactly one
violation, and asserts a non-zero exit. Each also asserts the *clean* case
passes, because a guard that fails on everything is equally useless.

The third case each guard must handle is the one that bites in practice: a
missing precondition must **fail**, not pass. `scripts/_guard.py` exists for
that, and `test_*_fails_when_it_cannot_run` pins it down.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

# The console script, not `python -m importlinter` — the package has no
# __main__, so `-m` exits 0 having done nothing. A proof that invokes the
# checker wrongly is the exact failure these tests exist to catch.
LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"


def run_guard(script: str, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A minimal well-formed repository. Each test breaks one thing."""
    (tmp_path / "src" / "copernus" / "modules" / "demo").mkdir(parents=True)
    (tmp_path / "src" / "copernus" / "engine.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "copernus" / "modules" / "demo" / "contract.py").write_text(
        "password: str\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# Fake\n\nNothing to see.\n", encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------------
# check_module_size.py — §7.5
# --------------------------------------------------------------------------


def test_module_size_passes_on_a_clean_repo(fake_repo):
    assert run_guard("check_module_size.py", fake_repo).returncode == 0


def test_module_size_rejects_an_oversized_module(fake_repo):
    bloated = fake_repo / "src" / "copernus" / "modules" / "demo" / "service.py"
    bloated.write_text("\n".join(f"x{i} = {i}" for i in range(400)), encoding="utf-8")

    result = run_guard("check_module_size.py", fake_repo)

    assert result.returncode == 1
    assert "300" in result.stderr


def test_module_size_rejects_an_oversized_engine(fake_repo):
    (fake_repo / "src" / "copernus" / "engine.py").write_text(
        "\n".join(f"x{i} = {i}" for i in range(150)), encoding="utf-8"
    )

    result = run_guard("check_module_size.py", fake_repo)

    assert result.returncode == 1
    assert "engine.py" in result.stderr


def test_module_size_fails_when_it_cannot_run(tmp_path):
    """No src/copernus at all. The guard must object, not shrug."""
    result = run_guard("check_module_size.py", tmp_path)

    assert result.returncode == 1
    assert "cannot run" in result.stderr


# --------------------------------------------------------------------------
# check_no_secrets_in_contracts.py — §7.4 / C-08
# --------------------------------------------------------------------------


def test_secrets_guard_passes_on_a_bare_annotation(fake_repo):
    """`password: str` is a contract declaring a field. Not a violation."""
    assert run_guard("check_no_secrets_in_contracts.py", fake_repo).returncode == 0


def test_secrets_guard_rejects_an_assigned_secret(fake_repo):
    (fake_repo / "src" / "copernus" / "modules" / "demo" / "contract.py").write_text(
        'password = "hunter2"\n', encoding="utf-8"
    )

    result = run_guard("check_no_secrets_in_contracts.py", fake_repo)

    assert result.returncode == 1
    assert "password" in result.stderr


def test_secrets_guard_rejects_an_annotated_assignment(fake_repo):
    (fake_repo / "src" / "copernus" / "modules" / "demo" / "contract.py").write_text(
        'connection_string: str = "Server=db;Pwd=x"\n', encoding="utf-8"
    )

    result = run_guard("check_no_secrets_in_contracts.py", fake_repo)

    assert result.returncode == 1
    assert "connection_string" in result.stderr


def test_secrets_guard_allows_an_empty_default(fake_repo):
    """An empty string is a placeholder, not a leaked credential."""
    (fake_repo / "src" / "copernus" / "modules" / "demo" / "contract.py").write_text(
        'api_key: str = ""\n', encoding="utf-8"
    )

    assert run_guard("check_no_secrets_in_contracts.py", fake_repo).returncode == 0


def test_secrets_guard_fails_when_it_cannot_run(tmp_path):
    result = run_guard("check_no_secrets_in_contracts.py", tmp_path)

    assert result.returncode == 1
    assert "cannot run" in result.stderr


# --------------------------------------------------------------------------
# check_no_python_in_markdown.py
# --------------------------------------------------------------------------


def test_markdown_guard_passes_on_prose(fake_repo):
    assert run_guard("check_no_python_in_markdown.py", fake_repo).returncode == 0


def test_markdown_guard_rejects_an_embedded_script(fake_repo):
    body = "\n".join(["import os"] + [f"value_{i} = {i}" for i in range(20)])
    (fake_repo / "GUIDE.md").write_text(f"# Guide\n\n```python\n{body}\n```\n", encoding="utf-8")

    result = run_guard("check_no_python_in_markdown.py", fake_repo)

    assert result.returncode == 1
    assert "GUIDE.md" in result.stderr


def test_markdown_guard_allows_a_short_snippet(fake_repo):
    """A three-line example is documentation, not a program."""
    (fake_repo / "GUIDE.md").write_text(
        "# Guide\n\n```python\nresult = engine.dispatch(event)\n```\n", encoding="utf-8"
    )

    assert run_guard("check_no_python_in_markdown.py", fake_repo).returncode == 0


def test_markdown_guard_ignores_other_languages(fake_repo):
    """A long bash block is not Python and must not be flagged as such."""
    body = "\n".join(f"echo line {i}" for i in range(30))
    (fake_repo / "GUIDE.md").write_text(f"# Guide\n\n```bash\n{body}\n```\n", encoding="utf-8")

    assert run_guard("check_no_python_in_markdown.py", fake_repo).returncode == 0


def test_markdown_guard_fails_when_it_cannot_run(tmp_path):
    """No Markdown anywhere — the guard cannot have checked anything."""
    result = run_guard("check_no_python_in_markdown.py", tmp_path)

    assert result.returncode == 1
    assert "cannot run" in result.stderr


# --------------------------------------------------------------------------
# check_no_windows_paths.py
#
# The drive prefixes below are assembled at runtime rather than written as
# literals. This file is inside the tree the guard scans, so a literal here
# would make the guard fail on its own proof — and the fix for that must not be
# an exclusion list. Every suppression mechanism eventually gets used to silence
# a real finding; not having one is worth two lines of string concatenation.
# --------------------------------------------------------------------------

_DRIVE_C = "C" + ":"
_DRIVE_D = "D" + ":"


def test_windows_path_guard_passes_on_a_clean_repo(fake_repo):
    assert run_guard("check_no_windows_paths.py", fake_repo).returncode == 0


def test_windows_path_guard_rejects_a_drive_path(fake_repo):
    (fake_repo / "src" / "copernus" / "modules" / "demo" / "repository.py").write_text(
        f'EXPORT = "{_DRIVE_C}/Users/operator/export.csv"\n', encoding="utf-8"
    )

    result = run_guard("check_no_windows_paths.py", fake_repo)

    assert result.returncode == 1
    assert "repository.py" in result.stderr


def test_windows_path_guard_rejects_a_backslash_drive_path(fake_repo):
    (fake_repo / "NOTES.md").write_text(f"Look in {_DRIVE_D}\\shared\\reports\n", encoding="utf-8")

    result = run_guard("check_no_windows_paths.py", fake_repo)

    assert result.returncode == 1


def test_windows_path_guard_allows_a_serial_port_name(fake_repo):
    """COM1 is checkweigher configuration, not a path. Flagging it would make
    the guard something people learn to ignore."""
    (fake_repo / "settings.ini").write_text("port = COM1\n", encoding="utf-8")

    assert run_guard("check_no_windows_paths.py", fake_repo).returncode == 0


def test_windows_path_guard_fails_when_it_cannot_run(tmp_path):
    result = run_guard("check_no_windows_paths.py", tmp_path)

    assert result.returncode == 1
    assert "cannot run" in result.stderr


# --------------------------------------------------------------------------
# check_coverage_floors.py
# --------------------------------------------------------------------------


def _write_project(root: Path, floors: str) -> None:
    (root / "pyproject.toml").write_text(
        f"[tool.copernus.coverage_floors]\n{floors}\n", encoding="utf-8"
    )


def _write_report(root: Path, path: str, percent: float) -> None:
    report = {"files": {path: {"summary": {"percent_covered": percent}}}}
    (root / "coverage.json").write_text(json.dumps(report), encoding="utf-8")


def test_coverage_floors_pass_when_met(tmp_path):
    _write_project(tmp_path, '"src/copernus/x.py" = 90')
    _write_report(tmp_path, "src/copernus/x.py", 95.0)

    assert run_guard("check_coverage_floors.py", tmp_path).returncode == 0


def test_coverage_floors_reject_a_module_below_its_floor(tmp_path):
    _write_project(tmp_path, '"src/copernus/x.py" = 100')
    _write_report(tmp_path, "src/copernus/x.py", 87.5)

    result = run_guard("check_coverage_floors.py", tmp_path)

    assert result.returncode == 1
    assert "87.5" in result.stdout


def test_coverage_floors_reject_a_floor_for_an_unmeasured_file(tmp_path):
    """A floor naming a file coverage never saw protects nothing.

    Without this, deleting or renaming a module silently retires its floor,
    and the config goes on looking protective indefinitely.
    """
    _write_project(tmp_path, '"src/copernus/gone.py" = 100')
    _write_report(tmp_path, "src/copernus/other.py", 100.0)

    result = run_guard("check_coverage_floors.py", tmp_path)

    assert result.returncode == 1
    assert "never measured" in result.stdout


def test_coverage_floors_fail_when_no_report_exists(tmp_path):
    """The classic silent pass: no report, so nothing was checked."""
    _write_project(tmp_path, '"src/copernus/x.py" = 90')

    result = run_guard("check_coverage_floors.py", tmp_path)

    assert result.returncode == 1
    assert "cannot run" in result.stderr


def test_coverage_floors_fail_when_none_are_declared(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    _write_report(tmp_path, "src/copernus/x.py", 100.0)

    result = run_guard("check_coverage_floors.py", tmp_path)

    assert result.returncode == 1
    assert "coverage_floors" in result.stderr


# --------------------------------------------------------------------------
# import-linter contracts
# --------------------------------------------------------------------------


def test_import_contracts_hold_on_the_real_repo():
    """The contracts pass as the repository actually stands."""
    result = subprocess.run(
        [str(LINT_IMPORTS)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 kept, 0 broken" in result.stdout


def test_forbidden_contract_rejects_io_in_a_service(tmp_path):
    """Plant an I/O import in a service and prove the contract breaks.

    Run against a copy so the real tree is never modified — a proof that
    requires editing the repository under test is one nobody will run twice.
    """
    import shutil

    work = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT,
        work,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "htmlcov"
        ),
    )

    service = work / "src" / "copernus" / "modules" / "auth" / "service.py"
    service.write_text("import sqlite3\n\n" + service.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [str(LINT_IMPORTS)],
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(work / "src")},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout
    assert "Services are pure" in result.stdout


# --------------------------------------------------------------------------
# check_doc_freshness.py — §7.8
#
# The rule this guard mechanises had already failed in this repository: all
# three governed documents carried "29 March 2026" while their commits were
# four months later. Prose rules rot; this one now has to hold.
# --------------------------------------------------------------------------


def _git_repo_with_doc(tmp_path: Path, header_date: str) -> Path:
    """A repo with one governed doc, committed, carrying `header_date`."""
    for name in ("ARCHITECTURE.md", "ROADMAP.md"):
        (tmp_path / name).write_text(
            f"# {name}\n\n> **Last updated:** {header_date}\n", encoding="utf-8"
        )
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@e",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e",
    }
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "docs"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, env=env, capture_output=True)
    return tmp_path


def test_doc_freshness_passes_when_the_header_is_current(tmp_path):
    repo = _git_repo_with_doc(tmp_path, date.today().strftime("%d %B %Y"))
    assert run_guard("check_doc_freshness.py", repo).returncode == 0


def test_doc_freshness_rejects_a_header_older_than_the_last_commit(tmp_path):
    repo = _git_repo_with_doc(tmp_path, "29 March 2020")
    result = run_guard("check_doc_freshness.py", repo)
    assert result.returncode == 1
    assert "the document changed and the header did not" in result.stderr


def test_doc_freshness_rejects_a_missing_header(tmp_path):
    repo = _git_repo_with_doc(tmp_path, date.today().strftime("%d %B %Y"))
    (repo / "ROADMAP.md").write_text("# ROADMAP\n\nNo header at all.\n", encoding="utf-8")
    result = run_guard("check_doc_freshness.py", repo)
    assert result.returncode == 1
    assert "no '**Last updated:**' header" in result.stderr


def test_doc_freshness_refuses_to_run_outside_a_git_repo(tmp_path):
    """The guard must fail, not pass, when it cannot check anything."""
    for name in ("ARCHITECTURE.md", "ROADMAP.md"):
        (tmp_path / name).write_text("> **Last updated:** 1 January 2030\n", encoding="utf-8")
    result = run_guard("check_doc_freshness.py", tmp_path)
    assert result.returncode == 1
    assert "not a git repository" in result.stderr
