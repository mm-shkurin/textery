"""Reading a value that a `given_*` step was supposed to have set.

Every Statements class in this package holds arrangement it cannot have at
construction -- the registered email, the issued code, the token pair the act
step produced. They were declared `= None` and read as if present, which is true
in every ordering the tests actually use and invisible to a reader deciding
whether a new step is safe to add.

`arranged()` says it out loud: the value is required by the time it is read, and
a step called out of order fails naming the field instead of surfacing as
`'NoneType' object has no attribute ...` somewhere further down. It is also what
lets the type checker see these classes at all -- `str | None` flowing into a
`str` parameter was 110 errors across 15 modules.
"""


def arranged[Value](value: Value | None, field: str) -> Value:
    """Return `value`, asserting a `given_*`/act step has already set it."""
    if value is None:
        raise AssertionError(
            f"{field} has not been arranged yet -- call the given_* step that sets it "
            f"before the step that reads it"
        )
    return value
