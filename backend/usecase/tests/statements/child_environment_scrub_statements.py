"""What a child pytest is allowed to inherit, asserted on the environment itself.

The scrub was watched only end-to-end: one parametrised gate test set a
`PYTEST_ADDOPTS` measured to disarm the forgotten-await gate and required the gate
to bite anyway. That shape is real, but it can only ever watch the entries for
which a *disarming* vector exists, and it drives `PYTEST_ADDOPTS` twice. Delete
`PYTHONWARNINGS`, `PYTEST_PLUGINS`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD` or
`PYTEST_CURRENT_TEST` from `LEAKY_CHILD_VARIABLES` and the whole suite stays
green -- while `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` ambient, with the scrub lifted,
fails all four gate tests including the control, exactly the breakage the
constant's own comment predicts.

So the roster is pinned here instead, against `REQUIRED_SCRUBBED_VARIABLES` --
spelled independently of the subject in `steerable_child_variables.py`, for the
reason recorded there. Every entry is set in the parent, a default `ChildPytestRun`
is asked what environment it would hand its child, and the assertion is made on the
differences that environment shows from the parent's -- read by
`observe_child_environment`, which records all five of them.

Reading the difference is the whole design, and the earliest shape did not have it.
Filtered through the expected roster, the actual was definitionally a subset of the
expected and the default half read `== {}` -- satisfied by a builder that scrubbed
the entire ambient environment, or that returned nothing at all. The opt-in half was
claimed to cover that and cannot: it constructs a *different* `ChildPytestRun` and
exercises the other branch, so the two halves degrade independently. Compared as a
removed-name set the default half is red on an entry surviving, red on an unrelated
variable being scrubbed, and red on an empty inherited environment -- and red, too,
when `LEAKY_CHILD_VARIABLES` grows an entry the roster here was never told about,
which no direction of the old shape could see.

Both halves then assert the two properties the subject holds *unconditionally*, and
which the removed-name set is blind to by construction: nothing was added or
rewritten, and the scratch root was redirected to this run's own. Those are not
decoration. `_child_environment` returns the ambient dict with three keys
overwritten, so a builder that handed the child the right *names* carrying rewritten
*values* removes nothing and passes a removed-name comparison in either branch; and
the scratch redirection is the half of that method with no roster at all behind it,
whose loss shows up as a child collecting into a directory this process does not own
rather than as a scrub failure.

The opt-in half stays, and now says the thing it was always meant to: nothing was
removed, and all seven names arrived carrying the values the parent set. Without it
a scrub that reached the opt-in would leave the disarmed families' gates asserting
nothing.
"""

from pathlib import Path

import pytest

from statements.arranged import arranged
from statements.child_pytest_run import ChildPytestRun
from statements.observed_child_environment import (
    ObservedChildEnvironment,
    observe_child_environment,
)
from statements.steerable_child_variables import (
    AMBIENT_VALUE,
    EXPECTED_KEPT_ENVIRONMENT,
    REQUIRED_SCRUBBED_VARIABLES,
)


class ChildEnvironmentScrubStatements:
    """Set the steerable variables in the parent, read what the child would be handed."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch
        self._scratch_root: Path | None = None
        self._default: ObservedChildEnvironment | None = None
        self._opt_in: ObservedChildEnvironment | None = None

    def given_every_variable_a_runner_could_steer_the_child_with(self) -> None:
        """Set in the parent, because inheritance is the whole question.

        `monkeypatch` restores all of them at teardown however the test ends, and
        the parent's own run is unaffected: its filters and `config.option` were
        resolved at startup.
        """
        for name in REQUIRED_SCRUBBED_VARIABLES:
            self._monkeypatch.setenv(name, AMBIENT_VALUE)

    def build_the_default_childs_environment(self, tmp_path: Path) -> None:
        self._scratch_root = tmp_path
        self._default = observe_child_environment(ChildPytestRun(), tmp_path)

    def build_the_opt_in_childs_environment(self, tmp_path: Path) -> None:
        self._scratch_root = tmp_path
        self._opt_in = observe_child_environment(
            ChildPytestRun(keep_ambient_environment=True), tmp_path
        )

    def assert_the_default_child_inherits_none_of_them(self) -> None:
        observed = arranged(self._default, "the default child's environment")
        removed = set(observed.removed_names)
        expected = set(REQUIRED_SCRUBBED_VARIABLES)
        assert removed == expected, (
            f"a default child's environment removed {sorted(removed)} from the parent's, "
            f"expected exactly {sorted(expected)} -- a name missing from the left survived "
            f"the scrub, and a runner that exports it then decides what this repository's "
            f"configuration is proven against; a name only on the left was scrubbed without "
            f"this roster being told, which is how the two silently drift apart"
        )
        self._assert_nothing_but_the_scrub_and_the_scratch_moved(observed, "a default child's")

    def assert_the_opt_in_child_inherits_all_of_them(self) -> None:
        observed = arranged(self._opt_in, "the opt-in child's environment")
        removed = set(observed.removed_names)
        assert removed == set(), (
            f"the opt-in child's environment removed {sorted(removed)} from the parent's, "
            f"expected it to remove nothing -- the disarmed families exist to run under a "
            f"hostile environment, and a scrub that reached them would leave those gates "
            f"asserting nothing"
        )
        assert observed.steerable_values == EXPECTED_KEPT_ENVIRONMENT, (
            f"the opt-in child would inherit {observed.steerable_values}, expected "
            f"{EXPECTED_KEPT_ENVIRONMENT} -- the names surviving is not enough; a child "
            f"handed the right names carrying rewritten values keeps none of the hostility "
            f"the vector was chosen for"
        )
        self._assert_nothing_but_the_scrub_and_the_scratch_moved(observed, "the opt-in child's")

    def _assert_nothing_but_the_scrub_and_the_scratch_moved(
        self, observed: ObservedChildEnvironment, which: str
    ) -> None:
        """The two claims the subject makes in *both* branches, so both halves make them.

        `steerable_values` cannot carry these: it is filtered through
        `REQUIRED_SCRUBBED_VARIABLES` and so is blind by construction to any name the
        roster was never told about. These two are read from the ambient snapshot
        instead, which is what makes them able to see a name the expectation has
        never heard of.
        """
        moved = (sorted(observed.added_names), sorted(observed.rewritten_names))
        assert moved == ([], []), (
            f"{which} environment added {moved[0]} and rewrote {moved[1]} on top of the "
            f"parent's, expected it to do neither -- `_child_environment` may drop names "
            f"and redirect the scratch root, and a value it quietly rewrote is invisible to "
            f"every removed-name comparison in this file"
        )
        expected_scratch = str(
            arranged(self._scratch_root, "the scratch root the children were built under") / "child"
        )
        expected = {"TMPDIR": expected_scratch, "TEMP": expected_scratch, "TMP": expected_scratch}
        assert observed.scratch_overrides == expected, (
            f"{which} environment points its scratch at {observed.scratch_overrides}, expected "
            f"{expected} -- the redirection is unconditional and has no roster behind it, and "
            f"a child that inherits the parent's TEMP builds its `tmp_path` factory under a "
            f"directory this process does not own"
        )
