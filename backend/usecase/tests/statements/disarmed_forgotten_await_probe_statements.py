"""The forgotten-await gate's hostile vectors, re-measured rather than remembered.

`test_forgotten_await_gate.py` sets each of `HOSTILE_RUNNER_ENVIRONMENTS` in the
parent and requires the gate to bite anyway. That assertion watches the scrub, and
it is silent about the vector: it passes when the vector genuinely disarms the gate
*and* when the vector is a complete no-op. Its potency rests on a terminal session
recorded in prose -- probe exit 1 with the environment clean, exit 0 with either
one set -- and nothing re-measures it. If a future pytest reorders when `-W`
filters are applied, or folds the `unraisableexception` plugin into the core so
`-p no:unraisableexception` stops unloading anything, both vectors quietly become
inert, the scrub test keeps passing, and the scrub is unwatched again.

So the recorded session is written down as a control: the same probe, the same
vector, through a child that *keeps* its environment -- and the run is required to
pass. A vector that has stopped disarming the gate makes this child fail, which is
the only place that loss can show.

The sibling family already ships this shape as
`assert_the_arming_check_passed_under_an_armed_environment`. This is its mirror:
there, an untouched environment must leave the check passing; here, a touched one
must leave the gate silent. Both pay the same price for keeping their ambient
environment, and both charge it in the same place: `DisarmedChildEnvironment` for
the mechanics, `KeptAmbientChildBase` for the steps that wire them in.
"""

from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements
from statements.kept_ambient_child_base import KeptAmbientChildBase


class DisarmedForgottenAwaitProbeStatements(KeptAmbientChildBase, ForgottenAwaitGateStatements):
    """Run the forgotten-await probe under a vector the child is allowed to keep."""

    def given_a_runner_environment_carrying_only(self, variable: str, value: str) -> None:
        """Passed by keyword: this step reads `(variable, value)` and the collaborator
        takes `(vector, variable)`, both `str`, so a positional call is a silent
        transposition waiting to happen.
        """
        self._environment.disarm_with_only(vector=value, variable=variable)

    def given_a_runner_environment_carrying_no_vector_at_all(self) -> None:
        """The same kept-ambient child, chosen deliberately to carry nothing.

        `disarm_with_only(None)` is the "chose nothing" state `KeptAmbientChildBase`'s
        refusal is careful to keep distinct from "chose nothing yet", and it is what makes the
        negative control differ from the two arms by the vector *alone* -- same
        probe, same `keep_ambient_environment=True` child, same hand scrub.
        """
        self._environment.disarm_with_only(vector=None)

    def assert_the_gate_was_disarmed_by_the_vector(self) -> None:
        """Exit 0 and a clean tally: the forgotten `await` went entirely unnoticed.

        `assert_the_probe_suite_passed` pins the whole tally, which is what makes
        this a measurement of the vector rather than of the exit code. A vector that
        left the warning recorded but unpromoted would report `{passed: 1,
        warning: 1}` -- half-disarmed, and a state the gate test above could not
        tell from fully disarmed.
        """
        self.assert_the_probe_suite_passed()

    def assert_the_gate_still_bit_without_a_vector(self) -> None:
        """The control that makes the two arms above measurements of their vectors.

        Without it, `{passed: 1}` under a vector is equally explained by "a
        kept-ambient child cannot fail this probe at all" -- the sibling gate runs a
        *scrubbed* child, so it differs from these arms by the isolation mechanism
        as well as by the vector and cannot serve as the control. Here the only
        difference from an arm is the vector, and the child must fail *and* name the
        unawaited coroutine: an exit code alone would also be produced by a child
        that broke before collecting the probe.
        """
        self.assert_the_probe_suite_failed()
        self.assert_the_failure_named_the_unawaited_coroutine()
