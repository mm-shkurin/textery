from collections.abc import Awaitable

from fake.document_edit.fake_ai_edit_repository import (
    FailingDocumentScopeRepository,
    StorageUnavailableError,
)
from statements.ai_edit_guard_base import QUEUED_EDIT_ID, AiEditGuardBase
from statements.arranged import arranged
from statements.document_guard_contract import assert_is_the_store_outage, captured_outage

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
        self._raised = await self._outage_from(self.resolve(self.first_document_id))

    async def request_the_edit_while_the_document_store_is_down(self) -> None:
        failing = FailingDocumentScopeRepository(StorageUnavailableError(OUTAGE_MESSAGE))
        self._raised = await self._outage_from(self.resolve_via(failing, self.first_document_id))

    async def _outage_from(self, resolution: Awaitable[object]) -> Exception:
        return await captured_outage(
            resolution, f"the store failure to propagate for edit {QUEUED_EDIT_ID}"
        )

    def assert_the_outage_propagated_unchanged(self) -> None:
        assert_is_the_store_outage(
            arranged(self._raised, "raised"), OUTAGE_MESSAGE, "the store outage"
        )

    def assert_the_edit_store_was_asked_once(self) -> None:
        """The positive control that keeps the emptiness assertion honest.

        `lookups == []` is the shape that passes when nothing is wired at all. On
        the path where step 2 *is* reached, the same spy must show the exact
        lookup -- otherwise both assertions in this class would be satisfied by a
        fake nobody ever calls.
        """
        self.assert_edit_lookups(
            [(QUEUED_EDIT_ID, self.first_document_id)],
            "the lookup must have reached the store before it failed, or both assertions "
            "in this class would be satisfied by a fake nobody ever calls",
        )

    def assert_the_edit_store_was_never_asked(self) -> None:
        """Step 1 failing is still step 1: the edit lookup must not have run.

        The ordering guard holds for an outage exactly as it does for a refusal.
        Without it, a guard that ran both lookups and let the document error win
        would pass `assert_the_outage_propagated_unchanged` while having already
        performed the unauthorized read the ADR forbids.
        """
        self.assert_edit_lookups(
            [],
            "the document store was down, and step 2 must not run when step 1 did not resolve",
        )
