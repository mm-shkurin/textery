"""What a child pytest is not allowed to inherit, and the filter that takes it away.

Split out of `child_pytest_run.py` when that file reached the 200-line limit. The
division is the family's usual one -- `arming_probe.py` carries the vectors its
Statements runs, `forgotten_await_probes.py` carries the probe sources -- so
`ChildPytestRun` reads as the mechanics of getting a trustworthy child and this
file holds the one policy decision those mechanics apply.

This is the *subject's* roster. `steerable_child_variables.py` holds a second copy,
spelled out independently, which is what `child_environment_scrub_statements.py`
pins this one against in both directions. The two are deliberately not shared: read
back from here, that expectation would agree with this tuple by construction and go
on agreeing after an entry was deleted. Do not collapse them.
"""

from collections.abc import Mapping

# Anything the ambient shell or a CI runner can set that would change what the
# child decides about warnings or which plugins it loads. Scrubbed by default so
# the gate is proven against `pyproject.toml` alone. Two entries are measured
# threats rather than assumed ones: `PYTEST_ADDOPTS=-W ignore::RuntimeWarning`
# makes the forgotten-await gate un-failable, and `PYTEST_DISABLE_PLUGIN_AUTOLOAD`
# keeps the control's `async def` test from ever running -- with the scrub lifted
# and that variable ambient, all four gate tests fail, the control included.
#
# `PYTHONWARNINGS=ignore::RuntimeWarning` reads like the flagship threat and is
# *not* one: pytest applies its own ini `filterwarnings` after the ones inherited
# from `PYTHONWARNINGS`, so the probe still fails with it set. It is scrubbed
# because it steers a different mechanism -- Python's own warnings machinery,
# before pytest sees anything -- which is enough to silence a warning a *probe*
# provokes directly, not because it can disarm this gate.
#
# `PY_COLORS`/`FORCE_COLOR` turn pytest's markup on, and the anchored banner pattern
# then matches nothing the child drew; `COV_CORE_*` is `pytest-cov`'s `.pth`
# bootstrap, which starts coverage inside any child that inherits it. Both groups
# are reasoned about in full in `steerable_child_variables.py`.
#
# The roster is asserted against, in both directions, by
# `test_child_environment_scrub.py`: shrink this tuple and that test goes red.
LEAKY_CHILD_VARIABLES = (
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


def without_leaky_variables(environment: Mapping[str, str]) -> dict[str, str]:
    """The ambient environment minus everything a runner could steer the child with."""
    return {name: value for name, value in environment.items() if name not in LEAKY_CHILD_VARIABLES}
