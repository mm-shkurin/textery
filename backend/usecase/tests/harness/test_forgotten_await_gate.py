import pytest

from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements


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

    @pytest.mark.skip(
        reason="RED: filterwarnings matches error::RuntimeWarning, but the forgotten await "
        "surfaces as pytest.PytestUnraisableExceptionWarning -- the probe run passes"
    )
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
