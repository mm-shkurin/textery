import pytest

from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements

# Two ambient states, each *measured* to disarm this gate on its own when the
# child is allowed to keep them, and each by a different mechanism: a command-line
# `-W` filter is applied after the ini entries and the last matching filter wins,
# while `-p no:unraisableexception` unloads the plugin that turns the destructor's
# swallowed RuntimeWarning into a warning at all, so the second ini entry matches
# nothing. Both were driven by hand against the real `pyproject.toml`: probe exit 1
# with the environment clean, exit 0 with either one set.
#
# `PYTHONWARNINGS=ignore::RuntimeWarning` is deliberately *not* in this list. It
# reads like the obvious vector and it is inert here -- measured, not assumed:
# pytest applies its own ini `filterwarnings` after the ones it inherits from
# `PYTHONWARNINGS`, so the probe still fails (exit 1) with it set, and a test
# carrying only that variable would be green in every state including the one it
# exists to reject.
HOSTILE_RUNNER_ENVIRONMENTS = [
    ("PYTEST_ADDOPTS", "-W ignore::RuntimeWarning"),
    ("PYTEST_ADDOPTS", "-p no:unraisableexception"),
]


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
        watched it: before this test, `LEAKY_CHILD_VARIABLES` and
        `_child_environment` were each referenced exactly once in the whole backend
        tree -- the definition and its single use. No test set a hostile variable and
        required the gate to bite, so the scrub was proven only by developer and CI
        shells happening to be clean, which is the assumption it exists to remove.

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
