"""The shared shape assertion for a compare-and-swap write.

Two adapters make the same structural guarantee -- `SqlAlchemyDocumentStorage`'s
`save_content_if_version_matches` and `SqlAlchemyGenerationStorage`'s `update` -- and
both pin it the same way, because a timing-based race test cannot catch a
read-compare-write (see either test's class docstring for the verified reason). The
assertions were written out twice, verbatim; a change to what "is a CAS" means had two
places to land in and one to be forgotten.

Only the no-SELECT message differs between the two callers, so that one is a parameter:
the consequence of a read before the write is specific to each method, and a generic
message would lose the part a reader needs.
"""

from statements.sql_recorder import RecordedSql


def assert_is_a_single_compare_and_swap(recorded: RecordedSql, no_select_because: str) -> None:
    """One UPDATE, no SELECT, the version compared in the WHERE, the row RETURNINGed."""
    selects = recorded.starting_with("SELECT")
    assert selects == [], f"{no_select_because} Got: {selects}"

    updates = recorded.starting_with("UPDATE")
    assert len(updates) == 1, f"expected exactly one UPDATE, got {len(updates)}: {updates}"

    statement = updates[0]
    head = statement.upper()
    assert "VERSION =" in head.split("WHERE", 1)[1], (
        f"the version must be compared in the WHERE clause, not in Python. Got: {statement}"
    )
    assert "RETURNING" in head, (
        "the new row must come back from the same statement; a follow-up SELECT would "
        f"re-open the race the CAS closes. Got: {statement}"
    )
