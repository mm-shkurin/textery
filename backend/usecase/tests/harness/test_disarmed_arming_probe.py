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
