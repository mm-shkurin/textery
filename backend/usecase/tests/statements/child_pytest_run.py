"""Running a probe module as a child pytest under this project's own configuration.

Kept apart from the gate that asserts on the result, so that file reads as the
claim being made and this one holds the mechanics of getting a trustworthy child:
which configuration it is pointed at, and which ambient state is taken away from
it. Both are the reason a green here means anything.
"""

import os
import subprocess
import sys
from pathlib import Path

from statements.arranged import arranged
from statements.child_pytest_report import ChildPytestReport
from statements.forgotten_await_probes import PROBE_MODULE_NAME

# backend/usecase/tests/statements/<this file> -> backend/
BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_CONFIG = BACKEND_ROOT / "pyproject.toml"

PROBE_TIMEOUT_SECONDS = 180

# Anything the ambient shell or a CI runner can set that would change what the
# child decides about warnings or which plugins it loads. Scrubbed so the gate is
# proven against `pyproject.toml` alone: `PYTHONWARNINGS=ignore::RuntimeWarning`
# in a runner's environment would otherwise make the gate un-failable, and
# `PYTEST_DISABLE_PLUGIN_AUTOLOAD` would keep the control's `async def` test from
# ever running.
LEAKY_CHILD_VARIABLES = (
    "PYTEST_ADDOPTS",
    "PYTHONWARNINGS",
    "PYTEST_PLUGINS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_CURRENT_TEST",
)


def _refuse_a_probe_inside_the_repository(probe_path: Path) -> None:
    """Refuse a destination the parent suite would collect from.

    `resolve()` on both sides, and ancestry rather than a string prefix: a
    scratch reached through a symlink or an `8.3` short path compares unequal as
    text while being the very directory the parent walks.
    """
    if BACKEND_ROOT not in probe_path.resolve().parents:
        return
    raise AssertionError(
        f"a probe may not be written under {BACKEND_ROOT}: the parent suite collects "
        f"`test_*.py` from that tree, so the probe survives as a real test of this suite "
        f"and the gate's claim that the parent never collects it becomes false. Write the "
        f"probe to a tmp_path outside the repository"
    )


class ChildPytestRun:
    """A probe module written to disk, then run by a child pytest."""

    def __init__(self) -> None:
        self._probe_path: Path | None = None
        self._scratch: Path | None = None

    def write_probe(self, tmp_path: Path, source: str) -> None:
        """The probe on disk -- but only once the destination has been judged.

        The refusal is the *first* statement for a reason: `mkdir` and
        `write_text` are both irreversible from the caller's point of view, and a
        guard placed after either has already dropped a `test_*.py` inside the
        tree the parent suite collects. By then the only remaining question is
        whether anything happens to delete it again.
        """
        probe_path = tmp_path / PROBE_MODULE_NAME
        _refuse_a_probe_inside_the_repository(probe_path)
        self._scratch = tmp_path / "child"
        self._scratch.mkdir(parents=True, exist_ok=True)
        self._probe_path = probe_path
        self._probe_path.write_text(source, encoding="utf-8")

    def execute(self) -> ChildPytestReport:
        completed = subprocess.run(
            self._probe_command(),
            env=self._child_environment(),
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            cwd=str(BACKEND_ROOT),
            check=False,
        )
        return ChildPytestReport(completed)

    def _probe_command(self) -> list[str]:
        """A child process, pointed at the real `pyproject.toml`.

        `-c` and `--rootdir` rather than a copy of the settings: a copy would
        assert that some configuration fails a forgotten `await`, which is not the
        claim. The claim is that *this repository's* configuration does.

        `--confcutdir` is the probe's own directory, and it is not decoration.
        pytest walks conftests upward from the *collected file*, not from
        rootdir, and the probe lives outside the repository -- so an unpinned walk
        runs past the scratch to the filesystem root, picking up whatever happens
        to sit above it while never reaching this repository's own conftests.
        Cutting the walk at the probe directory makes the child's conftest set
        exactly empty, which is the set the gate's claim assumes.

        Beyond that the child is left alone: it loads exactly the plugin set the
        real suite loads, or the gate would be proven under a shape nobody runs.
        """
        probe_path = arranged(self._probe_path, "probe module")
        return [
            sys.executable,
            "-m",
            "pytest",
            str(probe_path),
            "-c",
            str(PROJECT_CONFIG),
            "--rootdir",
            str(BACKEND_ROOT),
            "--confcutdir",
            str(probe_path.parent),
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(self._scratch_dir / "basetemp"),
        ]

    def _child_environment(self) -> dict[str, str]:
        """The child gets its own scratch root, and none of the ambient overrides.

        A nested pytest that inherits `TEMP` builds its `tmp_path` factory under a
        directory this process does not own -- and a full-suite run was once seen
        to abort the child's collection with `FileNotFoundError` on exactly such a
        path. The gate must fail only when the gate is wrong, so the shared mutable
        things between parent and child are taken away.
        """
        scratch = str(self._scratch_dir)
        environment = {
            name: value for name, value in os.environ.items() if name not in LEAKY_CHILD_VARIABLES
        }
        return {**environment, "TMPDIR": scratch, "TEMP": scratch, "TMP": scratch}

    @property
    def _scratch_dir(self) -> Path:
        return arranged(self._scratch, "child scratch directory")
