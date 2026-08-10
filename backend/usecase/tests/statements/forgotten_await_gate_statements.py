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

The mechanics of getting a trustworthy child -- the configuration it is pointed
at, the ambient state taken away from it -- live in `ChildPytestRun`; reading its
report as structured values lives in `ChildPytestReport`. What remains here is
the claim.
"""

from pathlib import Path

from statements.child_pytest_report import ChildPytestReport
from statements.child_pytest_run import BACKEND_ROOT, PROJECT_CONFIG, ChildPytestRun
from statements.forgotten_await_probes import (
    AWAITED_PROBE,
    FORGOTTEN_AWAIT_PROBE,
    PROBE_TEST_NAME,
    UNAWAITED_COROUTINE_TEXT,
)


class ForgottenAwaitGateStatements:
    """Run a probe suite under this project's pytest configuration and read it."""

    def __init__(self) -> None:
        self._run = ChildPytestRun()
        self._report: ChildPytestReport | None = None

    def given_a_call_site_that_forgets_to_await_an_async_given_step(self, tmp_path: Path) -> None:
        self._run.write_probe(tmp_path, FORGOTTEN_AWAIT_PROBE)

    def given_a_call_site_that_awaits_the_async_given_step(self, tmp_path: Path) -> None:
        self._run.write_probe(tmp_path, AWAITED_PROBE)

    def run_the_probe_under_the_projects_own_pytest_configuration(self) -> None:
        self._report = self._run.execute()

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
            expected = ChildPytestReport.expected_header_line(key, value)
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
        summarised = child.summary_counts()
        assert summarised == counts, (
            f"the child pytest summarised {summarised}, expected {counts} -- the "
            f"whole tally is pinned so a second failure, a skip or a stray warning cannot "
            f"hide inside a substring match:\n{child.tail}"
        )

    def assert_the_failure_named_the_unawaited_coroutine(
        self, expected_failing: set[str] | None = None
    ) -> None:
        """Read out of the FAILURES section, which is the whole point of the check.

        The same sentence appears in the child's *warnings summary* on a run where
        the gate is inert -- so looking for it anywhere in the output would be
        satisfied by the very state this test exists to reject, leaving the exit
        code as the only real assertion. Scoped to the section pytest writes only
        for tests that actually failed.

        The set of failing names is compared whole rather than searched, so the
        assertion says both which test was charged and which were not, and cannot
        pass over an absent section. `expected_failing` lets the attribution family
        name a different test without recopying this method.
        """
        child = self._child()
        expected = expected_failing if expected_failing is not None else {PROBE_TEST_NAME}
        failing = child.failing_test_names()
        assert failing == expected, (
            f"the child's FAILURES section is about {failing or 'no test at all'}, expected "
            f"exactly {expected} -- an unraisable fires at collection time, so a leak can be "
            f"charged to a test that passes in isolation:\n{child.tail}"
        )
        failures = child.section("FAILURES")
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

    # Not `arranged()`: that helper's message tells the reader to call a `given_*`
    # step, and the step that sets this one is the act step, not an arrangement.
    def _child(self) -> ChildPytestReport:
        assert self._report is not None, "the probe must be run before it is asserted on"
        return self._report
