"""Statements for the save payload's wire shape — scenario 2.1's own premise.

Every other row in this scenario observes what the BACKEND did with the request.
This one observes the request, because the property under test lives on the client
side of the wire: `save_document(title=None)` must OMIT the key, and a save carrying
a real title must SEND it. Those two shapes are what `SaveDocumentRequestDto`'s
`model_fields_set` reads to tell preserve from clear; collapse them and the
distinction the scenario exists to make is gone before the request is dispatched.

The distinction is currently recorded only in prose — a comment in
`document_content_only_save_statements.py` (lines 61-70) and one in the client itself.
Two comments in this scenario have already turned out to be false, so the claim is
made executable here.
"""

from clients.application.recording_application_client import (
    RecordedRequest,
    RecordingApplicationClient,
)

# Stand-ins, never resolved by anything: no server sees these, and the subject is the
# body's shape, not any identity behind it. Values still differ from each other so a
# mixed-up argument reads as a mismatch rather than as a coincidence.
DOCUMENT_ID_ON_THE_WIRE = "00000000-0000-0000-0000-00000000d0c5"
ACCESS_TOKEN_ON_THE_WIRE = "recorded-access-token"
# Cyrillic on purpose, matching the scenario's own title fixture: the recorded body is
# read back from serialized bytes, so a JSON encoding regression is visible here too.
CONTENT_ON_THE_WIRE = "Тело, сохранённое без заголовка"
TITLE_ON_THE_WIRE = "Заголовок, отправленный явно"
VERSION_ON_THE_WIRE = 2

# The request line a save must use. Pinned so the body being asserted is provably the
# save request: the recorder answers every request, so without this the assertions
# would key off dispatch position alone.
SAVE_METHOD = "PUT"
SAVE_PATH = f"/api/v1/documents/{DOCUMENT_ID_ON_THE_WIRE}"
# One `given_*` is one `save_document` call, so one request. Asserted exactly rather
# than "at least one": a client that retried or double-dispatched would otherwise be
# invisible behind a read of the last entry.
DISPATCHES_PER_SAVE = 1

# The exact body of a save that carries NO title intent. A whole-body equality, not a
# `"title" not in body`: membership alone still passes if the client starts dropping
# `content` or mangling `version`, and this is the only row that watches the save
# payload at all.
NO_TITLE_INTENT_BODY = {"content": CONTENT_ON_THE_WIRE, "version": VERSION_ON_THE_WIRE}
# The exact body of a save that carries a title.
TITLED_BODY = {**NO_TITLE_INTENT_BODY, "title": TITLE_ON_THE_WIRE}


class DocumentSavePayloadStatements:
    """Records what `ApplicationClient.save_document` puts on the wire."""

    def __init__(self, recording_client: RecordingApplicationClient) -> None:
        self._recording_client = recording_client

    async def given_a_save_carrying_no_title_intent(self) -> None:
        """`title=None` — the spelling the content-only autosave row uses."""
        await self._recording_client.save_document(
            document_id=DOCUMENT_ID_ON_THE_WIRE,
            content=CONTENT_ON_THE_WIRE,
            version=VERSION_ON_THE_WIRE,
            access_token=ACCESS_TOKEN_ON_THE_WIRE,
            title=None,
        )

    async def given_a_save_carrying_an_explicit_title(self) -> None:
        """The titled spelling the export-filename rows use."""
        await self._recording_client.save_document(
            document_id=DOCUMENT_ID_ON_THE_WIRE,
            content=CONTENT_ON_THE_WIRE,
            version=VERSION_ON_THE_WIRE,
            access_token=ACCESS_TOKEN_ON_THE_WIRE,
            title=TITLE_ON_THE_WIRE,
        )

    def assert_the_title_key_was_omitted_entirely(self) -> None:
        """The absent-key claim, stated against the bytes that were sent.

        The failure message names the null shape explicitly because that is the one
        regression this row exists to catch, and because `{'title': None}` and a
        missing `title` are one character apart in a bare dict diff.
        """
        body = self._the_only_save_request().body
        assert body == NO_TITLE_INTENT_BODY, (
            f"expected a save with no title intent to put exactly "
            f"{NO_TITLE_INTENT_BODY!r} on the wire -- the title key must be OMITTED, "
            "since sending 'title': null instead makes the backend read clear() where "
            "it must read preserve(), silently converting scenario 2.1 into the null "
            f"row, got {body!r}"
        )

    def assert_the_title_key_was_sent(self) -> None:
        """The other half: omission must be CONDITIONAL, not unconditional.

        Without this, a client that dropped `title` in every case would satisfy the
        assertion above -- and the export-filename rows that depend on the title
        reaching the backend would be the ones to fail, three files away.
        """
        body = self._the_only_save_request().body
        assert body == TITLED_BODY, (
            f"expected a save carrying a title to put exactly {TITLED_BODY!r} on the "
            "wire -- dropping the title key unconditionally makes the absent-key "
            "assertion vacuous and breaks every row that stores a title through this "
            f"client, got {body!r}"
        )

    def _the_only_save_request(self) -> RecordedRequest:
        requests = self._recording_client.recorded_requests
        assert len(requests) == DISPATCHES_PER_SAVE, (
            f"expected the save to dispatch exactly {DISPATCHES_PER_SAVE} request, got "
            f"{len(requests)}: {requests!r}"
        )
        request = requests[0]
        assert (request.method, request.path) == (SAVE_METHOD, SAVE_PATH), (
            f"expected the save to be dispatched as {SAVE_METHOD} {SAVE_PATH}, got "
            f"{request.method} {request.path}"
        )
        return request
