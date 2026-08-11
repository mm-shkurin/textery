"""The probe module the disarmed-arming family runs, its vectors and its sentences.

Kept apart from the Statements that runs it, the way `forgotten_await_probes.py` is
kept apart from `ForgottenAwaitGateStatements`: neither file then has to carry both
the source of a test suite and the machinery for reading one.
"""

# Imported as a module rather than `from typing import NamedTuple`: the roster guard
# discovers this module's public names with `vars()` and sees through imports only
# when they are modules, so a bare name bound here would read as an unclassified
# roster entry. See `ArmingProbeRosterStatements._declared_names`.
import typing

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

# The two vectors that trip the first two arms. They ride in
# `DisarmedChildEnvironment`'s `RUNNER_OVERRIDE_VARIABLE`, along with the scrub that has
# to precede it. The third vector, which has to survive both of these to be judged by
# the arm it is for, is below.
COMMAND_LINE_FILTER_OVERRIDE = "-W ignore::RuntimeWarning"
UNLOADED_WARNINGS_PLUGIN = "-p no:warnings"

# The only vector that reaches the declaration check. `-o` rewrites the ini value itself
# rather than layering a command-line filter over it, so `config.option.pythonwarnings`
# stays empty (check one passes) and the surviving `error::RuntimeWarning` still promotes
# the provoked warning (check two passes) -- leaving the declaration, now a list of one,
# as the only thing left to be wrong about.
REWRITTEN_FILTER_DECLARATION = "-o filterwarnings=error::RuntimeWarning"

class ArmRefusal(typing.NamedTuple):
    """The two clauses an arm's failure must carry, required by construction.

    A plain 2-tuple left the pairing to prose. Every docstring that consumes these
    says both halves are required, but the shared assertion helper only refuses an
    *empty* sequence -- so a rewrite that dropped `observed` left a 1-tuple that
    still read as an expectation and still passed, which is the exact "one half free
    to be emptied" failure those docstrings warn about. Named fields also stop the
    two from being read positionally at the four sites that consume them.
    """

    observed: str
    reasoning: str


# What each arm must say when it bites. Literals rather than imports from the
# module under test: read back from it, the assertion would still pass with all three
# messages rewritten to the empty string, and the whole point of these three arms is
# that a reader meeting them in CI is told which vector disarmed the suite.
#
# Each expectation is a *pair*: the clause carrying the value the arm actually observed,
# and the clause carrying its reasoning. The observed half is what makes the failure
# attributable to this vector rather than to the arm having fired for any reason at all;
# the reasoning half is what a reader meeting it in CI cannot reconstruct. Pinning only
# one leaves the other free to be emptied, so both are required.
EXPECTED_OVERRIDE_REFUSAL = ArmRefusal(
    observed="this run carries command-line warning filters ['ignore::RuntimeWarning']",
    reasoning="these override the declaration while `getini` still reads exactly the",
)
EXPECTED_INERT_FILTER_REFUSAL = ArmRefusal(
    observed="a RuntimeWarning raised in this very run did not fail it",
    reasoning="so a forgotten `await` warns and passes here, whatever the configuration files",
)

# The declaration refusal, whose arm no reader had seen before this family: until the
# third vector above, it had never failed in any process. The observed half pins the
# list `-o filterwarnings=error::RuntimeWarning` actually leaves behind -- without it the
# arm is satisfied by a declaration wrong for some unrelated reason, and the vector's
# potency goes unwatched. The reasoning half is the longest clause in the file, and the
# one an appended-entry regression turns on: both required entries stay present and the
# appended one still wins.
EXPECTED_REWRITTEN_DECLARATION_REFUSAL = ArmRefusal(
    observed="this run's `filterwarnings` is ['error::RuntimeWarning'], expected exactly",
    reasoning="no third one may follow them: the last matching filter wins, so an appended "
    "`ignore::RuntimeWarning` overrides both while leaving both present",
)

# What a run whose FAILURES section lacks an expected sentence actually means: the
# check failed for something other than the vector this family chose. Why the
# sentence is the only available evidence that an arm executed is recorded with the
# arms, in `DisarmedArmingProbeStatements`.
NOT_THE_DISARMED_ENVIRONMENT = "the arming check failed, but not for the disarmed environment"
