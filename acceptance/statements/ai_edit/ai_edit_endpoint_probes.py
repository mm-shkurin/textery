import uuid

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit.ai_edit_endpoints import (
    CANCEL_THE_EDIT,
    EDIT_SCOPED_ENDPOINTS,
    READ_ITS_MESSAGES,
    READ_ITS_REVISIONS,
    READ_THE_EVENT_STREAM,
    RESTORE_A_REVISION,
    SUBMIT_AN_INSTRUCTION,
    THE_EDIT_STATE_ENDPOINT,
)
from statements.test_data import TestData

# The edit and revision identifiers below are deliberately well-formed but
# unrelated to any real row: the guard under test must answer on the path
# document id alone, before it ever looks at the child identifier.
PROBE_EDIT_ID = "3f1a5c26-0f0f-4a3b-9a5b-1c2d3e4f5a6b"
PROBE_REVISION_NUMBER = "1"
PROBE_INSTRUCTION = "Сократи введение до одного абзаца."
PROBE_BASE_VERSION = 1


async def invoke(
    client: DocumentEditClient, endpoint: str, token: str, document_id: str
) -> RawResponseDto:
    if endpoint == SUBMIT_AN_INSTRUCTION:
        return await client.queue_edit(
            token,
            document_id,
            {"message": PROBE_INSTRUCTION, "base_version": PROBE_BASE_VERSION},
            TestData.unique_idempotency_key(),
        )
    if endpoint in EDIT_SCOPED_ENDPOINTS:
        return await invoke_with_edit(client, endpoint, token, document_id, PROBE_EDIT_ID)
    if endpoint == READ_ITS_MESSAGES:
        return await client.list_messages(token, document_id)
    if endpoint == READ_ITS_REVISIONS:
        return await client.list_revisions(token, document_id)
    if endpoint == RESTORE_A_REVISION:
        return await client.restore_revision(token, document_id, PROBE_REVISION_NUMBER)
    raise AssertionError(f"unknown endpoint under test: {endpoint!r}")


async def invoke_with_edit(
    client: DocumentEditClient,
    endpoint: str,
    token: str,
    document_id: str,
    edit_id: str,
) -> RawResponseDto:
    """Invoke one of the three edit-scoped endpoints with a caller-chosen edit id.

    Scenario 1.1 passes an id that matches no row; scenario 1.2 passes a REAL edit id
    that belongs to another document of the same owner. The dispatch is shared so both
    scenarios exercise the same URLs — a divergence in path shape between them would
    let one pass while the other is silently probing something else.
    """
    if endpoint == READ_THE_EVENT_STREAM:
        return await client.stream_edit(token, document_id, edit_id)
    if endpoint == THE_EDIT_STATE_ENDPOINT:
        return await client.get_edit(token, document_id, edit_id)
    if endpoint == CANCEL_THE_EDIT:
        return await client.cancel_edit(token, document_id, edit_id)
    raise AssertionError(f"not an edit-scoped endpoint: {endpoint!r}")


def absent_document_id() -> str:
    return str(uuid.uuid4())
