"""The arming check, driven red by a runner environment the child gets to keep.

`LiveHarnessConfigurationStatements` is the one guard that asserts on the run
executing it rather than on a file. Its two negative arms have never executed.
`_assert_a_runtime_warning_actually_raises` ends in a `raise AssertionError` that
no test has reached, and `_assert_no_command_line_filter_overrides_the_declaration`
ends in `assert overrides == []` on a list that has always been empty -- and
neither shows up as a coverage gap, because `try`/`except` and `assert` are not
branches to coverage.py. The evidence that they bite was measured by hand at a
terminal. Nothing in the suite would notice if the `except RuntimeWarning` were
widened to `Exception`, or if a future pytest stopped promoting the warning.

So the arming check is run as a child suite under a deliberately disarmed
environment, and the child is required to fail. Two environments, because the two
arms are reached by different vectors and each is invisible to the other:

* `-W ignore::RuntimeWarning` lands in `config.option.pythonwarnings`, which is
  applied after the ini entries and wins -- the shape a `PYTEST_ADDOPTS` in a CI
  runner produces. The declaration still reads exactly the two required entries.
* `-p no:warnings` unloads the plugin that applies `filterwarnings` at all.
  `pythonwarnings` is then empty and the declaration is still intact, so only the
  provoked warning can see it.

The child must therefore be run with its ambient environment left alone, which is
the opposite of what every other gate in this family needs: `ChildPytestRun`
scrubs `LEAKY_CHILD_VARIABLES` unconditionally, precisely so the forgotten-await
gate is proven against `pyproject.toml` and not against a shell. That scrub is why
this file is red today, and lifting it for this family alone is the design cost
the step is named for.
"""

from pathlib import Path

import pytest

from statements.child_pytest_run import LEAKY_CHILD_VARIABLES
from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements

# The probe's single test. Named rather than reused from the forgotten-await
# family: the FAILURES section is compared as a whole set of names, so the name is
# an assertion expectation and must belong to this probe alone.
ARMING_PROBE_TEST_NAME = "test_the_live_arming_check_runs_here"

# The subject, invoked exactly as the real suite invokes it -- through the public
# statement, from a `pytestconfig` that is the child's own. A probe that
# constructed a `Config` by hand would assert on a fabrication.
ARMING_PROBE = f"""
from statements.live_harness_configuration_statements import (
    LiveHarnessConfigurationStatements,
)


def {ARMING_PROBE_TEST_NAME}(pytestconfig) -> None:
    LiveHarnessConfigurationStatements(
        pytestconfig
    ).assert_both_filter_entries_are_in_force_in_this_run()
"""

# The two disarming vectors, and the variable a runner actually sets.
RUNNER_OVERRIDE_VARIABLE = "PYTEST_ADDOPTS"
COMMAND_LINE_FILTER_OVERRIDE = "-W ignore::RuntimeWarning"
UNLOADED_WARNINGS_PLUGIN = "-p no:warnings"

# What each arm must say when it bites. Literals rather than imports from the
# module under test: read back from it, the assertion would still pass with both
# messages rewritten to the empty string, and the whole point of these two arms is
# that a reader meeting them in CI is told which vector disarmed the suite.
#
# The override refusal carries the parsed filter list, so this pins that the
# override genuinely reached the child rather than that the message merely fired.
EXPECTED_OVERRIDE_REFUSAL = (
    "this run carries command-line warning filters ['ignore::RuntimeWarning']"
)
EXPECTED_INERT_FILTER_REFUSAL = "a RuntimeWarning raised in this very run did not fail it"


class DisarmedArmingProbeStatements(ForgottenAwaitGateStatements):
    """Run the live arming check as a child, under an environment of our choosing."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        super().__init__()
        self._monkeypatch = monkeypatch

    def given_a_runner_environment_that_overrides_the_declared_filters(self) -> None:
        self._disarm_the_child_with_only(COMMAND_LINE_FILTER_OVERRIDE)

    def given_a_runner_environment_that_unloads_the_warnings_plugin(self) -> None:
        self._disarm_the_child_with_only(UNLOADED_WARNINGS_PLUGIN)

    def given_a_runner_environment_that_leaves_the_suite_armed(self) -> None:
        """Removed rather than left alone: the control has to be a control.

        Once the child keeps the ambient environment, a developer whose shell
        already carries `PYTEST_ADDOPTS` would disarm the very run that exists to
        show an armed one passing -- and the control would then agree with the two
        disarmed cases for a reason nobody chose.
        """
        self._disarm_the_child_with_only(None)

    def _disarm_the_child_with_only(self, vector: str | None) -> None:
        """Every leaky variable removed, then the one vector put back.

        Scrubbing only `PYTEST_ADDOPTS` would leave each test differing from the
        control by more than the thing it is about. `PYTHONWARNINGS` is the case
        that matters and it is not hypothetical: it is a *different* mechanism from
        the `-W` filters this file's first vector uses -- those land in
        `config.option.pythonwarnings`, while `PYTHONWARNINGS` is read by Python's
        own warnings machinery before pytest sees anything. An ambient
        `PYTHONWARNINGS=ignore::RuntimeWarning` therefore stops the provoked
        RuntimeWarning from raising all by itself, which is precisely the state the
        `-p no:warnings` test asserts. That test would pass with its own vector
        contributing nothing -- green in exactly the state it exists to reject.

        Harmless while `ChildPytestRun` still scrubs these unconditionally, and
        load-bearing the moment this family's step lifts that scrub, which is the
        change the step exists to make. Read from `LEAKY_CHILD_VARIABLES` rather
        than relisted, so the isolation cannot fall behind the scrub it replaces.
        """
        for name in LEAKY_CHILD_VARIABLES:
            self._monkeypatch.delenv(name, raising=False)
        if vector is not None:
            self._monkeypatch.setenv(RUNNER_OVERRIDE_VARIABLE, vector)

    def given_the_live_arming_check_as_the_probe(self, tmp_path: Path) -> None:
        self._run.write_probe(tmp_path, ARMING_PROBE)

    def assert_the_arming_check_refused_the_command_line_override(self) -> None:
        self._assert_the_arming_check_failed_saying(EXPECTED_OVERRIDE_REFUSAL)

    def assert_the_arming_check_refused_the_inert_filter(self) -> None:
        self._assert_the_arming_check_failed_saying(EXPECTED_INERT_FILTER_REFUSAL)

    def assert_the_arming_check_passed_under_an_armed_environment(self) -> None:
        """The control that makes the two refusals attributable to the environment.

        Without it a probe that failed to import, or a statement that raised for
        any reason at all, would satisfy both refusals above on their tally and
        leave only the message text carrying the claim.
        """
        self.assert_the_probe_suite_passed()

    def _assert_the_arming_check_failed_saying(self, expected: str) -> None:
        """The tally, the charged test, and the sentence -- all three or none.

        The tally alone cannot say *which* arm fired, and the sentence alone is
        satisfied by a run that also failed something else or that printed the
        sentence in a warnings summary. `failure_text_contains` is scoped to the
        FAILURES section for that second reason, and the failing names are compared
        as a whole set so an absent section cannot pass.

        Do not weaken the tally to a `failed` count. The inert-filter sentence says
        only that a RuntimeWarning failed to raise, not which vector silenced it,
        and the whole-tally comparison is what tells the two apart: `-p no:warnings`
        unloads the plugin that records warnings, so the tally is exactly
        `{failed: 1}`, whereas a `pyproject.toml` that had simply lost its
        `filterwarnings` entries leaves that plugin loaded, records the provoked
        warning, and reports `{failed: 1, warning: 1}`. Pinning the dict whole is
        the only reason that second state is red rather than silently agreeing.

        The two sentences are deliberately *not* asserted to exclude each other.
        Only one arm can raise per test, so a FAILURES section can never carry
        both, and `not contains(the other sentence)` would be green whenever the
        positive check is green -- an assertion that cannot fail while its partner
        passes proves nothing and is the exact shape this scenario keeps shipping.
        """
        self.assert_the_probe_suite_failed()
        child = self._child()
        failing = child.failing_test_names()
        assert failing == {ARMING_PROBE_TEST_NAME}, (
            f"the child's FAILURES section is about {failing or 'no test at all'}, expected "
            f"exactly {{{ARMING_PROBE_TEST_NAME!r}}} -- the arming check is the only test in "
            f"the probe, so anything else failing means the child broke before it ran:"
            f"\n{child.tail}"
        )
        assert child.failure_text_contains(expected), (
            f"the arming check failed, but not for the disarmed environment: no "
            f'"{expected}" in its FAILURES section. That arm is a `raise` and an `assert` '
            f"that coverage.py does not count as branches, so this sentence is the only "
            f"evidence the arm executed at all:\n{child.tail}"
        )
