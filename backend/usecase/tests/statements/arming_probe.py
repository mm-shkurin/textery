"""The probe module the disarmed-arming family runs, its vectors and its sentences.

Kept apart from the Statements that runs it, the way `forgotten_await_probes.py` is
kept apart from `ForgottenAwaitGateStatements`: neither file then has to carry both
the source of a test suite and the machinery for reading one.
"""

# The probe's single test. Named rather than reused from the forgotten-await
# family: the FAILURES section is compared as a whole set of names, so the name is
# an assertion expectation and must belong to this probe alone.
ARMING_PROBE_TEST_NAME = "test_the_live_arming_check_runs_here"

# The subject, invoked exactly as the real suite invokes it -- through the public
# statement, from a `pytestconfig` that is the child's own. A probe that
# constructed a `Config` by hand would assert on a fabrication.
ARMING_PROBE = f"""
from statements.live_harness_configuration_statements import (
    LiveHarnessConfigurationStatements,
)


def {ARMING_PROBE_TEST_NAME}(pytestconfig) -> None:
    LiveHarnessConfigurationStatements(
        pytestconfig
    ).assert_both_filter_entries_are_in_force_in_this_run()
"""

# The two disarming vectors. The variable they ride in is `DisarmedChildEnvironment`'s
# `RUNNER_OVERRIDE_VARIABLE`, along with the scrub that has to precede it.
COMMAND_LINE_FILTER_OVERRIDE = "-W ignore::RuntimeWarning"
UNLOADED_WARNINGS_PLUGIN = "-p no:warnings"

# What each arm must say when it bites. Literals rather than imports from the
# module under test: read back from it, the assertion would still pass with both
# messages rewritten to the empty string, and the whole point of these two arms is
# that a reader meeting them in CI is told which vector disarmed the suite.
#
# The override refusal carries the parsed filter list, so this pins that the
# override genuinely reached the child rather than that the message merely fired.
EXPECTED_OVERRIDE_REFUSAL = (
    "this run carries command-line warning filters ['ignore::RuntimeWarning']"
)
EXPECTED_INERT_FILTER_REFUSAL = "a RuntimeWarning raised in this very run did not fail it"

# What a run whose FAILURES section lacks the expected sentence actually means.
# Both arms are a `raise` and an `assert` that coverage.py does not count as
# branches, so the sentence is the only evidence the arm executed at all.
NOT_THE_DISARMED_ENVIRONMENT = "the arming check failed, but not for the disarmed environment"
