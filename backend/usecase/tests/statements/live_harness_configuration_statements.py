"""What the running suite decided, as opposed to what `pyproject.toml` declares.

The forgotten-await gate asserts the declaration: it runs a child pointed at this
repository's configuration file with the ambient overrides scrubbed, and proves
that file fails a forgotten `await`. That is the strongest thing a child process
can say, and it is structurally unable to say anything about the parent -- the
suite CI actually runs. `PYTHONWARNINGS=ignore::RuntimeWarning` in a runner's
environment, a `-p no:unraisableexception` in `PYTEST_ADDOPTS`, or a plugin that
resets filters at session start all leave the gate green and the real suite
unarmed, because the gate deliberately takes exactly those things away from its
child.

So the parent asserts on itself, through the `config` object pytest built for
this very run. Two things, because either alone is insufficient: the filter
entries must be present, and the plugin that turns an unraisable exception into a
warning at all must be loaded -- without it there is no
`PytestUnraisableExceptionWarning` for the second entry to promote, and the first
entry alone was already proven insufficient.
"""

import warnings

import pytest

# What the behavioural half emits. Distinct prose so a reader meeting it in a
# traceback knows the warning was raised on purpose by the arming check.
ARMING_PROBE_MESSAGE = "the live harness arming probe's RuntimeWarning"

# The two entries, written out rather than read from the file being checked. The
# order is the order they must appear in: `filterwarnings` is applied in sequence
# and a reader comparing the two lists needs a stable expectation.
REQUIRED_FILTERWARNINGS = [
    "error::RuntimeWarning",
    "error::pytest.PytestUnraisableExceptionWarning",
]

# pytest's built-in plugin that catches `sys.unraisablehook` and re-raises the
# swallowed destructor exception as a warning. Named by the string pytest
# registers it under.
UNRAISABLE_PLUGIN_NAME = "unraisableexception"


class LiveHarnessConfigurationStatements:
    """Assert on the configuration of the run that is executing this assertion."""

    def __init__(self, config: pytest.Config) -> None:
        self._config = config

    def assert_both_filter_entries_are_in_force_in_this_run(self) -> None:
        """Three readings, because the declaration alone is not the effective state.

        `getini("filterwarnings")` returns the *ini* declaration and nothing else.
        `PYTEST_ADDOPTS="-W ignore::RuntimeWarning"` is parsed into command-line
        filters, which land in `config.option.pythonwarnings` and are applied
        *after* the ini entries -- so they win while `getini` still reads exactly
        the two required entries. Measured in this repository: under that env the
        two live-config tests reported 2 passed while a RuntimeWarning probe went
        from 1 failed to 1 passed. The suite was disarmed with the guard green.

        So the command-line override is refused, then the actual behaviour is
        provoked, and only then is the declaration pinned. That order is the
        diagnostic one: the effective state is what a reader needs told first, and
        provoking it also covers a `-W` smuggled into `addopts` inside
        `pyproject.toml`, which neither of the other two can see.
        """
        self._assert_no_command_line_filter_overrides_the_declaration()
        self._assert_a_runtime_warning_actually_raises()
        self._assert_the_declaration_is_exactly_the_required_entries()

    def _assert_the_declaration_is_exactly_the_required_entries(self) -> None:
        actual = list(self._config.getini("filterwarnings"))
        assert actual == REQUIRED_FILTERWARNINGS, (
            f"this run's `filterwarnings` is {actual}, expected exactly "
            f"{REQUIRED_FILTERWARNINGS} -- the gate that proves the entries work runs a child "
            f"with the ambient overrides scrubbed, so it stays green while a runner env "
            f"disarms the suite CI actually executes. Both entries are required, and no "
            f"third one may follow them: the last matching filter wins, so an appended "
            f"`ignore::RuntimeWarning` overrides both while leaving both present"
        )

    def _assert_no_command_line_filter_overrides_the_declaration(self) -> None:
        overrides = list(getattr(self._config.option, "pythonwarnings", None) or [])
        assert overrides == [], (
            f"this run carries command-line warning filters {overrides}. `-W` filters are "
            f"applied after the ini `filterwarnings` entries and the last matching filter "
            f"wins, so these override the declaration while `getini` still reads exactly the "
            f"two required entries -- the shape a `PYTEST_ADDOPTS` in a runner env produces"
        )

    def _assert_a_runtime_warning_actually_raises(self) -> None:
        """The effective state, provoked rather than read off a config object.

        Whatever combination of ini entries, `-W` filters and session-time plugin
        meddling this run ended up with, the only claim that matters is that the
        forgotten-`await` warning class still stops a test. So one is emitted.
        """
        try:
            warnings.warn(ARMING_PROBE_MESSAGE, RuntimeWarning, stacklevel=2)
        except RuntimeWarning:
            return
        raise AssertionError(
            "a RuntimeWarning raised in this very run did not fail it -- so a forgotten "
            "`await` warns and passes here, whatever the configuration files declare. The "
            "gate that proves the entries work runs a child with the ambient overrides "
            "scrubbed, and stays green through exactly this"
        )

    def assert_the_unraisable_plugin_is_loaded_in_this_run(self) -> None:
        loaded = self._config.pluginmanager.hasplugin(UNRAISABLE_PLUGIN_NAME)
        assert loaded is True, (
            f"pytest's '{UNRAISABLE_PLUGIN_NAME}' plugin is not loaded in this run, so no "
            f"PytestUnraisableExceptionWarning is ever raised and the second filter entry "
            f"matches nothing. `-p no:{UNRAISABLE_PLUGIN_NAME}` in PYTEST_ADDOPTS disarms the "
            f"forgotten-await guard without touching a line of configuration"
        )
