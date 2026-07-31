from clients.application.application_client import ApplicationClient
from clients.application.document_edit_client import DocumentEditClient
from statements.ai_edit import ai_edit_cross_revision_assertions as guard
from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit import ai_edit_document_state as state
from statements.ai_edit import ai_edit_revision_expectations as expected
from statements.ai_edit import ai_edit_revision_seed as revision_seed
from statements.ai_edit.ai_edit_cross_revision_assertions import AFTERMATH_CONTEXT
from statements.ai_edit.ai_edit_cross_revision_probes import (
    CrossRevisionAftermath,
    CrossRevisionProbe,
    CrossRevisionSetup,
)
from statements.authenticated_account import register_verify_and_login

BASELINE_CONTEXT = "when the scenario's baseline was captured, before the probe"


class AiEditCrossRevisionStatements:
    """Scenario 1.3 — a revision of one document is not found under another of the same
    owner. Everything is seeded through the public endpoints; no row is hand-built.
    """

    def __init__(self, client: ApplicationClient, edit_client: DocumentEditClient):
        self._client = client
        self._edit_client = edit_client

    async def given_a_revision_recorded_on_the_first_of_two_owned_documents(
        self,
    ) -> CrossRevisionSetup:
        owner = await register_verify_and_login(self._client)
        first_id, second_id = await seed.create_two_documents_owned_by(
            self._edit_client, owner.access_token
        )
        recorded = await revision_seed.record_a_revision_on(
            self._edit_client, owner.access_token, first_id
        )
        first_before = await self._read_state(
            owner.access_token, first_id, BASELINE_CONTEXT
        )
        second_before = await self._read_state(
            owner.access_token, second_id, BASELINE_CONTEXT
        )
        # The premise is asserted, not assumed: the revision exists on the FIRST
        # document and on neither the second nor nowhere at all.
        expected.assert_is_a_once_ai_edited_document(
            first_before, recorded.window, BASELINE_CONTEXT
        )
        expected.assert_is_a_never_edited_document(second_before, BASELINE_CONTEXT)
        return CrossRevisionSetup(
            owner_token=owner.access_token,
            revision_number=recorded.revision_number,
            seed_window=recorded.window,
            first_before=first_before,
            second_before=second_before,
        )

    async def when_the_revision_is_restored_under_the_second_documents_path(
        self, setup: CrossRevisionSetup
    ) -> CrossRevisionProbe:
        refusal = await self._edit_client.restore_revision(
            setup.owner_token, setup.second_document_id, str(setup.revision_number)
        )
        return CrossRevisionProbe(refusal=refusal, setup=setup)

    def then_the_request_is_refused_as_not_found(
        self, probe: CrossRevisionProbe
    ) -> None:
        guard.assert_refused_as_not_found(probe)

    async def then_no_new_version_is_created_on_either_document(
        self, probe: CrossRevisionProbe
    ) -> None:
        """Read both documents back and pin them. One Then clause, one DSL call.

        The read-back used to be a separate `then_`-named step that asserted nothing and
        handed its result through the test class — an action wearing a Then name, the
        same mislabel scenario 1.2's review fixed.
        """
        aftermath = CrossRevisionAftermath(
            first_after=await self._read_state(
                probe.owner_token, probe.first_document_id, AFTERMATH_CONTEXT
            ),
            second_after=await self._read_state(
                probe.owner_token, probe.second_document_id, AFTERMATH_CONTEXT
            ),
        )
        guard.assert_no_new_version_on_either_document(probe, aftermath)

    async def _read_state(
        self, token: str, document_id: str, context: str
    ) -> state.DocumentState:
        return await state.read_state(self._edit_client, token, document_id, context)
