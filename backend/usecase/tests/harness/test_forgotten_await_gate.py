import pytest

from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements
from statements.hostile_runner_environments import HOSTILE_RUNNER_ENVIRONMENTS


class TestForgottenAwaitGate:
    """A call site that forgets to `await` an async given_ step must fail the suite.

    Given a probe module whose test calls an async arrangement step without `await`
    When the probe is run under this repository's own pytest configuration
    Then the run reports a failure naming the coroutine that was never awaited

    This is the guard on a guard. `pyproject.toml` declares a `filterwarnings`
    entry whose entire purpose is to make that mistake fail rather than warn, and
    nothing in the suite notices if the entry is wrong, removed, or aimed at a
    warning class the interpreter never raises -- a harness claim cannot be driven
    red from inside the harness it claims to fix. Asserted from a child process so
    the probe's own failure is the subject rather than this suite's outcome.
    """

    def test_should_fail_the_run_when_a_call_site_forgets_to_await_an_async_given_step(
        self, tmp_path, forgotten_await_gate_statements: ForgottenAwaitGateStatements
    ):
        forgotten_await_gate_statements.given_a_call_site_that_forgets_to_await_an_async_given_step(
            tmp_path
        )

        forgotten_await_gate_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        forgotten_await_gate_statements.assert_the_projects_own_configuration_was_in_force()
        forgotten_await_gate_statements.assert_the_probe_suite_failed()
        forgotten_await_gate_statements.assert_the_failure_named_the_unawaited_coroutine()

    def test_should_leave_a_correctly_awaited_given_step_passing(
        self, tmp_path, forgotten_await_gate_statements: ForgottenAwaitGateStatements
    ):
        forgotten_await_gate_statements.given_a_call_site_that_awaits_the_async_given_step(tmp_path)

        forgotten_await_gate_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        forgotten_await_gate_statements.assert_the_projects_own_configuration_was_in_force()
        forgotten_await_gate_statements.assert_the_probe_suite_passed()
        forgotten_await_gate_statements.assert_nothing_was_left_unawaited_on_the_control()

    @pytest.mark.parametrize(("variable", "value"), HOSTILE_RUNNER_ENVIRONMENTS)
    def test_should_still_fail_the_forgotten_await_probe_when_the_runner_environment_ignores_runtime_warnings(  # noqa: E501
        self,
        tmp_path,
        monkeypatch,
        variable,
        value,
        forgotten_await_gate_statements: ForgottenAwaitGateStatements,
    ):
        """The scrub itself, watched -- and it is watched because it stopped being total.

        `ChildPytestRun` used to strip `LEAKY_CHILD_VARIABLES` from every child
        unconditionally; it now takes an opt-in that keeps them, for the one family
        whose subject is a hostile runner environment. From that change on, "does
        *this* gate's child get scrubbed?" is a per-call-site decision, and nothing
        watched it: before this test, no assertion anywhere in the backend tree read
        `LEAKY_CHILD_VARIABLES` or `_child_environment` at all -- the constant had its
        definition and its single use inside `ChildPytestRun`, and nothing else. No
        test set a hostile variable and required the gate to bite, so the scrub was
        proven only by developer and CI shells happening to be clean, which is the
        assumption it exists to remove.

        This test remains a *partial* witness and should not be read as more. It can
        only watch entries for which a disarming vector exists, and both of its
        parametrisations drive `PYTEST_ADDOPTS`; four of the roster's entries could be
        deleted with this file staying green. `test_child_environment_scrub.py`
        asserts on the built environment directly and is the pin on the roster itself;
        `test_hostile_runner_environment_potency.py` is what keeps the two vectors
        below from quietly becoming no-ops and leaving this test green over nothing.

        An opt-in threaded through the shared base, or a later refactor collapsing
        the two constructors, would un-arm the forgotten-await gate while every
        harness test stayed green -- and the loss would stay invisible until someone
        forgot an `await` for real. This test is green today and goes red the instant
        the scrub stops applying to this family.

        Both vectors were driven by hand before being written down, and a flipped
        default was then run as a negative control: flipping
        `ChildProbeStatements.__init__`'s default to True turns both parametrisations
        red. Flipping `ChildPytestRun.__init__`'s default does *not* -- measured, not
        assumed. That default is unobservable: `ChildProbeStatements` is its only
        instantiator and always passes the argument explicitly, so the base's own
        default is dead and this test cannot see it change. What is watched is the
        one default a family actually inherits.
        """
        forgotten_await_gate_statements.given_a_hostile_runner_environment(
            monkeypatch, variable, value
        )
        forgotten_await_gate_statements.given_a_call_site_that_forgets_to_await_an_async_given_step(
            tmp_path
        )

        forgotten_await_gate_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        forgotten_await_gate_statements.assert_the_projects_own_configuration_was_in_force()
        forgotten_await_gate_statements.assert_the_probe_suite_failed()
        forgotten_await_gate_statements.assert_the_failure_named_the_unawaited_coroutine()
