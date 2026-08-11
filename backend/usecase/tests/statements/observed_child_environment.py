"""What one call to `ChildPytestRun._child_environment()` did to the parent's.

Split from `child_environment_scrub_statements.py` so that file reads as the claim
and this one holds the reading. The reading is the part that decides how strong the
claim can be, and the earlier version of it was narrower than the subject:
`_child_environment` does three things -- it drops the leaky names, it redirects the
scratch root, and it hands everything else through untouched -- and only the first
was observed. Both halves of the scrub test were therefore green against a builder
that rewrote every surviving variable's value, and against one that dropped the
scratch redirection the subject's own docstring calls load-bearing (a full-suite run
was once seen to abort a child's collection with `FileNotFoundError` on exactly the
inherited `TEMP` this redirection takes away).

So all three are read here, and each is read as a *difference from the ambient
snapshot* rather than filtered through the expectation it will be compared with.
That distinction is the whole design: `steerable_values` is filtered through
`REQUIRED_SCRUBBED_VARIABLES` and so is definitionally blind to a steerable name the
roster was never told about, which is why `added_names` and `rewritten_names` are
computed from the snapshot instead and carry the names that filter would swallow.

The snapshot is taken when the environment is built rather than when it is asserted
on, so the comparison cannot drift if anything in between touches `os.environ`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from statements.child_pytest_run import ChildPytestRun
from statements.steerable_child_variables import REQUIRED_SCRUBBED_VARIABLES

# The child never runs here -- `_child_environment()` is read directly -- but a
# probe has to exist on disk because the environment carries the run's own scratch
# root, which `write_probe` is what creates.
UNRUN_PROBE = """
def test_never_run() -> None:
    pass
"""

# The three names `ChildPytestRun` overwrites for *every* child, kept or scrubbed
# alike. Excluded from `added_names` and `rewritten_names` below because the
# redirection is the subject's deliberate act rather than a leak; they are pinned by
# value separately, as `scratch_overrides`.
REDIRECTED_SCRATCH_VARIABLES = ("TMPDIR", "TEMP", "TMP")


@dataclass(frozen=True)
class ObservedChildEnvironment:
    """One built child environment, as five differences from the parent's."""

    removed_names: frozenset[str]
    added_names: frozenset[str]
    rewritten_names: frozenset[str]
    steerable_values: dict[str, str]
    scratch_overrides: dict[str, str]


def observe_child_environment(run: ChildPytestRun, tmp_path: Path) -> ObservedChildEnvironment:
    """Read the private builder, deliberately, rather than run a child.

    `_child_environment` is private because no *production* caller has any business
    with it; the scrub test is the one place whose subject it is, and promoting it to
    public to be asserted on would advertise it as a seam for callers who must not
    have one. Running a real child instead would prove the scrub only for entries
    with a measured disarming vector -- which is exactly the hole this reading exists
    to close.
    """
    run.write_probe(tmp_path, UNRUN_PROBE)
    ambient = dict(os.environ)
    environment = run._child_environment()
    redirected = set(REDIRECTED_SCRATCH_VARIABLES)
    return ObservedChildEnvironment(
        removed_names=frozenset(set(ambient) - set(environment)),
        added_names=frozenset(set(environment) - set(ambient) - redirected),
        # `.get(name, value)` so a name the builder *removed* is charged to
        # `removed_names` alone and does not also read as a rewrite.
        rewritten_names=frozenset(
            name
            for name, value in ambient.items()
            if name not in redirected and environment.get(name, value) != value
        ),
        steerable_values={
            name: value
            for name, value in environment.items()
            if name in REQUIRED_SCRUBBED_VARIABLES
        },
        # Described rather than omitted when absent, so the assertion reports both
        # what it wanted and what it got in one message.
        scratch_overrides={
            name: environment.get(name, f"<no {name} in the child's environment>")
            for name in REDIRECTED_SCRATCH_VARIABLES
        },
    )
