"""Choosing, deliberately, the one runner variable a kept-environment child gets.

Two families now run a child with `keep_ambient_environment=True`: the disarmed
arming probe, whose subject is a hostile `PYTEST_ADDOPTS`, and the potency
control beside the forgotten-await gate, which has to reproduce the very
environment that gate refuses to inherit. Both pay the same price for the
exemption -- the base no longer scrubs for them, so they must scrub by hand and
then put back exactly one vector -- and both were about to spell it out
separately.

The refusal is the part that could not live in either family. `ChildProbeStatements`
opts a whole class into keeping its environment while the compensating scrub sits
in a `given_` step, so nothing couples "this child keeps its environment" to "a
vector was deliberately chosen". A test written without the `given_` step passes
on a clean laptop and fails on a runner that exports `PYTEST_ADDOPTS`, pointing at
the harness rather than at the runner. `arranged()` is this repository's answer to
exactly that shape, and the armed control is included in it: leaving the
environment alone is a choice, and is recorded as one.
"""

import pytest

from statements.arranged import arranged
from statements.steerable_child_variables import REQUIRED_SCRUBBED_VARIABLES

# The variable a runner actually sets, and the default every vector rides in.
RUNNER_OVERRIDE_VARIABLE = "PYTEST_ADDOPTS"

# The field name `arranged()` is asked for, and therefore the one a reader of the
# refusal is told to go and set.
CHOSEN_ENVIRONMENT_FIELD = "the runner environment this child keeps"

# What the refusal must say, in full. Written out rather than read back from
# `arranged()`: read from the helper, this expectation would agree with it after
# its wording was emptied to the field name alone, and no other test in this suite
# pins that sentence -- the guard's message would then be unwatched everywhere.
EXPECTED_UNCHOSEN_REFUSAL = (
    f"{CHOSEN_ENVIRONMENT_FIELD} has not been arranged yet -- call the given_* step "
    f"that sets it before the step that reads it"
)

# What the armed control chose. A description rather than a value, because the
# control's vector *is* the absence of one -- and `arranged()` cannot tell "no
# choice made" from "chose nothing" unless the second is spelled.
UNTOUCHED_ENVIRONMENT = "an untouched runner environment"


class DisarmedChildEnvironment:
    """Every steerable variable removed, then the one chosen vector put back."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch
        self._chosen: str | None = None
        self._refusal: AssertionError | None = None

    def disarm_with_only(
        self, vector: str | None, variable: str = RUNNER_OVERRIDE_VARIABLE
    ) -> None:
        """Scrub, then set at most one thing.

        Scrubbing only the vector's own variable would leave each test differing
        from the control by more than the thing it is about. `PYTHONWARNINGS` is
        the case that matters and it is not hypothetical: it is a *different*
        mechanism from the `-W` filters these vectors use -- those land in
        `config.option.pythonwarnings`, while `PYTHONWARNINGS` is read by Python's
        own warnings machinery before pytest sees anything. An ambient
        `PYTHONWARNINGS=ignore::RuntimeWarning` therefore silences a provoked
        RuntimeWarning all by itself, which is precisely the state a
        `-p no:warnings` test asserts -- green with its own vector contributing
        nothing.

        Scrubbed against `REQUIRED_SCRUBBED_VARIABLES` rather than against the
        subject's own `LEAKY_CHILD_VARIABLES`. Read from the subject, this
        isolation would move whenever the subject moved: deleting an entry there
        would stop scrubbing it here too, and the potency control would go on
        passing under an ambient copy of the very variable it exists to hold
        still. The roster it is scrubbed against is pinned against the subject in
        both directions by `test_child_environment_scrub.py`, which is what keeps
        the two from drifting apart without a red test.
        """
        for name in REQUIRED_SCRUBBED_VARIABLES:
            self._monkeypatch.delenv(name, raising=False)
        if vector is not None:
            self._monkeypatch.setenv(variable, vector)
        self._chosen = vector if vector is not None else UNTOUCHED_ENVIRONMENT

    def refuse_the_act_until_a_vector_was_chosen(self) -> None:
        """Refuse the act until a `given_` step has decided what the child keeps.

        Not named `assert_*`, though it does raise: this runs on the *action* path,
        and `assert_` is reserved in this suite's DSL for the steps a test body calls
        in its assertion phase. A guard wearing that prefix reads, at every call
        site, as an assertion the test made -- when in fact no test ever calls it.
        """
        arranged(self._chosen, CHOSEN_ENVIRONMENT_FIELD)

    def record_the_refusal(self, refusal: AssertionError) -> None:
        """Held for the assertion step, so the act stays visible in the test body."""
        self._refusal = refusal

    def assert_the_refusal_named_the_unchosen_environment(self) -> None:
        """The whole sentence, not the field name inside it.

        `arranged()`'s message is fully deterministic, so there is nothing here to
        be loose about -- and an `in` over the field name alone would stay green
        through a rewrite that emptied the remedy clause, which is the half a
        reader meeting this failure in CI cannot reconstruct. `AssertionError` is
        raised from four other places on this act path (two `arranged()` calls
        inside `ChildPytestRun`, the probe-destination refusal, and the report
        guard), so equality rather than containment is also what makes this
        assertion about the unchosen environment rather than about the act having
        failed somehow.
        """
        refusal = arranged(self._refusal, "the refusal the act was expected to raise")
        assert str(refusal) == EXPECTED_UNCHOSEN_REFUSAL, (
            f"the act refused, but not for the unchosen environment -- it said "
            f'"{refusal}", expected "{EXPECTED_UNCHOSEN_REFUSAL}"'
        )

    def assert_no_child_was_run_before_the_refusal(self, no_child_was_run: bool) -> None:
        """The sentence says the guard fired; this says it fired *first*.

        Asserted apart from the message because they are separable states and only
        one of them is the point. A guard that ran the child, read its report, and
        only then noticed the unchosen environment raises the identical sentence and
        passes the assertion above unchanged -- while having already paid the entire
        cost the guard exists to avoid: a real pytest executed under whatever the
        developer's shell happens to carry, green on a clean laptop and red on a
        runner that exports `PYTEST_ADDOPTS`. Short-circuiting *is* the claim, and
        the report's absence is the only place it is observable.
        """
        assert no_child_was_run, (
            "the act raised the unchosen-environment refusal, but only after running a "
            "child -- the guard exists to keep a pytest from executing under an "
            "environment nobody chose, so refusing afterwards leaves that cost fully paid "
            "and the refusal is then a report about a run that already happened"
        )
