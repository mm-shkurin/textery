"""Issues an account owning ONE document with real content and no AI history, for UI 1.1.

"A document that has never been edited by AI" is established BY CONSTRUCTION, not by a read:
the account is brand new, the document is created inside this function, and no `POST
/ai-edits` is ever submitted for it, so no message and no revision can exist. Asserting the
emptiness over `GET /messages` was considered and rejected — it would put the scenario's
Given behind a route that answers 404 today, so a missing endpoint would surface as a setup
failure and hide the UI facts this scenario exists to pin.

The document is CREATED EMPTY (`CreateDocument`: "Create an empty manual document"), so the
setup writes content into it with story 5's `PUT /documents/{id}`. Without that write the
scenario's first Then — the content is shown in the editor — would assert an empty editor
against an empty document and pass no matter what the route rendered.

HTTP lives in `DocumentEditClient`, not here (`tdd-rules.md`, "Acceptance Test Client Layer");
this file owns only the POLICY: what the document must contain and what proves it was stored.
"""

import asyncio
import time
from dataclasses import dataclass

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.frontend.live_auth_session import LiveAuthSession, issue_live_session

DOCUMENT_TYPE = "доклад"

CREATED_STATUS = 201
OK_STATUS = 200

FIRST_VERSION = 1
VERSION_AFTER_SETUP_SAVE = 2

# The text a human would read on the page. Kept apart from the markup below because the two
# are asserted in different places and against different things: the browser layer compares
# the EDITOR'S TEXT to this, while the setup compares the STORED HTML to `DOCUMENT_CONTENT`.
DOCUMENT_PARAGRAPH_TEXT = "Введение к докладу, написанное до появления ИИ-правок."

# Wrapped in a `<p>`, not sent as a bare line, for two independent reasons: the save path
# sanitizes HTML, so a shape that survives sanitization unchanged is what makes the
# byte-equality assertion below meaningful; and Tiptap parses the stored content through its
# schema, where a paragraph is a node it keeps rather than one it has to infer.
DOCUMENT_CONTENT = f"<p>{DOCUMENT_PARAGRAPH_TEXT}</p>"


@dataclass(frozen=True)
class PristineDocumentAccount:
    """A verified account and the single, never-AI-edited document it owns."""

    access_token: str
    refresh_token: str
    document_id: str


def issue_account_with_a_document_never_edited_by_ai() -> PristineDocumentAccount:
    session = issue_live_session()
    return asyncio.run(_create_the_document(session))


async def _create_the_document(session: LiveAuthSession) -> PristineDocumentAccount:
    client = DocumentEditClient()
    try:
        document_id = await _create_empty_document(client, session.access_token)
        await _store_the_content(client, session.access_token, document_id)
        await _assert_the_content_is_readable_back(client, session.access_token, document_id)
    finally:
        await client.close()
    return PristineDocumentAccount(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        document_id=document_id,
    )


async def _create_empty_document(client: DocumentEditClient, token: str) -> str:
    idempotency_key = f"pristine-document-setup-{time.time_ns()}"
    response = await client.create_document(token, DOCUMENT_TYPE, idempotency_key)
    _assert_status(response, CREATED_STATUS, "creating the document")
    body = _body_of(response)
    # `version` is asserted, not assumed: the save below submits `version=FIRST_VERSION`, and
    # a document created at another version would meet a 409 and store nothing. There is no
    # title to assert: `create_document`'s third argument is the `Idempotency-Key` HEADER, and
    # `CreateDocumentRequestDto` accepts `document_type` alone, so the response carries no
    # `title` field at all. The browser layer pins the documents-list row by
    # `data-document-id`, so nothing downstream needs a title either.
    assert (body["document_type"], body["version"]) == (
        DOCUMENT_TYPE,
        FIRST_VERSION,
    ), (
        f"pristine-document setup: expected the new document to be a '{DOCUMENT_TYPE}' at "
        f"version {FIRST_VERSION}, got {response.text}"
    )
    return str(body["document_id"])


async def _store_the_content(client: DocumentEditClient, token: str, document_id: str) -> None:
    response = await client.save_document(token, document_id, DOCUMENT_CONTENT, FIRST_VERSION)
    _assert_status(response, OK_STATUS, "saving the document content")
    body = _body_of(response)
    assert (body["content"], body["version"]) == (DOCUMENT_CONTENT, VERSION_AFTER_SETUP_SAVE), (
        f"pristine-document setup: expected the save to store '{DOCUMENT_CONTENT}' at version "
        f"{VERSION_AFTER_SETUP_SAVE}, got {response.text}"
    )


async def _assert_the_content_is_readable_back(
    client: DocumentEditClient, token: str, document_id: str
) -> None:
    """Re-read over the SAME endpoint the editor route reads on mount.

    The save response alone would not do: it is built from the entity the write returned, and
    a store that dropped the content on the way to the database would still answer with it.
    This read is what proves the browser will be served the content the Then names.
    """
    response = await client.get_document(token, document_id)
    _assert_status(response, OK_STATUS, "re-reading the stored document")
    stored = _body_of(response)["content"]
    assert stored == DOCUMENT_CONTENT, (
        f"pristine-document setup: expected GET /documents/{document_id} — the read the "
        f"editor route itself issues — to return '{DOCUMENT_CONTENT}', got '{stored}'"
    )


def _assert_status(response: RawResponseDto, expected: int, what: str) -> None:
    assert response.status_code == expected, (
        f"pristine-document setup: {what} expected {expected}, "
        f"got {response.status_code}: {response.text}"
    )


def _body_of(response: RawResponseDto) -> dict:
    assert response.body is not None, (
        f"pristine-document setup: expected a JSON object body, got {response.text}"
    )
    return response.body
