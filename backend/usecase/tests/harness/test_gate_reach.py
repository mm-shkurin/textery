import pytest

from statements.gate_reach_statements import GateReachStatements


class TestGateReach:
    """What the forgotten-await gate proves must be bounded by assertions, not prose.

    Given the gate's own child-run machinery
    When a conftest sits above the probe, a probe is aimed inside the repository,
      or a leak in one test is followed by a clean one
    Then the conftest walk stops at the probe, the write is refused, and the leak
      is charged to the test that committed it

    Three separate claims the gate makes in docstrings and nowhere in code. The
    first two are about where the child may look and where the probe may be
    written; the third is about a failure class the second `filterwarnings` entry
    introduced -- an unraisable fires at collection time, so it can be charged to a
    test that then passes in isolation.
    """

    @pytest.mark.skip(reason="RED: pinning --confcutdir on the child is GREEN's")
    def test_should_not_load_a_conftest_from_above_the_probe_directory(
        self, tmp_path, gate_reach_statements: GateReachStatements
    ):
        gate_reach_statements.given_a_conftest_above_the_probe_directory(tmp_path)

        gate_reach_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        gate_reach_statements.assert_the_projects_own_configuration_was_in_force()
        gate_reach_statements.assert_the_poisoned_conftest_was_never_imported()
        gate_reach_statements.assert_the_probe_suite_failed()
        gate_reach_statements.assert_the_failure_named_the_unawaited_coroutine()

    @pytest.mark.skip(reason="RED: refusing an in-tree probe path is GREEN's")
    def test_should_refuse_to_write_a_probe_inside_the_repository(
        self, gate_reach_statements: GateReachStatements
    ):
        gate_reach_statements.try_to_write_a_probe_inside_the_repository()

        gate_reach_statements.assert_the_write_was_refused_before_it_landed()

    def test_should_charge_an_unawaited_coroutine_to_the_test_that_dropped_the_await(
        self, tmp_path, gate_reach_statements: GateReachStatements
    ):
        gate_reach_statements.given_a_probe_whose_leak_is_in_one_test_and_whose_next_test_is_clean(
            tmp_path
        )

        gate_reach_statements.run_the_probe_under_the_projects_own_pytest_configuration()

        gate_reach_statements.assert_the_projects_own_configuration_was_in_force()
        gate_reach_statements.assert_one_test_failed_and_the_other_passed()
        gate_reach_statements.assert_the_leak_was_reported_against_the_test_that_leaked()
