"""Running a probe module as a child pytest under this project's own configuration.

Kept apart from the gate that asserts on the result, so that file reads as the
claim being made and this one holds the mechanics of getting a trustworthy child:
which configuration it is pointed at, and which ambient state is taken away from
it. Both are the reason a green here means anything. *Which* ambient state that is
-- the roster itself and the reasoning behind each entry -- is one file further
out, in `child_environment_scrub.py`, so that this file holds the applying and not
the choosing.
"""

import os
import subprocess
import sys
from pathlib import Path

from statements.arranged import arranged
from statements.child_environment_scrub import without_leaky_variables
from statements.child_pytest_report import ChildPytestReport
from statements.forgotten_await_probes import PROBE_MODULE_NAME

# backend/usecase/tests/statements/<this file> -> backend/
BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_CONFIG = BACKEND_ROOT / "pyproject.toml"

# The tree the probe refusal is anchored to. `backend/` is where the *parent suite*
# collects from, but the refusal's own remedy clause says "outside the repository",
# and a guard anchored one level in leaves `<repo>/.tmp` -- what a plain
# `--basetemp`, or a CI image pointing `TMP` at the workspace root, produces --
# approved, with a collectable `test_*.py` left behind for any root-scoped run.
# Resolved, because `_refuse_a_probe_inside_the_repository` compares it against a
# resolved path's `.parents` and an unresolved anchor would never appear there,
# leaving the refusal silently inert.
REPOSITORY_ROOT = BACKEND_ROOT.parent

PROBE_TIMEOUT_SECONDS = 180


def _refuse_a_probe_inside_the_repository(probe_path: Path) -> None:
    """Refuse a destination the parent suite would collect from.

    Ancestry rather than a string prefix: a scratch reached through a symlink or
    an `8.3` short path compares unequal as text while being the directory the
    parent walks. Only `probe_path` is resolved here -- the anchor is resolved at
    its own definition above, and an unresolved one would never appear in a
    resolved path's `.parents`, leaving this refusal silently inert.

    Anchored to the *repository*, not to `backend/`, so that the tree this refuses
    and the tree its own remedy clause names are the same one. Anchored one level
    in, every destination between the two -- `<repo>/.tmp` above all -- passed the
    guard while breaking exactly the claim the guard exists to protect.
    """
    if REPOSITORY_ROOT not in probe_path.resolve().parents:
        return
    raise AssertionError(
        f"a probe may not be written under {REPOSITORY_ROOT}: the parent suite collects "
        f"`test_*.py` from that tree, so the probe survives as a real test of this suite "
        f"and the gate's claim that the parent never collects it becomes false. Write the "
        f"probe to a tmp_path outside the repository"
    )


class ChildPytestRun:
    """A probe module written to disk, then run by a child pytest."""

    def __init__(self, keep_ambient_environment: bool = False) -> None:
        """Scrubbed by default, because the default is what every gate but one needs.

        `keep_ambient_environment=True` is the single opt-in, and it exists for the
        families whose *subject* is a hostile runner environment: they have to hand
        the child a `PYTEST_ADDOPTS` the scrub would otherwise remove. Everywhere
        else -- the forgotten-await gate above all -- the scrub is the reason a green
        means anything, so it stays the default, and the two call sites that want it
        reach it through `KeptAmbientChildBase`, which charges the price beside it.
        """
        self._probe_path: Path | None = None
        self._scratch: Path | None = None
        self._keep_ambient_environment = keep_ambient_environment

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
        """Its own scratch root always; the ambient overrides unless a caller kept them.

        A nested pytest that inherits `TEMP` builds its `tmp_path` factory under a
        directory this process does not own -- and a full-suite run was once seen
        to abort the child's collection with `FileNotFoundError` on exactly such a
        path. The gate must fail only when the gate is wrong, so the shared mutable
        things between parent and child are taken away.

        The scratch redirection is unconditional; only the `LEAKY_CHILD_VARIABLES`
        filter is opt-out, and dropping it is never a convenience -- it means the
        caller is asserting *about* those variables.

        Both halves of that opt-out are asserted on directly, by
        `test_child_environment_scrub.py`: it sets every entry of the roster in the
        parent, calls this method on a default run and on a kept-environment run, and
        compares the set of names each one removed. That is what pins the roster
        itself -- an entry deleted from `LEAKY_CHILD_VARIABLES` is red there and
        nowhere else, because the end-to-end shape can only watch entries with a
        measured disarming vector. `test_forgotten_await_gate.py`'s parametrised
        hostile-environment test is the end-to-end half: it sets a `PYTEST_ADDOPTS`
        measured to disarm the gate and requires the gate to bite anyway, so a
        flipped default here goes red rather than quietly un-arming it.
        """
        scratch = str(self._scratch_dir)
        inherited = (
            dict(os.environ)
            if self._keep_ambient_environment
            else without_leaky_variables(os.environ)
        )
        return {**inherited, "TMPDIR": scratch, "TEMP": scratch, "TMP": scratch}

    @property
    def _scratch_dir(self) -> Path:
        return arranged(self._scratch, "child scratch directory")
