"""What stops a fourth vector from joining this family unwatched.

`arming_probe.py` is a roster: three disarming vectors and the sentences each arm
must say. Every one of them is referenced from exactly one place -- its own
`given_` or `assert_` step on `DisarmedArmingProbeStatements` -- and nothing
anywhere compares the roster as a whole. So a fourth constant added to that file
is driven by no test, asserted by no test, and reported by nothing: it simply sits
there, and the suite stays green.

That is not hypothetical for this family, it is its history. The third arm's
vector was named in `disarmed_arming_probe_statements.py`'s own module docstring
as "scheduled separately with its own vector (`-o filterwarnings=...`)" and then
went unscheduled for the whole life of the file, while the arm it belonged to had
never failed in any process. Coverage could not find it -- the arm is a bare
`assert`, and `assert` is not a branch to coverage.py, so the file reported 26 of
27 lines the entire time. And a fourth arm is already known to be waiting:
`assert_the_unraisable_plugin_is_loaded_in_this_run` sits outside
`assert_both_filter_entries_are_in_force_in_this_run`, its `assert loaded is True`
has never failed either, and its own message names the vector that would drive it
(`-p no:unraisableexception`).

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

import inspect

import statements.arming_probe as arming_probe

# Every public module-level name `arming_probe` is allowed to carry, written out.
# A name added there and not added here fails this guard; a name removed there and
# left here fails it too, so the pin holds in both directions.
EXPECTED_ROSTER = {
    "ARMING_PROBE",
    "ARMING_PROBE_TEST_NAME",
    "COMMAND_LINE_FILTER_OVERRIDE",
    "UNLOADED_WARNINGS_PLUGIN",
    "REWRITTEN_FILTER_DECLARATION",
    "EXPECTED_OVERRIDE_REFUSAL",
    "EXPECTED_INERT_FILTER_REFUSAL",
    "EXPECTED_REWRITTEN_DECLARATION_REFUSAL",
    "NOT_THE_DISARMED_ENVIRONMENT",
}

# The vectors, named apart from the sentences: these are the entries that must each
# have a test driving them, and the count is what the family's "one per arm" claim
# rests on.
EXPECTED_VECTORS = {
    "COMMAND_LINE_FILTER_OVERRIDE",
    "UNLOADED_WARNINGS_PLUGIN",
    "REWRITTEN_FILTER_DECLARATION",
}


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
            f"exactly one step, so one added without a test driving it is watched by "
            f"nothing. Added: {sorted(declared - EXPECTED_ROSTER)}; "
            f"missing: {sorted(EXPECTED_ROSTER - declared)}"
        )

    def assert_every_declared_vector_is_spent_on_a_given_step(self) -> None:
        """Which vectors a `given_` step actually names -- not how many there are.

        A count comparison ("as many steps as vectors, plus the control") would be
        green on a family that declared a fourth vector and wrote a fourth step
        naming the *third* one twice, which is the shape a copy-pasted step takes.
        So the linkage is read by name out of the steps' own source: a vector
        declared and never named by any step is a disarming environment nothing
        runs, and in the file it reads exactly like one that is covered.
        """
        named = self._vector_names_the_given_steps_use()
        assert named == EXPECTED_VECTORS, (
            f"the `given_a_runner_environment_*` steps name {sorted(named)}, expected "
            f"exactly {sorted(EXPECTED_VECTORS)} -- a declared vector no step names is a "
            f"disarming environment no test ever runs. Undriven: "
            f"{sorted(EXPECTED_VECTORS - named)}"
        )

    def _vector_names_the_given_steps_use(self) -> set[str]:
        """The vector constants named in the body of any vector-choosing step."""
        from statements.disarmed_arming_probe_statements import DisarmedArmingProbeStatements

        bodies = [
            inspect.getsource(getattr(DisarmedArmingProbeStatements, name))
            for name in dir(DisarmedArmingProbeStatements)
            if name.startswith("given_a_runner_environment_")
        ]
        return {name for name in EXPECTED_VECTORS if any(name in body for body in bodies)}

    def _declared_names(self) -> set[str]:
        """Every public module-level name `arming_probe` carries, discovered.

        `vars()` rather than a transcribed list, and filtered only on the leading
        underscore and on being a module or import -- so a constant of any type is
        caught. Filtering to `str` would let a future list-valued roster entry in
        without a word.
        """
        return {
            name
            for name, value in vars(arming_probe).items()
            if not name.startswith("_") and not inspect.ismodule(value)
        }
