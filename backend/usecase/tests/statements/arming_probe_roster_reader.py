"""Reading `arming_probe.py`'s roster off the module rather than transcribing it.

Split out of `ArmingProbeRosterStatements` when the fourth vector arrived: that file
stood at 190 lines and the two new roster entries left it ten short of the 200-line
limit, with a fifth vector already the thing it exists to anticipate. The division
is the one the harness families
already use -- `ChildPytestReport` reads a child run, `ForgottenAwaitGateStatements`
states the claims -- so the expectations and the assertions stay in the Statements
class and the reflection that answers them lives here.

Nothing in this file carries an expectation. It answers two questions about code as
it is written: which public names the probe module declares, and which of those the
family's vector-choosing steps actually reference. What either answer *should* be is
the Statements class's business, and keeping the two apart is what stops a repair
from being applied to the reader -- widening what it discovers is indistinguishable,
from the assertion's side, from widening the expectation.
"""

import ast
import inspect
import textwrap

import statements.arming_probe as arming_probe
from statements.disarmed_arming_probe_statements import DisarmedArmingProbeStatements

# The prefix every step that picks one disarming vector is named with. The linkage
# guard discovers its subjects by this rather than by a list, so a fourth step is
# in front of the guard the moment it is written -- and a vector whose step was
# never written is the state the guard reports.
VECTOR_CHOOSING_STEP_PREFIX = "given_a_runner_environment_"


class ArmingProbeRosterReader:
    """What the probe module and the family's steps say, discovered rather than told."""

    def declared_names(self) -> set[str]:
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

        The leading-underscore filter is a known hole and is left open deliberately:
        a `_`-prefixed vector would escape both guards. Closing it here would make
        every private helper a roster entry; what closes it is that a vector has to
        be referenced by a `given_` step to be driven at all, and a step naming a
        private constant is the reading the linkage guard's message asks for.
        """
        return {
            name
            for name, value in vars(arming_probe).items()
            if not name.startswith("_") and not inspect.ismodule(value)
        }

    def vector_names_the_given_steps_use(self) -> set[str]:
        """The roster constants a vector-choosing step actually *references*.

        Read off the parsed syntax tree rather than searched for as substrings.
        `getsource` returns the docstring too, so a substring test counts a step
        that merely *mentions* a constant in prose as having spent it -- and a
        copy-pasted step arrives carrying the copied step's docstring, which is
        the very shape the roster guard exists to reject. An `ast.Name` is a
        reference or it is nothing.

        Narrowed to the declared roster rather than to the expected vectors.
        Filtered by the expectation, the result could never hold anything the
        expectation did not already contain, so the caller's equality would
        collapse to "no vector is missing" and a step that reached for a *fifth*
        declared vector, or for one of the sentence constants, would be invisible.
        Against the roster the comparison is answerable in both directions.
        """
        declared = self.declared_names()
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
            if name.startswith(VECTOR_CHOOSING_STEP_PREFIX)
        ]
