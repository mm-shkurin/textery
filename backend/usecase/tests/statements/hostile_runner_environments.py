"""The runner environments measured to disarm the forgotten-await gate.

Two ambient states, each *measured* to disarm the gate on its own when the child
is allowed to keep them, and each by a different mechanism: a command-line `-W`
filter is applied after the ini entries and the last matching filter wins, while
`-p no:unraisableexception` unloads the plugin that turns the destructor's
swallowed RuntimeWarning into a warning at all, so the second ini entry matches
nothing. Both were driven by hand against the real `pyproject.toml`: probe exit 1
with the environment clean, exit 0 with either one set.

`PYTHONWARNINGS=ignore::RuntimeWarning` is deliberately *not* in this list. It
reads like the obvious vector and it is inert here -- measured, not assumed:
pytest applies its own ini `filterwarnings` after the ones it inherits from
`PYTHONWARNINGS`, so the probe still fails (exit 1) with it set, and a test
carrying only that variable would be green in every state including the one it
exists to reject.

Two test files parametrise over this list, and the pair is what makes either of
them mean anything -- `test_forgotten_await_gate.py` requires the gate to bite
*through* each vector, `test_hostile_runner_environment_potency.py` requires the
same probe to pass *under* it. Read alone, the first is silent about whether the
vector does anything and the second is silent about whether the probe leaks a
coroutine at all; read together, the vector's potency is the only thing that can
tell the two apart. So both must stay parametrised over this one list and over
`FORGOTTEN_AWAIT_PROBE`. The list lives here rather than in either test file
precisely so neither can drift off it.
"""

HOSTILE_RUNNER_ENVIRONMENTS = [
    ("PYTEST_ADDOPTS", "-W ignore::RuntimeWarning"),
    ("PYTEST_ADDOPTS", "-p no:unraisableexception"),
]
