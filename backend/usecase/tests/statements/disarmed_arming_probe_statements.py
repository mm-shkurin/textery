"""The arming check, driven red by a runner environment the child gets to keep.

`LiveHarnessConfigurationStatements` is the one guard that asserts on the run
executing it rather than on a file. It runs **three** checks, and none of their
negative arms has ever executed. Two of the three are driven here; the third,
`_assert_the_declaration_is_exactly_the_required_entries`, is unreachable by
either vector below because both short-circuit ahead of it, and is scheduled
separately with its own vector (`-o filterwarnings=...`).
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
scrubs `LEAKY_CHILD_VARIABLES` by default, precisely so the forgotten-await gate
is proven against `pyproject.toml` and not against a shell. This family was the
first `keep_ambient_environment=True` call site and the potency control beside the
forgotten-await gate is the second; both pay the same price for that exemption --
scrub by hand what the base no longer scrubs, then put back exactly one vector --
which is why the mechanics live in the shared `DisarmedChildEnvironment`.
"""

from pathlib import Path

import pytest

from statements.arming_probe import (
    ARMING_PROBE,
    ARMING_PROBE_TEST_NAME,
    COMMAND_LINE_FILTER_OVERRIDE,
    EXPECTED_INERT_FILTER_REFUSAL,
    EXPECTED_OVERRIDE_REFUSAL,
    NOT_THE_DISARMED_ENVIRONMENT,
    UNLOADED_WARNINGS_PLUGIN,
)
from statements.child_probe_statements import ChildProbeStatements
from statements.disarmed_child_environment import DisarmedChildEnvironment


class DisarmedArmingProbeStatements(ChildProbeStatements):
    """Run the live arming check as a child, under an environment of our choosing."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        super().__init__(keep_ambient_environment=True)
        self._environment = DisarmedChildEnvironment(monkeypatch)

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
        """Every steerable variable removed, then the one vector put back.

        The mechanics moved to `DisarmedChildEnvironment` when the potency control
        beside the forgotten-await gate needed the identical price for the identical
        exemption; why the whole roster is scrubbed rather than `PYTEST_ADDOPTS`
        alone, and why that roster is not the subject's own, is recorded there.
        What stays this family's is *which* vectors exist.
        """
        self._environment.disarm_with_only(vector)

    def given_the_live_arming_check_as_the_probe(self, tmp_path: Path) -> None:
        self._write_probe(tmp_path, ARMING_PROBE)

    def run_the_probe_expecting_it_to_be_refused(self) -> None:
        """The act for the arrangement guard this family does not yet have.

        The sibling overrides its act to call
        `refuse_the_act_until_a_vector_was_chosen()` first; this one runs a child
        straight away, so the `pytest.raises` below is what goes red today -- and
        `assert_no_child_was_run_before_the_refusal` is red independently of it.
        """
        with pytest.raises(AssertionError) as refusal:
            self.run_the_probe_under_the_projects_own_pytest_configuration()
        self._environment.record_the_refusal(refusal.value)

    def assert_the_refusal_named_the_unchosen_environment(self) -> None:
        self._environment.assert_the_refusal_named_the_unchosen_environment()

    def assert_no_child_was_run_before_the_refusal(self) -> None:
        """Red for a second, independent reason today, and that is deliberate.

        This family's act is unguarded, so it runs a real child under whatever the
        ambient environment carries and only the `pytest.raises` above goes red. Once
        the guard lands, this is what keeps it from being satisfied by a check placed
        *after* the run -- which would raise the right sentence while paying the whole
        cost the guard exists to avoid.
        """
        self._environment.assert_no_child_was_run_before_the_refusal(self._no_child_was_run())

    def assert_the_arming_check_refused_the_command_line_override(self) -> None:
        self._assert_the_arming_check_failed_saying(EXPECTED_OVERRIDE_REFUSAL)

    def assert_the_arming_check_refused_the_inert_filter(self) -> None:
        self._assert_the_arming_check_failed_saying(EXPECTED_INERT_FILTER_REFUSAL)

    def assert_the_arming_check_passed_under_an_armed_environment(self) -> None:
        """The only run in this family that executes the arming check's passing arm.

        Its earlier justification was wrong in both halves and is corrected rather
        than carried. A probe that failed to import does *not* satisfy the refusals
        above: it yields `{errors: 1}` and exit 2, which the whole-tally-plus-exit-
        code pin rejects on its own, and it produces an empty `failing_test_names()`,
        which the set equality rejects independently. Nor does this test make those
        refusals attributable to their environments -- it is a separate test with its
        own child run, and three independent runs cannot cross-check each other; a
        shared fixture would.

        What it does do is the reason to keep it: every other test here requires the
        check to *fail*, so without this one the `return` arm of
        `_assert_a_runtime_warning_actually_raises` -- the path the whole suite runs
        under -- would never be executed by any test at all, and an arming check that
        refused every environment would look identical.
        """
        self.assert_the_probe_suite_passed()

    def _assert_the_arming_check_failed_saying(self, expected: str) -> None:
        """The tally, the charged test, and the sentence -- all three or none.

        The arming check is the only test in the probe, so anything else in the
        FAILURES section means the child broke before it ran.

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
        self._assert_the_failure_was_charged_to(
            {ARMING_PROBE_TEST_NAME}, expected, NOT_THE_DISARMED_ENVIRONMENT
        )
