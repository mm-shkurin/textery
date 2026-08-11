"""Issues an account owning ONE document that already holds a real chat conversation, for UI 1.2.

1.2 is the mirror of 1.1: same account shape, same single document, same click-through — and a
NON-EMPTY history where 1.1 has none. The two setups are deliberately separate modules rather
than one parameterised by a message count: 1.1's premise is "never edited by AI", established
BY CONSTRUCTION (no edit is ever submitted), and this one's premise is the opposite, established
by spending real edits and reading the transcript back. Folding them together would make the
single most important fact about each Given an argument.

**How the conversation is made, and why there is no cheaper way.** `endpoints.md` lists no
endpoint that writes a message: messages are a side effect of `POST /documents/{id}/ai-edits`.
So the only route to "a document with earlier chat messages" is to submit real edits and wait
for each to reach `done`. That is why this setup is expensive, and why the count is small.

**Overflow is not asserted here.** "The newest message is visible without scrolling" is only a
real assertion on a conversation taller than the panel, but height is a browser fact — this
layer cannot know it. What this layer does is make overflow likely on purpose (see
`SEED_INSTRUCTIONS`); the browser layer then gates its own assertion on the history actually
overflowing, and fails loudly if it does not, rather than passing vacuously.

The instructions, the transcript read-back and the shared response helpers live in
`conversation_transcript.py`. HTTP lives in `DocumentEditClient`, not here (`tdd-rules.md`,
"Acceptance Test Client Layer").
"""

import asyncio
import time
from dataclasses import dataclass

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.frontend.ai_chat.conversation_transcript import (
    CONTEXT,
    OK_STATUS,
    SEED_INSTRUCTIONS,
    assert_status,
    body_of,
    read_the_transcript_back,
)
from statements.frontend.ai_chat.edit_completion_wait import wait_for_edit_to_complete
from statements.frontend.live_auth_session import LiveAuthSession, issue_live_session

DOCUMENT_TYPE = "доклад"
CREATED_STATUS = 201
ACCEPTED_STATUS = 202
NOT_FOUND_STATUS = 404
FIRST_VERSION = 1

DOCUMENT_PARAGRAPH_TEXT = "Введение к докладу, написанное до появления ИИ-правок."
DOCUMENT_CONTENT = f"<p>{DOCUMENT_PARAGRAPH_TEXT}</p>"


@dataclass(frozen=True)
class ConversationAccount:
    """A verified account, the one document it owns, and that document's stored transcript.

    `transcript_texts` is the server's own ordered list — oldest first — and is what the
    browser layer compares the rendered rows against, item for item.
    """

    access_token: str
    refresh_token: str
    document_id: str
    transcript_texts: tuple[str, ...]


def issue_account_with_an_existing_conversation() -> ConversationAccount:
    session = issue_live_session()
    return asyncio.run(_seed_the_conversation(session))


async def _seed_the_conversation(session: LiveAuthSession) -> ConversationAccount:
    client = DocumentEditClient()
    try:
        token = session.access_token
        document_id = await _create_document(client, token)
        await _store_the_starting_content(client, token, document_id)
        for instruction in SEED_INSTRUCTIONS:
            await _submit_one_edit(client, token, document_id, instruction)
        transcript = await read_the_transcript_back(client, token, document_id)
    finally:
        await client.close()
    return ConversationAccount(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        document_id=document_id,
        transcript_texts=transcript,
    )


async def _create_document(client: DocumentEditClient, token: str) -> str:
    response = await client.create_document(
        token, DOCUMENT_TYPE, f"restored-conversation-setup-{time.time_ns()}"
    )
    assert_status(response, CREATED_STATUS, "creating the document")
    body = body_of(response)
    assert (body["document_type"], body["version"]) == (DOCUMENT_TYPE, FIRST_VERSION), (
        f"{CONTEXT}: expected the new document to be a '{DOCUMENT_TYPE}' at version "
        f"{FIRST_VERSION}, got {response.text}"
    )
    return str(body["document_id"])


async def _store_the_starting_content(
    client: DocumentEditClient, token: str, document_id: str
) -> None:
    """`POST /documents` creates an EMPTY document, and an edit needs something to edit."""
    response = await client.save_document(token, document_id, DOCUMENT_CONTENT, FIRST_VERSION)
    assert_status(response, OK_STATUS, "saving the starting content")


async def _submit_one_edit(
    client: DocumentEditClient, token: str, document_id: str, instruction: str
) -> None:
    """Queue one edit at the document's CURRENT version and wait for it to finish.

    The version is re-read rather than counted forward from `FIRST_VERSION`: a completed edit
    writes a new version, so the second submission's `base_version` is not the first's, and a
    stale one meets a CAS conflict that records no assistant reply — leaving a transcript
    shorter than this setup thinks it made, with nothing to say so.
    """
    base_version = await _current_version_of(client, token, document_id)
    response = await client.queue_edit(
        token,
        document_id,
        {"message": instruction, "base_version": base_version},
        f"restored-conversation-edit-{time.time_ns()}",
    )
    _assert_the_edit_was_queued(response, instruction)
    await wait_for_edit_to_complete(
        client,
        token,
        document_id,
        str(body_of(response)["edit_id"]),
        CONTEXT,
        "Only a completed edit records the assistant's reply — this scenario's whole Given "
        "is that both sides of each turn are in the transcript",
    )


def _assert_the_edit_was_queued(response: RawResponseDto, instruction: str) -> None:
    """Demand the 202, and name the ONE cause that is true today when it is a 404.

    A bare "expected 202, got 404" sends the reader hunting for a wrong id or a lost token,
    when the real answer is that the route does not exist: `main.py` registers four routers
    (generation, auth, oauth, document) and `document_edit_router` is not among them. This is
    the FIRST failure a live run of scenario 1.2 meets and it will meet it on every run until
    green-selenium wires the router, so the diagnosis belongs in the message rather than in a
    comment in the test file.
    """
    if response.status_code == NOT_FOUND_STATUS:
        raise AssertionError(
            f"{CONTEXT}: queueing the edit '{instruction[:40]}...' got "
            f"{NOT_FOUND_STATUS}, not {ACCEPTED_STATUS}. POST /documents/<id>/ai-edits is "
            f"UNREGISTERED — main.py mounts only the generation, auth, oauth and document "
            f"routers, not document_edit_router — and `endpoints.md` lists no other endpoint "
            f"that writes a chat message, so this Given cannot be reached until it is "
            f"mounted: {response.text}"
        )
    assert_status(response, ACCEPTED_STATUS, f"queueing the edit '{instruction[:40]}...'")


async def _current_version_of(client: DocumentEditClient, token: str, document_id: str) -> int:
    response = await client.get_document(token, document_id)
    assert_status(response, OK_STATUS, "reading the document's current version")
    return int(body_of(response)["version"])
