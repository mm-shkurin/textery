"""The steps every family that keeps its child's ambient environment must ship.

Two families run their child with `keep_ambient_environment=True`: the disarmed
arming probe, whose subject *is* a hostile `PYTEST_ADDOPTS`, and the potency
control beside the forgotten-await gate, which has to reproduce the very
environment that gate refuses to inherit. `DisarmedChildEnvironment` already
holds the mechanics they share -- scrub the roster by hand, put back exactly one
vector, and refuse until one was chosen. What stayed duplicated was the four
steps that *wire* those mechanics into a Statements family: the guarded act, the
act that expects the guard to fire, and the two assertions about the refusal.

They were duplicated on purpose while the arming family's act was still
unguarded: a shared base carries the guarded act, and that act's absence there
was the recorded RED. The guard has since landed on both sides, so the two
copies are now verbatim and the base is what keeps them that way -- a fix
applied to one family's refusal path can no longer miss the other's.

Mixed in ahead of each family's own base rather than inserted into it. The two
families descend from different places -- `ChildProbeStatements` directly, and
`ForgottenAwaitGateStatements` which adds the gate's claims on top of it -- and
the second family must not inherit a probe it does not stage. `super()` inside
this class therefore resolves to whichever of those two the concrete family put
after it, which is exactly the act being wrapped.

What stays with each family is what differs: *which* vectors exist, which probe
is staged, and what the child is then required to say.
"""

import pytest

from statements.disarmed_child_environment import DisarmedChildEnvironment


class KeptAmbientChildBase:
    """The refusal path shared by the families whose child keeps its environment."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Both halves of the exemption in one place: the opt-in and its price.

        A family that opts into `keep_ambient_environment=True` without also
        arranging a `DisarmedChildEnvironment` has taken the base's scrub away and
        put nothing back -- the state the refusal below exists to make impossible.
        Binding them to a single constructor is what stops the two from being
        typed apart.
        """
        super().__init__(keep_ambient_environment=True)
        self._environment = DisarmedChildEnvironment(monkeypatch)

    def run_the_probe_under_the_projects_own_pytest_configuration(self) -> None:
        """Refused until a vector was chosen -- see `DisarmedChildEnvironment`.

        These families keep their ambient environment, so a test that forgot its
        `given_` step would run under whatever the developer's shell carries: green
        on a clean laptop, red on a runner that exports `PYTEST_ADDOPTS`, and
        pointing at the harness rather than at the runner either way. The guard runs
        before the act, not after it, because the entire cost it exists to avoid is
        paid inside the child.
        """
        self._environment.refuse_the_act_until_a_vector_was_chosen()
        super().run_the_probe_under_the_projects_own_pytest_configuration()

    def run_the_probe_expecting_it_to_be_refused(self) -> None:
        """The act for each family's arrangement guard.

        The refusal is caught here rather than in the test body so the body still
        reads as one act step, and is handed to the collaborator rather than kept
        on this class so the two assertions below have one source.
        """
        with pytest.raises(AssertionError) as refusal:
            self.run_the_probe_under_the_projects_own_pytest_configuration()
        self._environment.record_the_refusal(refusal.value)

    def assert_the_refusal_named_the_unchosen_environment(self) -> None:
        self._environment.assert_the_refusal_named_the_unchosen_environment()

    def assert_no_child_was_run_before_the_refusal(self) -> None:
        """What keeps the guard from being satisfied by a check placed *after* the run.

        A guard moved below the child run raises the identical sentence while paying
        the whole cost the guard exists to avoid, so the message assertion above
        cannot tell the two apart; the report's absence is the only place the
        short-circuit is observable. The reasoning in full is in
        `DisarmedChildEnvironment.assert_no_child_was_run_before_the_refusal`.
        """
        self._environment.assert_no_child_was_run_before_the_refusal(self._no_child_was_run())
