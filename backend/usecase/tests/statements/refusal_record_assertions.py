"""What a single refusal record must look like, judged independently of collection.

`RefusalLogStatementsBase` owns the recorder lifecycle, the act steps and the
accessors -- getting hold of the record. This module owns the other half: given a
record and the literals of the guard that emitted it, is it the right record. The
two guards' assertions were byte-identical apart from those literals, and the
sentinel below was the sharpest part of the copy: §1.2 and §1.3 each declared their
own `"<absent>"` under a different name, while `refusal_record_shape_statements`
exists precisely to prove the two build their `extra` by one rule.

Deliberately TEST-SIDE, like `document_guard_contract`: nothing here is imported
from `backend/usecase/src/`, so a rename on the production side has to face a red
test rather than approve itself.
"""

import logging

# The value a record is expected to carry for a field the guard must not attach.
# Expecting the sentinel -- rather than checking `not hasattr` -- is what makes
# "the guard recorded nothing at all" fail the same assertion that pins the ids it
# *must* carry.
ABSENT = "<absent>"

# Step 1 refuses for the same reason in both guards, so the cause is one string.
# The step-2 cause is per-guard and lives on the subclass.
DOCUMENT_SCOPE_REFUSAL_CAUSE = "document-scope-refused"


def assert_record_shape(
    record: logging.LogRecord, logger_name: str, message: str, cause: str, which: str
) -> None:
    """Logger, level, whole message and cause, settled in one equality.

    The message is compared with `==` rather than `in`: a substring check leaves
    the rest of it unconstrained, so an id the guard was never supposed to record
    could ride along in text while every check for the *enumerated* ids passed.
    """
    actual = (
        record.name,
        record.levelno,
        record.getMessage(),
        getattr(record, "refusal_cause", ABSENT),
    )
    expected = (logger_name, logging.INFO, message, cause)
    assert actual == expected, (
        f"the {which} refusal record is {actual}, expected {expected} -- the line must be "
        f"the id-free literal at INFO on the guard's own logger, discriminated only by its "
        f"structured cause"
    )


def assert_record_ids(
    record: logging.LogRecord, id_fields: tuple[str, ...], expected: dict[str, str], which: str
) -> None:
    """The whole id mapping, read through the pinned roster.

    `actual` is built from `id_fields`, not from `expected`'s own keys: derived
    from the expectation, a field dropped from the expectation drops from both
    sides and the assertion agrees with its own omission.
    """
    actual = {name: getattr(record, name, ABSENT) for name in id_fields}
    assert actual == expected, (
        f"the {which} refusal record carries ids {actual}, expected {expected} -- an id the "
        f"caller has no proven claim to must not be written to our logs, and the ids they "
        f"do own must be there for the record to be attributable"
    )


def assert_causes_are_distinct(
    cross_record: logging.LogRecord,
    absent_record: logging.LogRecord,
    child_scope_refusal_cause: str,
    probe_description: str,
) -> None:
    """Both operands read off production records, and both pinned exactly.

    Comparing the two module constants to each other is something no implementation
    can fail. Comparing the two *records* for inequality is better but still
    relative: a guard that stamped some third pair of different-but-wrong causes
    satisfies `!=` while the two values operators actually alert on have silently
    moved. Pinned as one tuple equality, so the property is both "different" and
    "these two".
    """
    cross = getattr(cross_record, "refusal_cause", ABSENT)
    absent = getattr(absent_record, "refusal_cause", ABSENT)
    expected = (child_scope_refusal_cause, DOCUMENT_SCOPE_REFUSAL_CAUSE)
    assert (cross, absent) == expected, (
        f"the two refusals were recorded under the causes {(cross, absent)}, expected "
        f"{expected} -- a cross-document probe against {probe_description} must not be "
        f"indistinguishable from a typo'd document id in our own records, which is the one "
        f"place the two must be told apart"
    )
