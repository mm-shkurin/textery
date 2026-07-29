from clients.application.application_client import ApplicationClient
from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit import ai_edit_endpoint_probes as probes
from statements.ai_edit import ai_edit_guard_assertions as guard
from statements.ai_edit.ai_edit_guard_probes import DocumentAftermath, GuardProbe
from statements.authenticated_account import register_verify_and_login
from statements.response_assertions import assert_is_valid_uuid
from statements.test_data import TestData

DOCUMENT_TYPE = "доклад"


class AiEditGuardStatements:
    def __init__(self, client: ApplicationClient, edit_client: DocumentEditClient):
        self._client = client
        self._edit_client = edit_client

    async def given_endpoint_invoked_against_a_foreign_and_an_absent_document(
        self, endpoint: str
    ) -> GuardProbe:
        caller = await register_verify_and_login(self._client)
        owner = await register_verify_and_login(self._client)
        foreign_document_id = await self._given_document_owned_by(owner.access_token)
        document_before = await self._read_document(owner.access_token, foreign_document_id)

        foreign = await probes.invoke(
            self._edit_client, endpoint, caller.access_token, foreign_document_id
        )
        absent = await probes.invoke(
            self._edit_client, endpoint, caller.access_token, probes.absent_document_id()
        )
        return GuardProbe(
            endpoint=endpoint,
            foreign=foreign,
            absent=absent,
            owner_token=owner.access_token,
            foreign_document_id=foreign_document_id,
            document_before=document_before,
        )

    async def when_the_owner_reads_the_document_aftermath(
        self, probe: GuardProbe
    ) -> DocumentAftermath:
        return DocumentAftermath(
            messages=await self._edit_client.list_messages(
                probe.owner_token, probe.foreign_document_id
            ),
            revisions=await self._edit_client.list_revisions(
                probe.owner_token, probe.foreign_document_id
            ),
            document_after=await self._read_document(
                probe.owner_token, probe.foreign_document_id
            ),
        )

    def assert_both_refused_as_not_found(self, probe: GuardProbe) -> None:
        guard.assert_both_refused_as_not_found(probe)

    def assert_response_bodies_byte_identical(self, probe: GuardProbe) -> None:
        guard.assert_response_bodies_byte_identical(probe)

    def assert_no_edit_revision_or_message_created(
        self, probe: GuardProbe, aftermath: DocumentAftermath
    ) -> None:
        guard.assert_no_edit_revision_or_message_created(probe, aftermath)

    async def _given_document_owned_by(self, token: str) -> str:
        response = await self._edit_client.create_document(
            token, DOCUMENT_TYPE, TestData.unique_idempotency_key()
        )
        assert response.status_code == 201, (
            f"setup: expected 201 creating the other account's document, got "
            f"status_code={response.status_code}, body={response.text!r}"
        )
        document_id = (response.body or {}).get("document_id")
        # A well-formed id, not merely a present one: every probe interpolates this into
        # its path, and a junk id would make all seven refusals 404 for the wrong reason
        # — the guard would look green while never having been exercised.
        assert_is_valid_uuid(document_id, field_name="document_id")
        return str(document_id)

    async def _read_document(self, token: str, document_id: str) -> RawResponseDto:
        response = await self._edit_client.get_document(token, document_id)
        assert response.status_code == 200, (
            f"setup: expected the owner to read their own document, got "
            f"status_code={response.status_code}, body={response.text!r}"
        )
        return response
