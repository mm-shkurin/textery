from statements.live_harness_configuration_statements import LiveHarnessConfigurationStatements


class TestLiveHarnessConfiguration:
    """The suite that is running must itself be armed, not only the file it reads.

    Given the pytest configuration of this very run
    When its warning filters and loaded plugins are read
    Then both required filter entries are in force and the unraisable plugin is loaded

    The forgotten-await gate proves what `pyproject.toml` declares, from a child
    with `PYTHONWARNINGS`, `PYTEST_ADDOPTS` and the plugin-autoload switch scrubbed
    -- which is exactly why it can say nothing about the parent. A runner env that
    ignores RuntimeWarning, or that deselects the unraisable plugin, leaves the
    gate green and the real suite unarmed. This is the one assertion the
    child-process shape structurally cannot make.
    """

    def test_should_run_this_suite_with_both_forgotten_await_filter_entries_in_force(
        self, live_harness_configuration_statements: LiveHarnessConfigurationStatements
    ):
        live_harness_configuration_statements.assert_both_filter_entries_are_in_force_in_this_run()

    def test_should_run_this_suite_with_the_unraisable_exception_plugin_loaded(
        self, live_harness_configuration_statements: LiveHarnessConfigurationStatements
    ):
        live_harness_configuration_statements.assert_the_unraisable_plugin_is_loaded_in_this_run()
