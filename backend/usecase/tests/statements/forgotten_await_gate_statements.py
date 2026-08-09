"""The gate that is supposed to fail a suite when a call site forgets an `await`.

`pyproject.toml` carries `filterwarnings` with the stated purpose of turning a
forgotten `await` on an `async` `given_` step from a warning into a failure -- the
exact defect that once left an arrangement silently empty and a test green. That
claim is a claim about the *harness*, which is the one kind of change that cannot
be driven red by an ordinary test: nothing in the suite fails when the filter is
wrong, absent, or matching a warning class that is never raised.

So the claim is asserted by running pytest as a child process against this
project's own configuration file, on a probe module that commits the defect, and
reading the child's report. That shape stays green once the gate works and goes
red the day somebody removes the entry -- which a test living *inside* the gated
suite could never do, because a test that deliberately forgets an `await` would
itself have to fail once the gate bites.
"""

import os
import subprocess
import sys
from pathlib import Path

from statements.arranged import arranged
from statements.child_pytest_report import ChildPytestReport
from statements.forgotten_await_probes import (
    AWAITED_PROBE,
    FORGOTTEN_AWAIT_PROBE,
    PROBE_MODULE_NAME,
    PROBE_TEST_NAME,
    UNAWAITED_COROUTINE_TEXT,
)

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


class ForgottenAwaitGateStatements:
    """Run a probe suite under this project's pytest configuration and read it."""

    def __init__(self) -> None:
        self._probe_path: Path | None = None
        self._report: ChildPytestReport | None = None
        self._scratch: Path | None = None

    def given_a_call_site_that_forgets_to_await_an_async_given_step(self, tmp_path: Path) -> None:
        self._probe_path = self._write_probe(tmp_path, FORGOTTEN_AWAIT_PROBE)

    def given_a_call_site_that_awaits_the_async_given_step(self, tmp_path: Path) -> None:
        self._probe_path = self._write_probe(tmp_path, AWAITED_PROBE)

    def _write_probe(self, tmp_path: Path, source: str) -> Path:
        self._scratch = tmp_path / "child"
        self._scratch.mkdir(parents=True, exist_ok=True)
        probe_path = tmp_path / PROBE_MODULE_NAME
        probe_path.write_text(source, encoding="utf-8")
        return probe_path

    def _child_environment(self) -> dict[str, str]:
        """The child gets its own scratch root, and none of the ambient overrides.

        A nested pytest that inherits `TEMP` builds its `tmp_path` factory under a
        directory this process does not own -- and a full-suite run was once seen
        to abort the child's collection with `FileNotFoundError` on exactly such a
        path. The gate must fail only when the gate is wrong, so the shared mutable
        things between parent and child are taken away.
        """
        scratch = str(arranged(self._scratch, "child scratch directory"))
        environment = {
            name: value for name, value in os.environ.items() if name not in LEAKY_CHILD_VARIABLES
        }
        return {**environment, "TMPDIR": scratch, "TEMP": scratch, "TMP": scratch}

    def run_the_probe_under_the_projects_own_pytest_configuration(self) -> None:
        """A child process, pointed at the real `pyproject.toml`.

        `-c` and `--rootdir` rather than a copy of the settings: a copy would
        assert that some configuration fails a forgotten `await`, which is not the
        claim. The claim is that *this repository's* configuration does.

        Beyond that the child is left alone: it loads exactly the plugin set the
        real suite loads, or the gate would be proven under a shape nobody runs.
        """
        assert self._probe_path is not None, (
            "a probe module must be arranged before the child run -- see the given_ steps"
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(self._probe_path),
                "-c",
                str(PROJECT_CONFIG),
                "--rootdir",
                str(BACKEND_ROOT),
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(arranged(self._scratch, "child scratch directory") / "basetemp"),
            ],
            env=self._child_environment(),
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            cwd=str(BACKEND_ROOT),
            check=False,
        )
        self._report = ChildPytestReport(completed)

    def assert_the_projects_own_configuration_was_in_force(self) -> None:
        """Without this, a child that silently found no config proves nothing.

        pytest falls back to built-in defaults when `-c` cannot be read, and a
        defaults-only run passes the forgotten-await probe for a reason that has
        nothing to do with what this repository declares. Both header lines are
        pinned as whole lines: a substring check would also accept a `rootdir:`
        that merely starts with this path.
        """
        child = self._child()
        for key, value in (("rootdir", BACKEND_ROOT), ("configfile", PROJECT_CONFIG.name)):
            expected = f"{key}: {value}"
            actual = child.header_line(key)
            assert actual == expected, (
                f"the child run reported '{actual}', expected '{expected}' -- a run that fell "
                f"back to pytest's built-in defaults says nothing about the configuration "
                f"this repository actually declares:\n{child.tail}"
            )

    def assert_the_probe_suite_failed(self) -> None:
        self._assert_the_child_reported(1, {"failed": 1})

    def assert_the_probe_suite_passed(self) -> None:
        """The control that makes the failing probe attributable to the `await`.

        Exactly one passed and nothing else: a warning counted here would mean the
        control is not clean, and a skip would mean pytest declined to run an
        `async def` test rather than running it green.
        """
        self._assert_the_child_reported(0, {"passed": 1})

    def _assert_the_child_reported(self, exit_code: int, counts: dict[str, int]) -> None:
        child = self._child()
        assert child.exit_code == exit_code, (
            f"the child pytest exited {child.exit_code}, expected {exit_code}:\n{child.tail}"
        )
        assert child.summary_counts() == counts, (
            f"the child pytest summarised {child.summary_counts()}, expected {counts} -- the "
            f"whole tally is pinned so a second failure, a skip or a stray warning cannot "
            f"hide inside a substring match:\n{child.tail}"
        )

    def assert_the_failure_named_the_unawaited_coroutine(self) -> None:
        """Read out of the FAILURES section, which is the whole point of the check.

        The same sentence appears in the child's *warnings summary* on a run where
        the gate is inert -- so looking for it anywhere in the output would be
        satisfied by the very state this test exists to reject, leaving the exit
        code as the only real assertion. Scoped to the section pytest writes only
        for tests that actually failed, and the failing test is named too.
        """
        child = self._child()
        failures = child.section("FAILURES")
        assert PROBE_TEST_NAME in failures, (
            f"the child's FAILURES section does not name '{PROBE_TEST_NAME}':\n{child.tail}"
        )
        assert UNAWAITED_COROUTINE_TEXT in failures, (
            f"the child failed, but not for the forgotten `await`: no "
            f'"{UNAWAITED_COROUTINE_TEXT}" in its FAILURES section:\n{child.tail}'
        )

    def assert_nothing_was_left_unawaited_on_the_control(self) -> None:
        child = self._child()
        assert UNAWAITED_COROUTINE_TEXT not in child.output, (
            f"the control probe itself left a coroutine unawaited, so it is not a control:"
            f"\n{child.tail}"
        )

    def _child(self) -> ChildPytestReport:
        assert self._report is not None, "the probe must be run before it is asserted on"
        return self._report
