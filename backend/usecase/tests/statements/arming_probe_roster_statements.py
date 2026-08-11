"""What stops a fourth vector from joining this family unwatched.

`arming_probe.py` is a roster: the disarming vectors and the sentences each arm
must say. Each is referenced from a single place in `DisarmedArmingProbeStatements`
-- the vectors from their own `given_` steps, the refusal sentences from their own
`assert_` steps, and `ARMING_PROBE_TEST_NAME` and `NOT_THE_DISARMED_ENVIRONMENT`
from the one private helper those `assert_` steps share -- and nothing anywhere
compares the roster as a whole. So a constant added to that file is driven by no
test, asserted by no test, and reported by nothing: it simply sits there, and the
suite stays green.

That is not hypothetical for this family, it is its history: the third arm's vector
sat in a module docstring as "scheduled separately" for the whole life of the file,
driven by nothing and reported by nothing. Why coverage could not find it is with
the arms themselves, in `DisarmedArmingProbeStatements`.

The fourth arm this file was written to anticipate is now driven:
`assert_the_unraisable_plugin_is_loaded_in_this_run` sits outside
`assert_both_filter_entries_are_in_force_in_this_run`, its `assert loaded is True`
has never failed in any process, and its own message names the
`-p no:unraisableexception` that drives it. The expectations below were written
first and the vector was added to satisfy them, which is the order this file exists
to enforce.

So the roster is **discovered** from the module rather than transcribed from it,
and pinned against hand-written literal names. Transcribed, the expectation would
widen with the thing it guards -- the `dataclasses.fields()` lesson this story has
now learned three times -- and adding a constant to both places at once is exactly
what an author adding a constant does. Discovery means the addition is red until
someone writes the test that drives it, which is the whole point. The discovery
itself lives in `ArmingProbeRosterReader`, so a repair cannot be applied to what is
read instead of to what is expected.

Names only, deliberately. Repeating the sentences would put a second copy of each in
the repository free to drift from the first. What is unwatched is the *membership* of
the roster, and that is what this pins.

One entry is named here whose *value* nothing pins, and the exception is recorded
rather than glossed: `NOT_THE_DISARMED_ENVIRONMENT` reaches its only consumer as
`_assert_the_failure_was_charged_to`'s `because` argument -- a failure-message
clause, never an expected value -- so it could be rewritten to the empty string with
the suite green. Its membership is guarded here; its text is guarded nowhere. Every
other entry is pinned by the test that consumes it.
"""

from statements.arming_probe_roster_reader import ArmingProbeRosterReader

# The roster is declared as a *partition* rather than as one flat list beside a
# second copy of the vectors. Flat, the two sets were independent hand-written
# literals, and the repair an author reaches for when the membership guard reddens
# -- add the new name to the roster -- turned that guard green while leaving the
# linkage guard below blind to the new vector for good. That is the same shape as
# the third vector sitting undriven in a docstring for the file's whole life, which
# is what this file exists to make impossible. Partitioned, a name cannot enter the
# roster without being classified, and classifying it as a vector is what puts it in
# front of the linkage guard.
#
# The union is derived; every *name* is still a hand-written literal. The derivation
# is over this file's own expectations, not over the module being guarded, so the
# `dataclasses.fields()` lesson -- an expectation that widens with the thing it
# guards -- does not apply: nothing here is read back from `arming_probe`.

# The disarming vectors: the entries that must each have a test driving them, and
# what the family's "one per arm" claim rests on.
EXPECTED_VECTORS = {
    "COMMAND_LINE_FILTER_OVERRIDE",
    "UNLOADED_WARNINGS_PLUGIN",
    "REWRITTEN_FILTER_DECLARATION",
    "UNLOADED_UNRAISABLE_PLUGIN",
}

# What each arm must say when it bites, plus the reading of a missing sentence.
# Driven by an `assert_` step rather than a `given_` one, so they are deliberately
# out of the linkage guard's reach.
EXPECTED_SENTENCES = {
    "EXPECTED_OVERRIDE_REFUSAL",
    "EXPECTED_INERT_FILTER_REFUSAL",
    "EXPECTED_REWRITTEN_DECLARATION_REFUSAL",
    "EXPECTED_UNLOADED_UNRAISABLE_PLUGIN_REFUSAL",
    "NOT_THE_DISARMED_ENVIRONMENT",
}

# The probe suite itself and the name of its single test.
EXPECTED_PROBE_SOURCE = {
    "ARMING_PROBE",
    "ARMING_PROBE_TEST_NAME",
}

# The types the roster's own entries are built from. Not a vector and not a
# sentence, so it is classified rather than left to widen one of those two.
EXPECTED_TYPES = {
    "ArmRefusal",
}

# Every public module-level name `arming_probe` is allowed to carry. A name added
# there and not classified above fails the membership guard; a name removed there
# and left above fails it too, so the pin holds in both directions.
EXPECTED_ROSTER = (
    EXPECTED_VECTORS | EXPECTED_SENTENCES | EXPECTED_PROBE_SOURCE | EXPECTED_TYPES
)


class ArmingProbeRosterStatements:
    """Pin the membership of `arming_probe.py` against hand-written literal names."""

    def __init__(self) -> None:
        self._reader = ArmingProbeRosterReader()

    def assert_the_probe_module_declares_exactly_the_known_roster(self) -> None:
        """Discovered, then compared whole -- so an addition cannot be silent.

        Compared as a set rather than searched for known names: `name in declared`
        for each expected entry is green on a module that also declares five
        undriven ones, which is the entire state this exists to reject.
        """
        declared = self._reader.declared_names()
        assert declared == EXPECTED_ROSTER, (
            f"`arming_probe.py` declares {sorted(declared)}, expected exactly "
            f"{sorted(EXPECTED_ROSTER)} -- every constant in that module is referenced from "
            f"a single place in `DisarmedArmingProbeStatements`, so one added without a "
            f"test driving it is watched by nothing. Added: {sorted(declared - EXPECTED_ROSTER)}; "
            f"missing: {sorted(EXPECTED_ROSTER - declared)}"
        )

    def assert_every_declared_vector_is_spent_on_a_given_step(self) -> None:
        """Which vectors a `given_` step actually references -- not how many exist.

        A count comparison ("as many steps as vectors, plus the control") would be
        green on a family that declared a fifth vector and wrote a fifth step
        naming the *fourth* one twice, which is the shape a copy-pasted step takes.
        So the linkage is read as references out of the steps' own syntax tree: a
        vector declared and never referenced by any step is a disarming environment
        nothing runs, and in the file it reads exactly like one that is covered.

        Answerable in both directions, because the discovered set is narrowed to
        the whole declared roster rather than to the expectation -- so a step
        reaching for a constant that is not a vector is as red as a vector no step
        reaches for.
        """
        referenced = self._reader.vector_names_the_given_steps_use()
        assert referenced == EXPECTED_VECTORS, (
            f"the `given_a_runner_environment_*` steps reference {sorted(referenced)}, "
            f"expected exactly {sorted(EXPECTED_VECTORS)} -- a declared vector no step "
            f"references is a disarming environment no test ever runs. Undriven: "
            f"{sorted(EXPECTED_VECTORS - referenced)}; unexpected: "
            f"{sorted(referenced - EXPECTED_VECTORS)}"
        )
