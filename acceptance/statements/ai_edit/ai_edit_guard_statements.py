from clients.application.application_client import ApplicationClient
from clients.application.document_edit_client import DocumentEditClient
from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit import ai_edit_endpoint_probes as probes
from statements.ai_edit import ai_edit_guard_assertions as guard
from statements.ai_edit.ai_edit_guard_probes import (
    DocumentAftermath,
    GuardProbe,
    GuardSetup,
)
from statements.authenticated_account import register_verify_and_login


class AiEditGuardStatements:
    def __init__(self, client: ApplicationClient, edit_client: DocumentEditClient):
        self._client = client
        self._edit_client = edit_client

    async def given_a_foreign_document_and_an_absent_document_id(self) -> GuardSetup:
        caller = await register_verify_and_login(self._client)
        owner = await register_verify_and_login(self._client)
        foreign_document_id = await seed.create_document_owned_by(
            self._edit_client, owner.access_token
        )
        return GuardSetup(
            caller_token=caller.access_token,
            owner_token=owner.access_token,
            foreign_document_id=foreign_document_id,
            absent_document_id=probes.absent_document_id(),
            document_before=await seed.read_document(
                self._edit_client, owner.access_token, foreign_document_id
            ),
        )

    async def when_the_endpoint_is_invoked_against_both(
        self, setup: GuardSetup, endpoint: str
    ) -> GuardProbe:
        foreign = await probes.invoke(
            self._edit_client, endpoint, setup.caller_token, setup.foreign_document_id
        )
        absent = await probes.invoke(
            self._edit_client, endpoint, setup.caller_token, setup.absent_document_id
        )
        return GuardProbe(
            endpoint=endpoint, foreign=foreign, absent=absent, setup=setup
        )

    async def when_the_owner_reads_the_document_aftermath(
        self, probe: GuardProbe
    ) -> DocumentAftermath:
        """An ACTION, not a Then: three HTTP reads, asserting nothing of its own.

        It carried a `then_` name while the steps that actually assert carried `assert_`
        ones — the mislabel scenarios 1.2 and 1.3 already fixed. Naming follows what the
        step does.
        """
        return DocumentAftermath(
            messages=await self._edit_client.list_messages(
                probe.owner_token, probe.foreign_document_id
            ),
            revisions=await self._edit_client.list_revisions(
                probe.owner_token, probe.foreign_document_id
            ),
            document_after=await seed.read_document(
                self._edit_client, probe.owner_token, probe.foreign_document_id
            ),
        )

    def then_both_are_refused_as_not_found(self, probe: GuardProbe) -> None:
        guard.assert_both_refused_as_not_found(probe)

    def then_the_two_response_bodies_are_byte_identical(self, probe: GuardProbe) -> None:
        guard.assert_response_bodies_byte_identical(probe)

    def then_no_edit_revision_or_message_is_created(
        self, probe: GuardProbe, aftermath: DocumentAftermath
    ) -> None:
        guard.assert_no_edit_revision_or_message_created(probe, aftermath)
