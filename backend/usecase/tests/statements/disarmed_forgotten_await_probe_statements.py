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
must leave the gate silent.
"""

import pytest

from statements.disarmed_child_environment import DisarmedChildEnvironment
from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements


class DisarmedForgottenAwaitProbeStatements(ForgottenAwaitGateStatements):
    """Run the forgotten-await probe under a vector the child is allowed to keep."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        super().__init__(keep_ambient_environment=True)
        self._environment = DisarmedChildEnvironment(monkeypatch)

    def given_a_runner_environment_carrying_only(self, variable: str, value: str) -> None:
        """Passed by keyword: this step reads `(variable, value)` and the collaborator
        takes `(vector, variable)`, both `str`, so a positional call is a silent
        transposition waiting to happen.
        """
        self._environment.disarm_with_only(vector=value, variable=variable)

    def run_the_probe_under_the_projects_own_pytest_configuration(self) -> None:
        """Refused until a vector was chosen -- see `DisarmedChildEnvironment`.

        This family keeps its ambient environment, so a test that forgot its
        `given_` step would run under whatever the developer's shell carries: green
        on a clean laptop, red on a runner that exports `PYTEST_ADDOPTS`, and
        pointing at the harness rather than at the runner either way.
        """
        self._environment.refuse_the_act_until_a_vector_was_chosen()
        super().run_the_probe_under_the_projects_own_pytest_configuration()

    def run_the_probe_expecting_it_to_be_refused(self) -> None:
        """The act for this family's own refusal test -- see the sibling family.

        The sibling ships the same two steps. They are not collapsed into a shared
        base yet on purpose: what a base would naturally also carry is the guarded
        act above, and the sibling's act is deliberately *unguarded* right now --
        that is the RED. The extraction belongs after it goes green.
        """
        with pytest.raises(AssertionError) as refusal:
            self.run_the_probe_under_the_projects_own_pytest_configuration()
        self._environment.record_the_refusal(refusal.value)

    def assert_the_refusal_named_the_unchosen_environment(self) -> None:
        self._environment.assert_the_refusal_named_the_unchosen_environment()

    def assert_no_child_was_run_before_the_refusal(self) -> None:
        self._environment.assert_no_child_was_run_before_the_refusal(self._no_child_was_run())

    def assert_the_gate_was_disarmed_by_the_vector(self) -> None:
        """Exit 0 and a clean tally: the forgotten `await` went entirely unnoticed.

        `assert_the_probe_suite_passed` pins the whole tally, which is what makes
        this a measurement of the vector rather than of the exit code. A vector that
        left the warning recorded but unpromoted would report `{passed: 1,
        warning: 1}` -- half-disarmed, and a state the gate test above could not
        tell from fully disarmed.
        """
        self.assert_the_probe_suite_passed()
