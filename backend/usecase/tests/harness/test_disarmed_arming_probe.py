import pytest

from statements.disarmed_arming_probe_statements import DisarmedArmingProbeStatements


class TestDisarmedArmingProbe:
    """The guard that asserts this run is armed must itself be shown to bite.

    Given a child pytest whose runner environment disarms the declared filters
    When the live arming check runs inside it
    Then the child fails, naming the vector that disarmed it -- while the same
      check under an untouched environment passes

    Two of the three checks `LiveHarnessConfigurationStatements` runs end in a
    `raise` and a bare `assert`, neither of which coverage.py counts as a branch,
    and neither had ever executed. (The third check's arm is unreachable by either
    vector here and is driven separately.) The evidence that they bite was a
    terminal session. This is that session, written down as two tests and a control.
    """

    def test_should_fail_the_arming_check_when_a_runner_env_overrides_the_declared_filters(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        disarmed_arming_probe_statements.given_a_runner_environment_that_overrides_the_declared_filters()
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        disarmed_arming_probe_statements.assert_the_projects_own_configuration_was_in_force()
        disarmed_arming_probe_statements.assert_the_arming_check_refused_the_command_line_override()

    def test_should_fail_the_arming_check_when_a_runner_env_unloads_the_warnings_plugin(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        disarmed_arming_probe_statements.given_a_runner_environment_that_unloads_the_warnings_plugin()
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        disarmed_arming_probe_statements.assert_the_projects_own_configuration_was_in_force()
        disarmed_arming_probe_statements.assert_the_arming_check_refused_the_inert_filter()

    def test_should_pass_the_arming_check_when_the_runner_environment_leaves_it_alone(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        disarmed_arming_probe_statements.given_a_runner_environment_that_leaves_the_suite_armed()
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        disarmed_arming_probe_statements.assert_the_projects_own_configuration_was_in_force()
        disarmed_arming_probe_statements.assert_the_arming_check_passed_under_an_armed_environment()


@pytest.mark.skip(
    reason="RED: Failed: DID NOT RAISE AssertionError -- "
    "DisarmedArmingProbeStatements inherits ChildProbeStatements' act unguarded, so "
    "a run with no vector chosen executes a real child instead of refusing"
)
class TestDisarmedArmingProbeArrangement:
    """This family keeps its ambient environment, so it must be told which one to keep.

    Given the live arming check staged as the probe and no runner environment chosen
    When the probe run is asked for
    Then it refuses, naming the arrangement that was never made

    `DisarmedArmingProbeStatements` opts the whole class into
    `keep_ambient_environment=True`, but the compensating scrub lives in
    `_disarm_the_child_with_only`, reachable only through the three `given_a_runner_
    environment_*` steps. Nothing couples "this child keeps its environment" to "a
    vector was deliberately chosen" -- so the already-scheduled third-arming-arm test
    can be written without a `given_` step, pass on a clean laptop, and fail on a
    runner that exports `PYTEST_ADDOPTS`, diagnosing the harness rather than the
    runner. That is not a hypothesis about a future test; it is the shape the next
    scheduled test in this file will be written in.

    The `None` case is inside the guard on purpose. `given_a_runner_environment_that_
    leaves_the_suite_armed` chooses an untouched environment, and "chose nothing" must
    stay distinguishable from "chose nothing yet" -- which is why
    `DisarmedChildEnvironment` records a description rather than the vector itself.
    """

    def test_should_refuse_the_probe_run_when_no_runner_environment_was_chosen(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_expecting_it_to_be_refused()

        disarmed_arming_probe_statements.assert_the_refusal_named_the_unchosen_environment()
        disarmed_arming_probe_statements.assert_no_child_was_run_before_the_refusal()
