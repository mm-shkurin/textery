import pytest

from statements.arming_probe_roster_statements import ArmingProbeRosterStatements
from statements.disarmed_arming_probe_statements import DisarmedArmingProbeStatements


class TestDisarmedArmingProbe:
    """The guard that asserts this run is armed must itself be shown to bite.

    Given a child pytest whose runner environment disarms the declared filters
    When the live arming check runs inside it
    Then the child fails, naming the vector that disarmed it -- while the same
      check under an untouched environment passes

    None of the three checks `LiveHarnessConfigurationStatements` runs had ever
    executed on its failing side, and no report could say so. The evidence that they
    bite was a terminal session; this is that session, written down as three tests
    and a control.

    One vector per arm, and they cannot be pooled. Why -- and why the third vector is
    the only one that has to pass the first two checks honestly to be judged by the
    third -- is in `DisarmedArmingProbeStatements`.
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

    def test_should_fail_the_arming_check_when_a_runner_env_rewrites_the_declaration(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        disarmed_arming_probe_statements.given_a_runner_environment_that_rewrites_the_declaration()
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        disarmed_arming_probe_statements.assert_the_projects_own_configuration_was_in_force()
        disarmed_arming_probe_statements.assert_the_arming_check_refused_the_rewritten_declaration()

    @pytest.mark.skip(
        reason="RED: AttributeError -- DisarmedArmingProbeStatements has no "
        "given_a_runner_environment_that_unloads_the_unraisable_plugin; the vector, "
        "its refusal sentence and a probe that calls the fourth arm do not exist yet"
    )
    def test_should_fail_the_arming_check_when_a_runner_env_unloads_the_unraisable_plugin(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        """The fourth arm, and the only one that lives outside the three-check sequence.

        `assert_the_unraisable_plugin_is_loaded_in_this_run` is a sibling of the
        three arms rather than one of them, so none of the three vectors above
        reaches it: its `assert loaded is True` has never failed in any process, and
        being a bare `assert` it will never be reported as a coverage gap either.

        `-p no:unraisableexception` is the vector its own message names, and it is
        the one that passes all three earlier checks honestly -- nothing lands in
        `pythonwarnings`, the ini declaration is untouched so a provoked
        RuntimeWarning still raises, and the two required entries are both still
        there. What it removes is the plugin that turns a swallowed destructor
        exception into a `PytestUnraisableExceptionWarning` at all, so the second
        entry matches nothing and the forgotten-await guard is disarmed with every
        line of configuration intact.
        """
        disarmed_arming_probe_statements.given_a_runner_environment_that_unloads_the_unraisable_plugin()
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        disarmed_arming_probe_statements.assert_the_projects_own_configuration_was_in_force()
        disarmed_arming_probe_statements.assert_the_arming_check_refused_the_unloaded_unraisable_plugin()

    def test_should_pass_the_arming_check_when_the_runner_environment_leaves_it_alone(
        self, tmp_path, disarmed_arming_probe_statements: DisarmedArmingProbeStatements
    ):
        disarmed_arming_probe_statements.given_a_runner_environment_that_leaves_the_suite_armed()
        disarmed_arming_probe_statements.given_the_live_arming_check_as_the_probe(tmp_path)

        disarmed_arming_probe_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        disarmed_arming_probe_statements.assert_the_projects_own_configuration_was_in_force()
        disarmed_arming_probe_statements.assert_the_arming_check_passed_under_an_armed_environment()


class TestDisarmedArmingProbeArrangement:
    """This family keeps its ambient environment, so it must be told which one to keep.

    Given the live arming check staged as the probe and no runner environment chosen
    When the probe run is asked for
    Then it refuses, naming the arrangement that was never made

    `DisarmedArmingProbeStatements` opts the whole class into
    `keep_ambient_environment=True`, while the compensating scrub lives in
    `_disarm_the_child_with_only`, reachable only through the four `given_a_runner_
    environment_*` steps. Nothing in that arrangement couples "this child keeps its
    environment" to "a vector was deliberately chosen"; the guard in
    `KeptAmbientChildBase` is what couples them, and this test is what holds it
    there. Without it the third arming-arm test above could have been written
    without a `given_` step, passed on a clean laptop, and failed on a runner that
    exports `PYTEST_ADDOPTS`, diagnosing the harness rather than the runner -- and
    that is not a hypothesis: it is the shape that test would have taken had this
    guard not already been here, and the shape any fourth arm would take next.

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


@pytest.mark.skip(
    reason="RED: the roster expectations name the fourth vector first -- "
    "arming_probe.py is missing UNLOADED_UNRAISABLE_PLUGIN and "
    "EXPECTED_UNLOADED_UNRAISABLE_PLUGIN_REFUSAL, and no given_ step drives it"
)
class TestArmingProbeRoster:
    """A vector added to this family must be driven, not merely declared.

    Given the probe module's declared constants and the steps that spend them
    When the roster is read off the module rather than transcribed from it
    Then it is exactly the known names, and every vector is named by a `given_` step

    Each constant in `arming_probe.py` is referenced from a single place in
    `DisarmedArmingProbeStatements`, and until now nothing compared the roster
    whole -- so a fourth vector would have been driven by no test and flagged by no
    report. Why that is this family's own history rather than a worry about it, and
    why the roster is discovered rather than transcribed, is in
    `ArmingProbeRosterStatements`.
    """

    def test_should_declare_exactly_the_known_probe_constants(
        self, arming_probe_roster_statements: ArmingProbeRosterStatements
    ):
        arming_probe_roster_statements.assert_the_probe_module_declares_exactly_the_known_roster()

    def test_should_spend_every_declared_vector_on_a_given_step(
        self, arming_probe_roster_statements: ArmingProbeRosterStatements
    ):
        arming_probe_roster_statements.assert_every_declared_vector_is_spent_on_a_given_step()
