"""The fields of a `Generation` a failure path must not touch, read off one entity.

A sibling module rather than another method on the Statements, for the reason
`arranged.py` is one: the *list* is a statement about `Generation`, not about the
prompt-failure scenario, and the next Statements that needs "the row came back
unaltered" should inherit the list rather than retype a subset of it.

Split out of `generation_prompt_failure_statements.py` when widening its
unaltered-row assertion from three fields to nine pushed that file past the
200-line limit.
"""

from typing import Any

from generation.generation import Generation

# Every attribute `Generation.__init__` sets, minus the three this usecase is
# *supposed* to move. `GenerateDocument.execute` calls exactly `mark_in_progress()`,
# `complete()` and `fail()`, which between them write `status`, `content` and
# `error_message` and nothing else -- so on any path, success or failure, the nine
# below are invariants of the row.
#
# Enumerated rather than derived from `vars(generation)` minus a mutable set: a
# derivation covers a field added to the entity tomorrow automatically, which sounds
# like the safer option and is the weaker one. A new field is a new decision about
# whether this usecase may write it, and the tests that care should go red until
# somebody makes it. `assert_no_field_escaped_this_list` below is what turns that
# from a comment into a check.
INVARIANT_FIELD_NAMES = (
    "id",
    "owner_id",
    "created_at",
    "version",
    "topic",
    "volume_pages",
    "requirements",
    "extra_wishes",
    "document_type",
    # Both arrived with «Повторить» (story 12) and are decided invariant here.
    # `GenerateDocument` runs a generation; it never creates one, so it has no
    # business rewriting the key that made this row unique to its request, nor the
    # lineage that says which failed row it descends from. Writing either from a
    # failure path would break the retry ceiling's count and the replay lookup at
    # once — which is exactly the decision this tripwire exists to force.
    "idempotency_key",
    "source_generation_id",
)

# The three the usecase legitimately writes. Named here rather than left implicit so
# that the completeness check below has both halves to add up.
MUTABLE_FIELD_NAMES = ("status", "content", "error_message")


def invariant_fields(generation: Generation) -> tuple[Any, ...]:
    """`INVARIANT_FIELD_NAMES`' values, by value, in declared order.

    By value and not by holding the entity, which is the whole point: the fake hands
    the usecase the very instance the test seeded and the usecase mutates it in
    place, so a "snapshot" that is really an alias moves both sides of the comparison
    together and passes against a usecase that rewrote the field under test.
    """
    return tuple(getattr(generation, name) for name in INVARIANT_FIELD_NAMES)


def assert_no_field_escaped_this_list(generation: Generation) -> None:
    """Every attribute of `generation` is declared invariant or declared mutable.

    The tripwire that keeps `INVARIANT_FIELD_NAMES` honest. Without it, a tenth field
    added to `Generation` is simply absent from the tuple, and every "the row came
    back unaltered" assertion in this suite keeps passing while saying nothing about
    it -- the silent under-assertion the hand-written list is otherwise wide open to.
    """
    declared = set(INVARIANT_FIELD_NAMES) | set(MUTABLE_FIELD_NAMES)
    actual = set(vars(generation))

    undeclared = sorted(actual - declared)
    stale = sorted(declared - actual)

    assert undeclared == [], (
        f"Generation grew {undeclared} -- decide whether GenerateDocument may write "
        f"each one, then add it to INVARIANT_FIELD_NAMES or MUTABLE_FIELD_NAMES"
    )
    assert stale == [], f"these names are declared here but no longer exist on Generation: {stale}"
