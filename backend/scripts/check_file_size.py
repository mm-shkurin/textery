"""Fail if any tracked Python file exceeds the 200-line limit.

The limit is stated in `.claude/rules/coding-rules.md` as a hard rule for every
source file regardless of type. It was the only rule in this repository with no
gate behind it, and it had eight violations -- one of them a production module --
because nothing reported them. Every other stated rule here (lint, format, types,
dependency vulnerabilities, coverage) answers in CI; this one now does too.

Run from `backend/`:

    python scripts/check_file_size.py
"""

import subprocess
import sys
from pathlib import Path

MAX_LINES = 200

# Alembic's own template writes these, and their length is a function of how many
# columns a migration touches. They are excluded from the formatter and the linter
# in pyproject.toml for the same reason, so the exclusion is consistent rather than
# a carve-out invented here.
EXCLUDED_PREFIXES = ("adapters/db/migrations/versions/",)


def tracked_python_files() -> list[str]:
    """Ask git, not the filesystem.

    A `Path.rglob` walk reaches `.venv/`, `__pycache__/` and any scratch file
    sitting in the tree, so the gate's answer would depend on the state of the
    machine running it. Git's index is the same set on every developer's checkout
    and on the runner.
    """
    listed = subprocess.run(
        ["git", "ls-files", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [path for path in listed.stdout.splitlines() if path]


def line_count(path: str) -> int:
    # Counted from bytes split on newline rather than by iterating a text handle,
    # so that a file without a trailing newline counts its last line, and so the
    # count does not vary with the checkout's line endings.
    return len(Path(path).read_bytes().splitlines())


def violations() -> list[tuple[str, int]]:
    found = []
    for path in tracked_python_files():
        if path.startswith(EXCLUDED_PREFIXES):
            continue
        count = line_count(path)
        if count > MAX_LINES:
            found.append((path, count))
    return sorted(found, key=lambda pair: -pair[1])


def main() -> int:
    found = violations()
    if not found:
        return 0
    print(f"{len(found)} file(s) over the {MAX_LINES}-line limit:", file=sys.stderr)
    for path, count in found:
        print(f"  {count:>4}  {path}", file=sys.stderr)
    print(
        "\nSplit them. The limit is in .claude/rules/coding-rules.md and applies to "
        "every source file, tests and fixtures included.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
