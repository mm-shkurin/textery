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


# The endpoint set is closed (`ALL_ENDPOINTS`), so the dispatch is a table rather than a
# chain of string comparisons: the DSL name sits next to the client call it means, and a
# name with no entry is caught by one lookup instead of falling off the end of a chain.
_DOCUMENT_SCOPED_CALLS = {
    SUBMIT_AN_INSTRUCTION: lambda client, token, document_id: client.queue_edit(
        token,
        document_id,
        {"message": PROBE_INSTRUCTION, "base_version": PROBE_BASE_VERSION},
        TestData.unique_idempotency_key(),
    ),
    READ_ITS_MESSAGES: lambda client, token, document_id: client.list_messages(
        token, document_id
    ),
    READ_ITS_REVISIONS: lambda client, token, document_id: client.list_revisions(
        token, document_id
    ),
    RESTORE_A_REVISION: lambda client, token, document_id: client.restore_revision(
        token, document_id, PROBE_REVISION_NUMBER
    ),
}


async def invoke(
    client: DocumentEditClient, endpoint: str, token: str, document_id: str
) -> RawResponseDto:
    if endpoint in EDIT_SCOPED_ENDPOINTS:
        return await invoke_with_edit(client, endpoint, token, document_id, PROBE_EDIT_ID)
    call = _DOCUMENT_SCOPED_CALLS.get(endpoint)
    if call is None:
        raise AssertionError(f"unknown endpoint under test: {endpoint!r}")
    return await call(client, token, document_id)


# All three take the same path triple, so the table maps the DSL name straight onto the
# client method that spells that URL.
_EDIT_SCOPED_CALLS = {
    READ_THE_EVENT_STREAM: DocumentEditClient.stream_edit,
    THE_EDIT_STATE_ENDPOINT: DocumentEditClient.get_edit,
    CANCEL_THE_EDIT: DocumentEditClient.cancel_edit,
}


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
    call = _EDIT_SCOPED_CALLS.get(endpoint)
    if call is None:
        raise AssertionError(f"not an edit-scoped endpoint: {endpoint!r}")
    return await call(client, token, document_id, edit_id)


def absent_document_id() -> str:
    return str(uuid.uuid4())
