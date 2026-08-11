"""The roster of everything a runner could steer a child pytest with.

Spelled out here rather than imported from `child_pytest_run.LEAKY_CHILD_VARIABLES`.
Read back from the module under test, every consumer below would agree with that
tuple by construction and go on agreeing with it after an entry was deleted --
green in exactly the state they exist to reject.

Two consumers, and they are deliberately different in kind:

* `child_environment_scrub_statements.py` compares this roster against what
  `ChildPytestRun._child_environment()` actually removes, in both directions. That
  is the pin: `LEAKY_CHILD_VARIABLES` may neither shrink below this roster nor grow
  beyond it without a red test.
* `DisarmedChildEnvironment` scrubs *this* roster by hand for the two families that
  opt out of the base's scrub. It used to scrub `LEAKY_CHILD_VARIABLES`, which made
  their isolation co-vary with the subject: delete `PYTHONWARNINGS` from that tuple
  and the potency control silently stopped scrubbing it too, so an ambient
  `PYTHONWARNINGS=ignore::RuntimeWarning` would leave the control passing with its
  own vector contributing nothing. Isolation must not move when the subject moves.

`PY_COLORS` and `FORCE_COLOR` are in the roster for a different reason than the
rest. They steer no filter and load no plugin; they turn pytest's markup on, and
`ChildPytestReport`'s anchored banner pattern then matches nothing the child drew,
so every gate in this package reports `the child summarised {}` -- blaming pytest
for a report pytest wrote correctly. `coloured_child_report_statements.py` proves
the reader survives colour once it arrives; the scrub keeps it from arriving.

`COV_CORE_SOURCE`/`COV_CORE_CONFIG`/`COV_CORE_DATAFILE` are in the roster for a
third reason, and they are *measured* rather than assumed: `pytest-cov` exports
them for the duration of a coverage run and its `.pth` bootstrap starts coverage
inside any process that inherits them. The children here run with
`cwd=BACKEND_ROOT`, so under `/test-coverage` an inheriting child writes stray
`.coverage.*` files into the repository and merges probe-module lines -- code
written by a Statements module, executed once, never imported by the suite --
into the combined report the parent then reads as its own.

What is deliberately *not* in the roster, so a later reader does not have to
re-derive it: `PYTEST_XDIST_*`, `CI`, `GITHUB_ACTIONS` and the rest of a runner's
badge variables steer nothing a child pytest decides -- no filter, no plugin, no
markup -- and `COVERAGE_FILE` is left alone on purpose, because it names a file
rather than loading anything and the children start no coverage once `COV_CORE_*`
is gone. The standard this file holds itself to is that an exclusion is written
down with its reason, the way `PYTHONWARNINGS` documents being scrubbed for a
mechanism other than the one it looks like.
"""

# Everything an ambient shell or a CI runner can set that changes what the child
# decides about warnings, which plugins it loads, or how it draws its report.
REQUIRED_SCRUBBED_VARIABLES = (
    "PYTEST_ADDOPTS",
    "PYTHONWARNINGS",
    "PYTEST_PLUGINS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_CURRENT_TEST",
    "PY_COLORS",
    "FORCE_COLOR",
    "COV_CORE_SOURCE",
    "COV_CORE_CONFIG",
    "COV_CORE_DATAFILE",
)

# One recognisable value for all of them: the claim is about names surviving, and
# the names are what the roster above is for.
AMBIENT_VALUE = "set-by-the-parent"

# What the opt-in child must be handed, written out as a literal rather than built
# from the roster with `dict.fromkeys`. Derived, both sides of that equality would
# move together and a reader would have to resolve a comprehension to learn what
# was expected. The duplication is double-entry bookkeeping and is the point: the
# two disagreeing is itself a red test.
EXPECTED_KEPT_ENVIRONMENT = {
    "PYTEST_ADDOPTS": "set-by-the-parent",
    "PYTHONWARNINGS": "set-by-the-parent",
    "PYTEST_PLUGINS": "set-by-the-parent",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "set-by-the-parent",
    "PYTEST_CURRENT_TEST": "set-by-the-parent",
    "PY_COLORS": "set-by-the-parent",
    "FORCE_COLOR": "set-by-the-parent",
    "COV_CORE_SOURCE": "set-by-the-parent",
    "COV_CORE_CONFIG": "set-by-the-parent",
    "COV_CORE_DATAFILE": "set-by-the-parent",
}
