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
from typing import TYPE_CHECKING
from uuid import UUID

from fake.document_edit.fake_ai_edit_repository import StorageUnavailableError
from shared.exceptions import NotFoundException

if TYPE_CHECKING:
    # Typeshed's "any dataclass instance", available to the checker only. Typed as
    # `object` this module's projection helper was a standing mypy failure, because
    # `dataclasses.fields` accepts a dataclass and `object` is not one.
    from _typeshed import DataclassInstance

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


def assert_is_the_canonical_refusal(refusal: object, which: str) -> None:
    """Type, byte-identical body and non-disclosure settled in one equality.

    Named once so no two refusals in the story can drift apart: whatever
    "canonical" comes to mean, every refusal 1.1 and 1.2 raise is held to the
    same single expression of it. `which` keeps the failure scenario-specific --
    a reader of a red run still learns *which* refusal broke the contract.

    Typed `object`, not `Exception`: the boundary probes hand it whatever the guard
    produced, and "the guard returned a scope where it should have refused" is one
    of the outcomes this equality exists to catch. Narrowing the parameter made
    that call site a standing mypy error and presumed away the case.
    """
    assert (type(refusal), str(refusal)) == (NotFoundException, REFUSAL_MESSAGE), (
        f"the {which} refusal is {type(refusal).__name__}('{refusal}'), expected "
        f"NotFoundException('{REFUSAL_MESSAGE}')"
    )


async def captured_outage(resolution: Awaitable[object], description: str) -> Exception:
    """Await a guard call that must let a store failure out, and hand it back.

    Caught as bare `Exception`, not `StorageUnavailableError`: narrowing the
    guard's error is exactly the defect under test, so the capture must be able to
    see whatever the guard actually let out.
    """
    return await captured(resolution, Exception, description)


async def outcome_of(resolution: Awaitable[object]) -> object:
    """Records what came back; judges none of it.

    The two classes that own boundary and silence probes each grew this shape, and
    each for the same reason: an act step that swallowed the expected error and
    raised `AssertionError` on anything else enforced a real behavioural contract
    from inside the arrange/act half, where no reader of the test body could see
    it. The judging belongs in the then-phase; the capturing belongs here.
    """
    try:
        return await resolution
    except Exception as raised:  # noqa: BLE001 -- the then-phase pins the exact type
        return raised


def assert_is_the_store_outage(raised: object, message: str, which: str) -> None:
    """Exact type and exact text, not merely "not a NotFoundException".

    A negative-only check is satisfied by anything -- a wrapper, a generic
    RuntimeError, an exception raised while handling the first one. This one
    equality settles the propagation positively, and by doing so already rules out
    both `NotFoundException` and the canonical refusal body: an exact `type(...) ==`
    admits no subclass, and an exact `str(...) ==` admits no other text.
    """
    actual = (type(raised), str(raised))
    assert actual == (StorageUnavailableError, message), (
        f"{which} surfaced as {type(raised).__name__}('{raised}'), expected "
        f"StorageUnavailableError('{message}') -- an outage rendered as the canonical 404 "
        f"hides the incident and still passes the byte-identity assertion"
    )


def assert_lookups(what: str, actual: list[object], expected: list[object], why: str) -> None:
    """A child store's call log, compared whole.

    Comparing the whole list -- rather than a count, or "the child was not
    returned" -- is what makes the ordering and range guards real. A guard that
    looked the child up first and only then checked the document would refuse
    identically and satisfy every other assertion in its package, while having
    already performed an unauthorized read. `why` carries each caller's stake into
    the failure.
    """
    assert actual == expected, f"expected {what} lookups {expected}, got {actual} -- {why}"


def assert_bounded_projection(
    scope: "DataclassInstance", expected_field_names: list[str], why: str
) -> None:
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
