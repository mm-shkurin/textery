"""Where a probe may and may not be written, and what the refusal must say.

Split out of `GateReachStatements` when the second refusal destination arrived and
that file passed the 200-line limit. The division is the family's usual one --
`arming_probe.py` carries the vectors and sentences its Statements runs, and
`forgotten_await_probes.py` carries the probe sources -- so the Statements file
reads as the claims being made and this one holds the destinations they are made
about.

The roots here are the specification, not a reading of the guard, and that is now
true of the destinations as well as of the expectation. This file imports nothing
from `child_pytest_run`: `IN_TREE_SCRATCH` used to be built from the guard's own
`BACKEND_ROOT`, so a wrong `parents[3]` moved anchor and destination together and
the backend-tree refusal stayed green while both named the wrong tree. It is spelled
`REPOSITORY_ROOT / "backend" / ...` instead, from the independent derivation below.
"""

import shutil
from pathlib import Path

# The tree the refusal actually has to be about. The guard's own anchor was
# `backend/`, but the claim the gate makes -- and the remedy its message gives -- is about the
# *repository*: "write the probe to a tmp_path outside the repository". Those are
# two different directories, and the gap between them is a real destination.
#
# Derived from *this* file's location, not as `BACKEND_ROOT.parent`. `BACKEND_ROOT`
# is a `parents[3]` inside the module under test, and taking `.parent` of it is
# reading the guard's own anchor back out to build the guard's expectation: were
# that index ever wrong, anchor and expectation would move together and the
# comparison would stay green while both named the wrong tree. Independently
# derived they disagree, which is what a wrong anchor has to do.
#
# backend/usecase/tests/statements/<this file> -> the repository root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]

# The independent derivation is only worth having if it is answerable, so it is
# anchored to hand-written facts about this repository's layout rather than to a
# directory name -- the checkout is cloned, renamed and worked in `git worktree`s,
# so its own name is not a fact about it. `backend/` and `ProductSpecification/`
# are both committed and both sit directly under the root.
# Raised rather than asserted. A bare `assert` at module scope vanishes under `-O`
# or `PYTHONOPTIMIZE`, and these two defend the index that the `rmtree` below is
# aimed by: drifted, with the checks compiled away, the deletion points *outside*
# the repository and `ignore_errors=True` suppresses every complaint about it.
# A guard whose absence is silent and whose failure mode is a silent recursive
# delete may not be the kind of statement an interpreter flag can remove.
if not (REPOSITORY_ROOT / "backend").is_dir():
    raise RuntimeError(
        f"{REPOSITORY_ROOT} carries no `backend/`, so the `parents[4]` above has drifted "
        f"and every refusal expectation here names a tree that is not this repository"
    )
if not (REPOSITORY_ROOT / "ProductSpecification").is_dir():
    raise RuntimeError(
        f"{REPOSITORY_ROOT} carries no `ProductSpecification/`. `backend/` alone would be "
        f"satisfied by a parent directory that happens to contain one, so both are required"
    )

# The prefix every scratch this module names must carry. Read by
# `GateReachStatements` before it removes one: a recursive delete aimed by a
# constant is aimed by whatever that constant last said, so the destination is
# required to be inside `REPOSITORY_ROOT` *and* to be recognisably one of ours.
# Both halves are needed -- the ancestry check alone would approve deleting
# `backend/`, and the name check alone would approve `/.gate_reach_x`.
SCRATCH_NAME_PREFIX = ".gate_reach_"

# Where the probe-path refusal is exercised. Inside the repository on purpose --
# that is the condition being refused -- and removed in a `finally`, because until
# the refusal lands the write actually happens, and a stray `test_*_probe.py`
# under `backend/` is collected by the real suite on the next run.
IN_TREE_SCRATCH = (
    REPOSITORY_ROOT / "backend" / "usecase" / "tests" / "harness" / f"{SCRATCH_NAME_PREFIX}backend"
)

# The destination the anchor and the message disagree about: inside the repository,
# outside `backend/`. `--basetemp` at `<repo>/.tmp`, or a CI image pointing `TMP` at
# the workspace root, lands exactly here -- the scenario `gate_reach_statements`'
# own module docstring already anticipates in prose. A dot-prefixed name because
# this is a scratch, and removed in the same `finally` for the same reason as above:
# until the refusal is re-anchored the write really happens.
IN_REPOSITORY_SCRATCH = REPOSITORY_ROOT / f"{SCRATCH_NAME_PREFIX}repository"

# Deliberately no probe body: the refusal must land on the path alone, before the
# source is ever looked at, so this write has nothing for a lenient guard to
# approve of. An empty literal at the call site would read as an oversight.
NO_PROBE_SOURCE = ""

# The refusal `ChildPytestRun.write_probe` must raise, decided here because the
# test is the specification -- GREEN writes the guard to this text, not the other
# way round. Compared whole rather than searched for the root path: a refusal
# raised for some other reason echoes the attempted path too, since the path is
# under the refused tree by construction, so a substring check cannot tell the
# path-refusal apart from any other AssertionError on that write.
#
# Anchored to `REPOSITORY_ROOT`, not to `BACKEND_ROOT`. The refusal's own remedy
# clause says "outside the repository", and a guard that refuses only `backend/`
# leaves `<repo>/.tmp` -- a plain `--basetemp` -- approved, with a collectable
# `test_*.py` left behind for any root-scoped run.
#
# Named for the tree it is anchored to, not for the destination that provokes it:
# `IN_TREE_SCRATCH` above is `backend/`, and one file calling two adjacent constants
# "in tree" for two different trees is how the anchor and the sentence drifted apart
# in the first place.
EXPECTED_REPOSITORY_REFUSAL = (
    f"a probe may not be written under {REPOSITORY_ROOT}: the parent suite collects "
    f"`test_*.py` from that tree, so the probe survives as a real test of this suite "
    f"and the gate's claim that the parent never collects it becomes false. Write the "
    f"probe to a tmp_path outside the repository"
)


def remove_only_a_scratch_of_ours(scratch: Path) -> None:
    """A recursive silent delete, refused unless the target is provably one of ours.

    `shutil.rmtree(..., ignore_errors=True)` on a caller-supplied `Path` is the most
    destructive line in this package, and re-anchoring the refusal aimed it *under
    the repository root* -- so a destination constant that drifted, or a future
    caller passing a directory it did not create, would delete real work silently
    and recursively. It also runs unconditionally, including when the refusal fired
    before `mkdir`, so a directory that happened to already sit at that path is
    destroyed by a test that never wrote a byte to it.

    Two guards, both named, both *before* the deletion. Ancestry alone would approve
    deleting `backend/` itself; the name prefix alone would approve `/.gate_reach_x`
    on some other volume. Together they say: inside this repository, and recognisably
    a scratch this module named. `RuntimeError` rather than `assert`, for the reason
    the two module-scope checks above give themselves: a guard on a silent recursive delete may
    not be removable by `-O`.
    """
    if not scratch.resolve().is_relative_to(REPOSITORY_ROOT):
        raise RuntimeError(
            f"refusing to remove {scratch}: it is not under {REPOSITORY_ROOT}, so a "
            f"destination constant has drifted and this recursive delete is aimed outside "
            f"the repository -- with `ignore_errors=True` suppressing every complaint"
        )
    if not scratch.name.startswith(SCRATCH_NAME_PREFIX):
        raise RuntimeError(
            f"refusing to remove {scratch}: its name does not begin with "
            f"'{SCRATCH_NAME_PREFIX}', so nothing says this directory was created by this "
            f"module rather than being real work that happened to be at that path"
        )
    shutil.rmtree(scratch, ignore_errors=True)
