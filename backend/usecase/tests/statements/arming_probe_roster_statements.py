"""What stops a fourth vector from joining this family unwatched.

`arming_probe.py` is a roster: three disarming vectors and the sentences each arm
must say. Each is referenced from a single place in `DisarmedArmingProbeStatements`
-- the vectors from their own `given_` steps, the refusal sentences from their own
`assert_` steps, and `ARMING_PROBE_TEST_NAME` and `NOT_THE_DISARMED_ENVIRONMENT`
from the one private helper those `assert_` steps share -- and nothing anywhere
compares the roster as a whole. So a fourth constant added to that file is driven
by no test, asserted by no test, and reported by nothing: it simply sits there, and
the suite stays green.

That is not hypothetical for this family, it is its history: the third arm's vector
sat in a module docstring as "scheduled separately" for the whole life of the file,
driven by nothing and reported by nothing. Why coverage could not find it is with
the arms themselves, in `DisarmedArmingProbeStatements`.

A fourth arm is already known to be waiting, which is what makes this a guard
rather than a retrospective: `assert_the_unraisable_plugin_is_loaded_in_this_run`
sits outside `assert_both_filter_entries_are_in_force_in_this_run`, its
`assert loaded is True` has never failed in any process either, and its own message
names the `-p no:unraisableexception` that would drive it.

So the roster is **discovered** from the module rather than transcribed from it,
and pinned against hand-written literal names. Transcribed, the expectation would
widen with the thing it guards -- the `dataclasses.fields()` lesson this story has
now learned three times -- and adding a constant to both places at once is exactly
what an author adding a constant does. Discovery means the addition is red until
someone writes the test that drives it, which is the whole point.

Names only, deliberately. Every value here is already pinned by the test that
consumes it, and repeating the sentences would put a second copy of each in the
repository free to drift from the first. What is unwatched is the *membership* of
the roster, and that is what this pins.
"""

import ast
import inspect
import textwrap

import statements.arming_probe as arming_probe
from statements.disarmed_arming_probe_statements import DisarmedArmingProbeStatements

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
}

# What each arm must say when it bites, plus the reading of a missing sentence.
# Driven by an `assert_` step rather than a `given_` one, so they are deliberately
# out of the linkage guard's reach.
EXPECTED_SENTENCES = {
    "EXPECTED_OVERRIDE_REFUSAL",
    "EXPECTED_INERT_FILTER_REFUSAL",
    "EXPECTED_REWRITTEN_DECLARATION_REFUSAL",
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

    def assert_the_probe_module_declares_exactly_the_known_roster(self) -> None:
        """Discovered, then compared whole -- so an addition cannot be silent.

        Compared as a set rather than searched for known names: `name in declared`
        for each expected entry is green on a module that also declares five
        undriven ones, which is the entire state this exists to reject.
        """
        declared = self._declared_names()
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
        green on a family that declared a fourth vector and wrote a fourth step
        naming the *third* one twice, which is the shape a copy-pasted step takes.
        So the linkage is read as references out of the steps' own syntax tree: a
        vector declared and never referenced by any step is a disarming environment
        nothing runs, and in the file it reads exactly like one that is covered.

        Answerable in both directions, because the discovered set is narrowed to
        the whole declared roster rather than to the expectation -- so a step
        reaching for a constant that is not a vector is as red as a vector no step
        reaches for.
        """
        referenced = self._vector_names_the_given_steps_use()
        assert referenced == EXPECTED_VECTORS, (
            f"the `given_a_runner_environment_*` steps reference {sorted(referenced)}, "
            f"expected exactly {sorted(EXPECTED_VECTORS)} -- a declared vector no step "
            f"references is a disarming environment no test ever runs. Undriven: "
            f"{sorted(EXPECTED_VECTORS - referenced)}; unexpected: "
            f"{sorted(referenced - EXPECTED_VECTORS)}"
        )

    def _vector_names_the_given_steps_use(self) -> set[str]:
        """The roster constants a vector-choosing step actually *references*.

        Read off the parsed syntax tree rather than searched for as substrings.
        `getsource` returns the docstring too, so a substring test counts a step
        that merely *mentions* a constant in prose as having spent it -- and a
        copy-pasted step arrives carrying the copied step's docstring, which is
        the very shape the class docstring says this guard exists to reject. An
        `ast.Name` is a reference or it is nothing.

        Narrowed to the declared roster rather than to `EXPECTED_VECTORS`. Filtered
        by the expectation, the result could never hold anything the expectation
        did not already contain, so the equality below would collapse to "no vector
        is missing" and a step that reached for a *fourth* declared vector, or for
        one of the sentence constants, would be invisible. Against the roster the
        comparison is answerable in both directions.
        """
        declared = self._declared_names()
        return {
            node.id
            for step in self._vector_choosing_steps()
            for node in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(step))))
            if isinstance(node, ast.Name) and node.id in declared
        }

    def _vector_choosing_steps(self) -> list[object]:
        """The steps whose job is to pick one disarming vector, discovered by prefix."""
        return [
            getattr(DisarmedArmingProbeStatements, name)
            for name in dir(DisarmedArmingProbeStatements)
            if name.startswith("given_a_runner_environment_")
        ]

    def _declared_names(self) -> set[str]:
        """Every public module-level name `arming_probe` carries, discovered.

        `vars()` rather than a transcribed list, and filtered only on the leading
        underscore and on being a module -- so a constant of any type is caught.
        Filtering to `str` would let a future list-valued roster entry in without a
        word, and `ArmRefusal` would have been missed outright.

        The module filter is the *only* import this can see through, which is why
        `arming_probe.py` imports `typing` as a module rather than binding
        `NamedTuple` directly: a bare imported name is indistinguishable from a
        declared one here and would read as an unclassified roster entry. That
        constraint is recorded at the import itself, where it has to be obeyed.
        """
        return {
            name
            for name, value in vars(arming_probe).items()
            if not name.startswith("_") and not inspect.ismodule(value)
        }
