"""Run every blocking gate CI runs, in CI's order, as one command.

The gates existed before this script and were correct; what was missing was a
single way to run them. Five separate commands means the cheap ones get run and
the slow one does not, which is exactly how a red `types` job reached `main`
twice: `mypy` over the src roots was run, bare `mypy` -- the one CI runs, which
also checks the tests -- was not.

Ordered cheapest-first so a formatting mistake is reported in seconds rather than
after the suite. Does NOT stop at the first failure: knowing all four verdicts is
worth the extra seconds, and stopping early turns one fix-and-rerun cycle into
four. `pytest` needs no database for the suites listed here; the db adapter's own
suite skips itself without PostgreSQL, so it is included and simply reports its
skips.

Mirrors `.github/workflows/ci.yml`. If a gate is added there, add it here.
"""

import subprocess
import sys

# Exactly the invocation each CI step runs. `mypy` with no argument is the whole
# configured file set (tests included); the second invocation names the src roots
# because --disallow-incomplete-defs cannot be scoped in pyproject.toml -- see the
# comment on that step in ci.yml.
GATES: list[tuple[str, list[str]]] = [
    ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ("ruff format --check", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("file sizes", [sys.executable, "scripts/check_file_size.py"]),
    ("mypy", [sys.executable, "-m", "mypy"]),
    (
        "mypy --disallow-incomplete-defs",
        [
            sys.executable,
            "-m",
            "mypy",
            "--disallow-incomplete-defs",
            "domain/src",
            "usecase/src",
            "adapters/rest/src",
            "adapters/db/src",
            "adapters/security/src",
            "adapters/rendering/src",
            "adapters/generation_provider/src",
            "adapters/oauth_provider/src",
            "application/src",
        ],
    ),
    # --cov with the source roots named in pyproject, and the same floor CI
    # blocks on. Running plain `pytest` here would have made this script claim to
    # be the CI gate list while silently dropping the coverage ratchet.
    (
        "pytest --cov-fail-under=90",
        [sys.executable, "-m", "pytest", "-q", "--cov", "--cov-fail-under=90"],
    ),
    # The only gate here that needs the network: it asks PyPI's advisory data
    # about the pinned runtime set. Scoped to requirements.txt, not the installed
    # environment, so a red result is unambiguous about what deploys.
    ("pip-audit", [sys.executable, "-m", "pip_audit", "-r", "requirements.txt"]),
]


def main() -> int:
    failed: list[str] = []
    for name, command in GATES:
        print(f"\n=== {name}", flush=True)
        if subprocess.run(command).returncode != 0:
            failed.append(name)

    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print(f"\nAll {len(GATES)} gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
