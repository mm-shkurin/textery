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
report as structured values lives in `ChildPytestReport`; running a probe as a
child at all lives in `ChildProbeStatements`. What remains here is the claim.
"""

from pathlib import Path

import pytest

from statements.child_probe_statements import ChildProbeStatements
from statements.forgotten_await_probes import (
    AWAITED_PROBE,
    FORGOTTEN_AWAIT_PROBE,
    PROBE_TEST_NAME,
    UNAWAITED_COROUTINE_TEXT,
)

# What a run whose FAILURES section lacks the coroutine sentence actually means.
NOT_THE_FORGOTTEN_AWAIT = "the child failed, but not for the forgotten `await`"


class ForgottenAwaitGateStatements(ChildProbeStatements):
    """The forgotten-await probe, and what the child must say about it."""

    def given_a_call_site_that_forgets_to_await_an_async_given_step(self, tmp_path: Path) -> None:
        self._write_probe(tmp_path, FORGOTTEN_AWAIT_PROBE)

    def given_a_call_site_that_awaits_the_async_given_step(self, tmp_path: Path) -> None:
        self._write_probe(tmp_path, AWAITED_PROBE)

    def given_a_hostile_runner_environment(
        self, monkeypatch: pytest.MonkeyPatch, variable: str, value: str
    ) -> None:
        """Set in the parent, so the question is whether the child inherits it.

        Taking `monkeypatch` as a step argument the way the steps above take
        `tmp_path`, rather than through the constructor: `GateReachStatements`
        inherits this family and has no runner environment to stage, and a required
        constructor dependency would make it carry one that is false for it.

        The parent's own run is unaffected -- its filters and `config.option` were
        resolved at startup -- and `monkeypatch` restores the variable at teardown
        however the test ends.
        """
        monkeypatch.setenv(variable, value)

    def assert_the_failure_named_the_unawaited_coroutine(self) -> None:
        """Read out of the FAILURES section, which is the whole point of the check.

        The same sentence appears in the child's *warnings summary* on a run where
        the gate is inert -- so looking for it anywhere in the output would be
        satisfied by the very state this test exists to reject, leaving the exit
        code as the only real assertion. Scoped to the section pytest writes only
        for tests that actually failed.

        The set of failing names is compared whole rather than searched, so the
        assertion says both which test was charged and which were not, and cannot
        pass over an absent section.
        """
        self._assert_the_await_leak_was_charged_to({PROBE_TEST_NAME})

    def _assert_the_await_leak_was_charged_to(self, expected: set[str]) -> None:
        """The same claim against a named set, for a probe that fails elsewhere.

        Parameterised here rather than on the public step so that step keeps its
        no-argument reading -- a test body naming the probe's own test would be
        restating this family's fixture back at it. The expected sentence is fixed
        because it is what makes this family's claim about the `await` and not
        about a child that failed for any reason at all.
        """
        self._assert_the_failure_was_charged_to(
            expected, UNAWAITED_COROUTINE_TEXT, NOT_THE_FORGOTTEN_AWAIT
        )

    def assert_nothing_was_left_unawaited_on_the_control(self) -> None:
        child = self._child()
        assert UNAWAITED_COROUTINE_TEXT not in child.output, (
            f"the control probe itself left a coroutine unawaited, so it is not a control:"
            f"\n{child.tail}"
        )
