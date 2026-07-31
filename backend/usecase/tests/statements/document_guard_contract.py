"""The arrangement contract shared by the document-scope and edit-scope guards.

Scenario 1.1 (`document_scope_guard_statements`) and scenario 1.2
(`ai_edit_guard_base`) grew byte-identical copies of the same actor ids, the same
frozen clock and the same canonical refusal body. Two copies of a constant that
must never differ is a drift trap: a rename in one scenario leaves the other
green while the two guards silently stop describing the same contract.

Everything here is deliberately TEST-SIDE. None of it is imported from
`backend/usecase/src/` -- the test is the specification, so importing the
production constant would make any future edit to it self-approving: a rename of
the refusal text would keep both 1.1 and 1.2 green while the acceptance suite's
byte-identity contract with the client silently changed.
"""

from collections.abc import Awaitable
from dataclasses import fields
from datetime import UTC, datetime
from uuid import UUID

from shared.exceptions import NotFoundException

EPOCH = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

CALLER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000002")
ABSENT_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000099")

# The one canonical refusal body the ADR requires of all seven endpoints. It
# names no document and carries no instruction text --
# `not_found_exception_handler` logs the exception verbatim at INFO, so anything
# in here lands in the log of a request whose whole premise is that the caller
# has no claim to that id.
REFUSAL_MESSAGE = "document not found"


async def captured[Raised: Exception](
    awaitable: Awaitable[object], expected: type[Raised], description: str
) -> Raised:
    """Await a guard call that must raise, and hand the exception back.

    Three classes had grown their own copy of this try/except/else-AssertionError
    shape, differing only in the type they catch and the prose they fail with --
    and the silent-success branch is the one that matters: a guard that *returns*
    where it should have refused would otherwise surface as an
    `AssertionError: NoneType` further down, or not at all.

    `description` carries each call site's own words into the failure, so a red
    run still names which refusal or which outage failed to materialise.
    """
    try:
        await awaitable
    except expected as raised:
        return raised
    raise AssertionError(
        f"expected {description}, but the guard returned ({expected.__name__} was never raised)"
    )


def assert_is_the_canonical_refusal(refusal: Exception, which: str) -> None:
    """Type, byte-identical body and non-disclosure settled in one equality.

    Named once so no two refusals in the story can drift apart: whatever
    "canonical" comes to mean, every refusal 1.1 and 1.2 raise is held to the
    same single expression of it. `which` keeps the failure scenario-specific --
    a reader of a red run still learns *which* refusal broke the contract.
    """
    assert (type(refusal), str(refusal)) == (NotFoundException, REFUSAL_MESSAGE), (
        f"the {which} refusal is {type(refusal).__name__}('{refusal}'), expected "
        f"NotFoundException('{REFUSAL_MESSAGE}')"
    )


def assert_bounded_projection(scope: object, expected_field_names: list[str], why: str) -> None:
    """The scope carries exactly the fields it was pinned to, and no more.

    Pinned by literal name list rather than derived from `dataclasses.fields` of
    the class under test: a guard derived from the thing it guards widens the
    moment the thing widens. A field added later with a default would still
    satisfy dataclass equality, and the promise the projection encodes would die
    without a single red test. `why` carries each scope's own stake in that
    promise into the failure message.
    """
    actual = [field.name for field in fields(scope)]
    assert actual == expected_field_names, (
        f"{type(scope).__name__} must stay the bounded projection "
        f"{expected_field_names}, but carries {actual} -- {why}"
    )
