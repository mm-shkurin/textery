from clients.application.application_client import ApplicationClient
from clients.application.document_edit_client import DocumentEditClient
from statements.ai_edit import ai_edit_cross_document_assertions as guard
from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit import ai_edit_endpoint_probes as probes
from statements.ai_edit import ai_edit_queue_seed as queue_seed
from statements.ai_edit.ai_edit_cross_document_probes import (
    CrossDocumentProbe,
    CrossDocumentSetup,
)
from statements.authenticated_account import register_verify_and_login


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
        first_document_id, second_document_id = await seed.create_two_documents_owned_by(
            self._edit_client, owner.access_token
        )
        # A REAL edit, queued through the shared public-endpoint seed. The scenario only
        # bites when the edit id exists: a fabricated id would be refused by any handler
        # that merely fails to find it, and the test would pass without the path document
        # id ever having been consulted.
        queued = await queue_seed.queue_edit_on(
            self._edit_client, owner.access_token, first_document_id
        )
        return CrossDocumentSetup(
            owner_token=owner.access_token,
            first_document_id=first_document_id,
            second_document_id=second_document_id,
            edit_id=queued.edit_id,
            queued_before=queued.queued_before,
            queued_after=queued.queued_after,
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

    def then_the_request_is_refused_as_not_found(
        self, probe: CrossDocumentProbe
    ) -> None:
        guard.assert_refused_as_not_found(probe)

    async def then_the_edit_is_unchanged_under_its_own_document(
        self, probe: CrossDocumentProbe
    ) -> None:
        """Read the edit back under its rightful document and pin it. One Then clause.

        The read-back used to be a separate `then_`-named step that asserted nothing and
        handed its result through the test class — an action wearing a Then name.
        """
        edit_state_after = await self._edit_client.get_edit(
            probe.setup.owner_token, probe.first_document_id, probe.edit_id
        )
        guard.assert_the_edit_survived_under_its_own_document(probe, edit_state_after)
