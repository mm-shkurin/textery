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

import pytest

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
        """The whole list, in order -- not "both entries are somewhere in it".

        A containment check is satisfied by the state this assertion exists to
        reject. `filterwarnings` is applied in sequence and the *last* matching
        entry wins, so a runner that appends `ignore::RuntimeWarning` via
        `PYTEST_ADDOPTS` leaves both required entries present, nothing missing, and
        the suite disarmed. Whole-list equality means an appended entry has to be
        added to the constant deliberately.
        """
        actual = list(self._config.getini("filterwarnings"))
        assert actual == REQUIRED_FILTERWARNINGS, (
            f"this run's `filterwarnings` is {actual}, expected exactly "
            f"{REQUIRED_FILTERWARNINGS} -- the gate that proves the entries work runs a child "
            f"with the ambient overrides scrubbed, so it stays green while a runner env "
            f"disarms the suite CI actually executes. Both entries are required, and no "
            f"third one may follow them: the last matching filter wins, so an appended "
            f"`ignore::RuntimeWarning` overrides both while leaving both present"
        )

    def assert_the_unraisable_plugin_is_loaded_in_this_run(self) -> None:
        loaded = self._config.pluginmanager.hasplugin(UNRAISABLE_PLUGIN_NAME)
        assert loaded is True, (
            f"pytest's '{UNRAISABLE_PLUGIN_NAME}' plugin is not loaded in this run, so no "
            f"PytestUnraisableExceptionWarning is ever raised and the second filter entry "
            f"matches nothing. `-p no:{UNRAISABLE_PLUGIN_NAME}` in PYTEST_ADDOPTS disarms the "
            f"forgotten-await guard without touching a line of configuration"
        )
