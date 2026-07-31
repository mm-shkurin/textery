from uuid import UUID

from document_edit.ai_edit_repository import AiEditRepository
from document_edit.resolve_owned_edit import resolve_owned_edit

from document.document_repository import DocumentRepository
from fake.document_edit.fake_ai_edit_repository import (
    FailingDocumentScopeRepository,
    StorageUnavailableError,
)
from statements.ai_edit_guard_base import (
    CALLER_ID,
    QUEUED_EDIT_ID,
    AiEditGuardBase,
)
from statements.arranged import arranged

OUTAGE_MESSAGE = "ai_edits read timed out"


class AiEditStoreFailureStatements(AiEditGuardBase):
    """An outage in either store must not be rendered as the canonical 404.

    A later broad `except` around the guard would map a down database onto
    "document not found" -- and §1.2's own byte-identity assertion would pass
    while the incident became invisible to the caller and to the on-call.
    """

    def __init__(self) -> None:
        super().__init__()
        self._raised: Exception | None = None

    def given_the_edit_store_is_unavailable(self) -> None:
        self.ai_edit_repository.fail_every_lookup_with(StorageUnavailableError(OUTAGE_MESSAGE))

    async def request_the_edit_under_its_own_document(self) -> None:
        self._raised = await self._capture(self.first_document_id, self.ai_edit_repository)

    async def request_the_edit_while_the_document_store_is_down(self) -> None:
        failing = FailingDocumentScopeRepository(StorageUnavailableError(OUTAGE_MESSAGE))
        self._raised = await self._capture(self.first_document_id, self.ai_edit_repository, failing)

    async def _capture(
        self,
        document_id: UUID,
        ai_edit_repository: AiEditRepository,
        document_repository: DocumentRepository | None = None,
    ) -> Exception:
        try:
            await resolve_owned_edit(
                document_repository or self.document_repository,
                ai_edit_repository,
                document_id,
                QUEUED_EDIT_ID,
                CALLER_ID,
            )
        except Exception as raised:  # noqa: BLE001 - the guard under test is what may narrow it
            return raised
        raise AssertionError(
            f"expected the store failure to propagate for edit {QUEUED_EDIT_ID}, "
            f"but the guard returned"
        )

    def assert_the_outage_propagated_unchanged(self) -> None:
        """Exact type and exact text, not merely "not a NotFoundException".

        A negative-only check is satisfied by anything -- a wrapper, a generic
        RuntimeError, an exception raised while handling the first one. This one
        equality settles the propagation positively, and by doing so it already
        rules out both `NotFoundException` and the canonical refusal body: an
        exact `type(...) ==` admits no subclass, and an exact `str(...) ==` admits
        no other text. The negative restatements this method used to carry were
        unreachable, and an assertion that cannot fail is one a reader still has
        to spend attention on.
        """
        raised = arranged(self._raised, "raised")
        assert (type(raised), str(raised)) == (StorageUnavailableError, OUTAGE_MESSAGE), (
            f"the store outage surfaced as {type(raised).__name__}('{raised}'), expected "
            f"StorageUnavailableError('{OUTAGE_MESSAGE}') -- an outage rendered as the "
            f"canonical 404 hides the incident and still passes the byte-identity assertion"
        )

    def assert_the_edit_store_was_asked_once(self) -> None:
        """The positive control that keeps the emptiness assertion honest.

        `lookups == []` is the shape that passes when nothing is wired at all. On
        the path where step 2 *is* reached, the same spy must show the exact
        lookup -- otherwise both assertions in this class would be satisfied by a
        fake nobody ever calls.
        """
        lookups = self.ai_edit_repository.lookups
        expected = [(QUEUED_EDIT_ID, self.first_document_id)]
        assert lookups == expected, (
            f"expected the edit lookup {expected} to have reached the store before it failed, "
            f"got {lookups}"
        )

    def assert_the_edit_store_was_never_asked(self) -> None:
        """Step 1 failing is still step 1: the edit lookup must not have run.

        The ordering guard holds for an outage exactly as it does for a refusal.
        Without it, a guard that ran both lookups and let the document error win
        would pass `assert_the_outage_propagated_unchanged` while having already
        performed the unauthorized read the ADR forbids.
        """
        lookups = self.ai_edit_repository.lookups
        assert lookups == [], (
            f"the AI-edit repository was called {len(lookups)} time(s) ({lookups}) while the "
            f"document store was down -- step 2 must not run when step 1 did not resolve"
        )
