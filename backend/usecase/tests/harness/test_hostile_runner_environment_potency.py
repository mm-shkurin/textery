import pytest

from statements.disarmed_forgotten_await_probe_statements import (
    DisarmedForgottenAwaitProbeStatements,
)
from statements.hostile_runner_environments import HOSTILE_RUNNER_ENVIRONMENTS


class TestHostileRunnerEnvironmentPotency:
    """Each vector the scrub test relies on must be shown to actually disarm the gate.

    Given the forgotten-await probe and a child that keeps its ambient environment
    When the probe is run under one of the hostile vectors
    Then the child passes -- the forgotten `await` went entirely unnoticed

    The armed control for `TestForgottenAwaitGate`, and its mirror: there the gate
    must bite through the vector, here the vector must be strong enough that the
    gate cannot. Without this pair, both vectors could quietly become inert -- a
    pytest that reordered `-W` application, or folded `unraisableexception` into
    the core -- and the scrub test would keep passing while watching nothing. Their
    potency was otherwise a terminal session recorded in a comment.

    The pairing is load-bearing in the other direction too: `{passed: 1}` on its
    own is also what a probe that never leaked a coroutine would report. What makes
    this a measurement of the *vector* is that both classes parametrise over the
    same `HOSTILE_RUNNER_ENVIRONMENTS` and stage the same `FORGOTTEN_AWAIT_PROBE`,
    so the environment is the only difference between a run that fails and this one.
    """

    @pytest.mark.parametrize(("variable", "value"), HOSTILE_RUNNER_ENVIRONMENTS)
    def test_should_let_the_forgotten_await_probe_pass_when_the_child_keeps_the_hostile_vector(
        self,
        tmp_path,
        variable,
        value,
        disarmed_forgotten_await_probe_statements: DisarmedForgottenAwaitProbeStatements,
    ):
        statements = disarmed_forgotten_await_probe_statements
        statements.given_a_runner_environment_carrying_only(variable, value)
        statements.given_a_call_site_that_forgets_to_await_an_async_given_step(tmp_path)

        statements.run_the_probe_under_the_projects_own_pytest_configuration()

        statements.assert_the_projects_own_configuration_was_in_force()
        statements.assert_the_gate_was_disarmed_by_the_vector()


class TestDisarmedForgottenAwaitProbeArrangement:
    """This family keeps its ambient environment, so it must be told which one to keep.

    Given the forgotten-await probe staged and no runner environment chosen
    When the probe run is asked for
    Then it refuses, naming the arrangement that was never made

    Two assertions, because the message and the short-circuit are separable states
    and only the second is the point: a guard that ran the child, read its report and
    only then noticed the unchosen environment raises the identical sentence while
    having already paid the whole cost the guard exists to avoid.

    Green from the day it was written, and that is the point: the guard exists in
    `DisarmedForgottenAwaitProbeStatements` and nothing watched it. The sibling
    family got this test as a RED; here the coupling is already in place, so this
    is the armed control that stops a later refactor from deleting the override --
    a class that keeps its ambient environment and forgot its `given_` step is
    green on a clean laptop and red on a runner that exports `PYTEST_ADDOPTS`,
    diagnosing the harness rather than the runner.
    """

    def test_should_refuse_the_probe_run_when_no_runner_environment_was_chosen(
        self,
        tmp_path,
        disarmed_forgotten_await_probe_statements: DisarmedForgottenAwaitProbeStatements,
    ):
        statements = disarmed_forgotten_await_probe_statements
        statements.given_a_call_site_that_forgets_to_await_an_async_given_step(tmp_path)

        statements.run_the_probe_expecting_it_to_be_refused()

        statements.assert_the_refusal_named_the_unchosen_environment()
        statements.assert_no_child_was_run_before_the_refusal()
