from collections.abc import Awaitable

from fake.document_edit.fake_ai_edit_repository import (
    FailingDocumentScopeRepository,
    StorageUnavailableError,
)
from statements.arranged import arranged
from statements.document_guard_contract import captured
from statements.revision_guard_base import (
    RECORDED_REVISION_NUMBER,
    RECORDED_REVISION_PARAMETER,
    RevisionGuardBase,
)

# Qualified by class: `RevisionSilenceStatements` pins a deliberately *different*
# outage text, and two same-named constants that must stay different are the drift
# trap the scope-field lists in this family already closed by qualifying their names.
REVISION_OUTAGE_MESSAGE = "document_revisions read timed out"


class RevisionOutageStatements(RevisionGuardBase):
    """An outage in either store must not be rendered as the canonical 404.

    A later broad `except` around either step would map a down database onto
    "document not found" -- and §1.3's own byte-identity assertion would pass while
    the incident became invisible to the caller and to the on-call. 1.2 proved this
    for step 1 only; here both repositories are driven to raise.
    """

    def __init__(self) -> None:
        super().__init__()
        self._raised: Exception | None = None

    def given_the_revision_store_is_unavailable(self) -> None:
        self.revision_repository.fail_every_lookup_with(
            StorageUnavailableError(REVISION_OUTAGE_MESSAGE)
        )

    async def request_the_revision_under_its_own_document(self) -> None:
        self._raised = await self._outage_from(self.resolve(self.first_document_id))

    async def request_the_revision_while_the_document_store_is_down(self) -> None:
        failing = FailingDocumentScopeRepository(StorageUnavailableError(REVISION_OUTAGE_MESSAGE))
        self._raised = await self._outage_from(self.resolve_via(failing, self.first_document_id))

    async def _outage_from(self, resolution: Awaitable[object]) -> Exception:
        # Caught as bare `Exception`, not `StorageUnavailableError`: narrowing the
        # guard's error is exactly the defect under test, so the capture must be
        # able to see whatever the guard actually let out.
        return await captured(
            resolution,
            Exception,
            f"the store failure to propagate for revision '{RECORDED_REVISION_PARAMETER}'",
        )

    def assert_the_outage_propagated_unchanged(self) -> None:
        """Exact type and exact text, not merely "not a NotFoundException".

        A negative-only check is satisfied by anything -- a wrapper, a generic
        RuntimeError, an exception raised while handling the first one. This one
        equality settles the propagation positively, and by doing so already rules
        out both `NotFoundException` and the canonical refusal body: an exact
        `type(...) ==` admits no subclass, and an exact `str(...) ==` admits no
        other text.
        """
        raised = arranged(self._raised, "raised")
        assert (type(raised), str(raised)) == (StorageUnavailableError, REVISION_OUTAGE_MESSAGE), (
            f"the store outage surfaced as {type(raised).__name__}('{raised}'), expected "
            f"StorageUnavailableError('{REVISION_OUTAGE_MESSAGE}') -- an outage rendered as the "
            f"canonical 404 hides the incident and still passes the byte-identity assertion"
        )

    def assert_the_revision_store_was_asked_once(self) -> None:
        """The positive control that keeps the emptiness assertion honest.

        `lookups == []` is the shape that passes when nothing is wired at all. On
        the path where step 2 *is* reached, the same spy must show the exact
        lookup -- otherwise both assertions in this class would be satisfied by a
        fake nobody ever calls.
        """
        self._assert_revision_lookups(
            [(RECORDED_REVISION_NUMBER, self.first_document_id)],
            "the lookup must have reached the store before it failed, or both assertions in "
            "this class would be satisfied by a fake nobody ever calls",
        )

    def assert_the_revision_store_was_never_asked(self) -> None:
        """Step 1 failing is still step 1: the revision lookup must not have run.

        Without it, a guard that ran both lookups and let the document error win
        would pass the propagation assertion while having already performed the
        unauthorized read the ADR forbids.
        """
        self._assert_revision_lookups(
            [],
            "the document store was down, and step 2 must not run when step 1 did not resolve",
        )
