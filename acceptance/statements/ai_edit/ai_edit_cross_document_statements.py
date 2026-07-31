from datetime import datetime, timezone

from clients.application.application_client import ApplicationClient
from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit import ai_edit_cross_document_assertions as guard
from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit import ai_edit_endpoint_probes as probes
from statements.ai_edit.ai_edit_cross_document_probes import (
    CrossDocumentProbe,
    CrossDocumentSetup,
)
from statements.ai_edit.ai_edit_edit_states import QUEUED_STATUS
from statements.ai_edit.ai_edit_http_status import ACCEPTED_STATUS
from statements.authenticated_account import register_verify_and_login
from statements.response_assertions import assert_is_valid_uuid
from statements.test_data import TestData

ACCEPTED_FIELDS = {"edit_id", "status"}


class AiEditCrossDocumentStatements:
    """Scenario 1.2 — an edit of one document is not found under another of the same
    owner. Everything is seeded through the public endpoints; no row is hand-built.
    """

    def __init__(self, client: ApplicationClient, edit_client: DocumentEditClient):
        self._client = client
        self._edit_client = edit_client

    async def given_an_edit_queued_on_the_first_of_two_owned_documents(
        self,
    ) -> CrossDocumentSetup:
        owner = await register_verify_and_login(self._client)
        first_document_id = await seed.create_document_owned_by(
            self._edit_client, owner.access_token
        )
        second_document_id = await seed.create_document_owned_by(
            self._edit_client, owner.access_token
        )
        edit_id, queued_before, queued_after = await self._given_an_edit_queued_on(
            owner.access_token, first_document_id
        )
        return CrossDocumentSetup(
            owner_token=owner.access_token,
            first_document_id=first_document_id,
            second_document_id=second_document_id,
            edit_id=edit_id,
            queued_before=queued_before,
            queued_after=queued_after,
        )

    async def when_the_edit_is_requested_under_the_second_documents_path(
        self, setup: CrossDocumentSetup, endpoint: str
    ) -> CrossDocumentProbe:
        refusal = await probes.invoke_with_edit(
            self._edit_client,
            endpoint,
            setup.owner_token,
            setup.second_document_id,
            setup.edit_id,
        )
        return CrossDocumentProbe(endpoint=endpoint, refusal=refusal, setup=setup)

    async def then_the_edit_is_read_back_under_its_own_document(
        self, probe: CrossDocumentProbe
    ) -> RawResponseDto:
        return await self._edit_client.get_edit(
            probe.setup.owner_token, probe.first_document_id, probe.edit_id
        )

    def assert_refused_as_not_found(self, probe: CrossDocumentProbe) -> None:
        guard.assert_refused_as_not_found(probe)

    def assert_the_edit_survived_under_its_own_document(
        self, probe: CrossDocumentProbe, edit_state_after: RawResponseDto
    ) -> None:
        guard.assert_the_edit_survived_under_its_own_document(probe, edit_state_after)

    async def _given_an_edit_queued_on(
        self, token: str, document_id: str
    ) -> tuple[str, datetime, datetime]:
        """A REAL edit, queued through the public endpoint.

        The scenario only bites when the edit id exists: a fabricated id would be
        refused by any handler that merely fails to find it, and the test would pass
        without the path document id ever having been consulted. `base_version` is the
        literal first version, which `create_document_owned_by` has just pinned — not a
        value read back at runtime, so the request stays dumb.
        """
        before = datetime.now(timezone.utc)
        response = await self._edit_client.queue_edit(
            token,
            document_id,
            {"message": probes.PROBE_INSTRUCTION, "base_version": seed.FIRST_VERSION},
            TestData.unique_idempotency_key(),
        )
        after = datetime.now(timezone.utc)
        self._assert_accepted_as_queued(response, document_id)
        return str((response.body or {})["edit_id"]), before, after

    @staticmethod
    def _assert_accepted_as_queued(response: RawResponseDto, document_id: str) -> None:
        assert response.status_code == ACCEPTED_STATUS, (
            f"setup: expected {ACCEPTED_STATUS} queueing an edit on the caller's first "
            f"document {document_id}, got status_code={response.status_code}, "
            f"body={response.text!r}"
        )
        body = response.body or {}
        assert set(body) == ACCEPTED_FIELDS, (
            f"setup: expected the accepted edit to carry exactly "
            f"{sorted(ACCEPTED_FIELDS)}, got {sorted(body)} in body={response.text!r}"
        )
        assert_is_valid_uuid(body.get("edit_id"), field_name="edit_id")
        # documents_ai_edits_create.yaml: on a FIRST submission status is server-set to
        # exactly `queued`. The idempotency key is fresh, so this IS a first submission —
        # any other value means the seeded edit is not the one the scenario describes.
        assert body.get("status") == QUEUED_STATUS, (
            f"setup: a first submission is server-set to {QUEUED_STATUS!r}, got "
            f"status={body.get('status')!r} in body={response.text!r}"
        )
