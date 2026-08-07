"""Which names in a fixture module `conftest.py` has to re-export.

`conftest.py` used to re-list the db suite's fixtures by hand, twice — an import
list and an `__all__`. A fixture added to `statement_fixtures` and forgotten there
is invisible until setup of whichever test asks for it, where pytest reports
"fixture not found" and prints the ones that WERE remembered. Four fixtures sat in
that state, and only CI could see it: on a machine without Postgres the whole suite
skips, so the list was never exercised.

So the list is computed. This module is where that computation lives, with the two
things that make it trustworthy.
"""

from _pytest.fixtures import FixtureFunctionDefinition

# Every fixture this module family is expected to define. A registry that silently
# EMPTIES is the same bug with the same symptom, and the detection below is the part
# that can quietly stop matching — pytest's fixture marker is private and has been
# renamed at least once (`_pytestfixturefunction` -> `_fixture_function_marker`), and
# a `hasattr` against a name that no longer exists returns an empty list without a
# word. Raising on a short count turns that into a collection-time failure that names
# its own cause. Raise this number when fixtures are added.
_EXPECTED_AT_LEAST = 15


def fixture_names(namespace: dict[str, object]) -> list[str]:
    """The public fixture names in `namespace`, for a module's `__all__`.

    Detected by the wrapper type pytest puts a decorated fixture in, not by a naming
    convention: a `_statements`-suffix rule would drop `db_session`, and would accept
    a plain helper that happened to be named like a fixture.
    """
    found = [
        name
        for name, value in list(namespace.items())
        if not name.startswith("_") and isinstance(value, FixtureFunctionDefinition)
    ]
    if len(found) < _EXPECTED_AT_LEAST:
        raise RuntimeError(
            f"Found {len(found)} fixtures, fewer than the {_EXPECTED_AT_LEAST} expected — "
            f"fixture detection has stopped recognising pytest's wrapper type. conftest "
            f"re-exports this list, so an empty one makes every db test fail with "
            f"'fixture not found'."
        )
    return found
