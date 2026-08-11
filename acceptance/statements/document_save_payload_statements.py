"""Statements for the save payload's wire shape — scenario 2.1's own premise.

Every other row in this scenario observes what the BACKEND did with the request.
This one observes the request, because the property under test lives on the client
side of the wire: `save_document(title=None)` must OMIT the key, and a save carrying
a real title must SEND it. Those shapes are what `SaveDocumentRequestDto`'s
`model_fields_set` reads to tell preserve from clear; collapse them and the
distinction the scenario exists to make is gone before the request is dispatched.

That distinction was previously recorded only in prose -- a comment in
`document_content_only_save_statements.py` (71-73) and one in the client. Two
comments in this scenario have already proved false, so it is made executable here.
"""

from clients.application.recording_application_client import (
    RecordedRequest,
    RecordingApplicationClient,
)

from statements.document_save_payload_wire import (
    ACCESS_TOKEN_ON_THE_WIRE,
    BLANK_TITLED_BODY,
    BLANK_TITLE_ON_THE_WIRE,
    CONTENT_ON_THE_WIRE,
    DISPATCHES_PER_SAVE,
    DOCUMENT_ID_ON_THE_WIRE,
    EXPECTED_AUTHORIZATION,
    NO_TITLE_INTENT_BODY,
    SAVE_METHOD,
    SAVE_PATH,
    TITLED_BODY,
    TITLE_ON_THE_WIRE,
    VERSION_ON_THE_WIRE,
    WHITESPACE_TITLED_BODY,
    WHITESPACE_TITLE_ON_THE_WIRE,
)


class DocumentSavePayloadStatements:
    """Records what `ApplicationClient.save_document` puts on the wire."""

    def __init__(self, recording_client: RecordingApplicationClient) -> None:
        self._recording_client = recording_client

    async def given_a_save_carrying_no_title_intent(self) -> None:
        """`title=None` — the spelling the content-only autosave row uses."""
        await self._given_a_save_titled(None)

    async def given_a_save_carrying_an_explicit_title(self) -> None:
        """The titled spelling the export-filename rows use."""
        await self._given_a_save_titled(TITLE_ON_THE_WIRE)

    async def given_a_save_carrying_a_blank_title(self) -> None:
        """`title=""` -- 3.2's blank value, where a blank-but-present title is the
        whole subject. Literal at `test_export_document_acceptance.py:142`, forwarded
        at `document_blank_title_save_statements.py:74-80`."""
        await self._given_a_save_titled(BLANK_TITLE_ON_THE_WIRE)

    async def given_a_save_carrying_a_whitespace_title(self) -> None:
        """`title="   "` -- 3.2's other blank value, the TRUTHY one. Same parametrize
        line as the empty one (ids `empty_title`/`whitespace_title`)."""
        await self._given_a_save_titled(WHITESPACE_TITLE_ON_THE_WIRE)

    async def _given_a_save_titled(self, title: str | None) -> None:
        """The one save call every row makes, with the ONE argument that differs.

        A parameter rather than four linear bodies, for the same reason
        `BLANK_TITLED_BODY` is written as `NO_TITLE_INTENT_BODY` plus a key: this
        file's entire claim is that the rows are identical requests EXCEPT for
        `title`. Copies state that by resemblance only, and a stray edit to `content`
        or `version` in one would leave the expected-body constants -- all composed
        from `NO_TITLE_INTENT_BODY` -- asserting a difference the arrange never meant
        to make. Here the sameness is structural.
        """
        await self._recording_client.save_document(
            document_id=DOCUMENT_ID_ON_THE_WIRE,
            content=CONTENT_ON_THE_WIRE,
            version=VERSION_ON_THE_WIRE,
            access_token=ACCESS_TOKEN_ON_THE_WIRE,
            title=title,
        )

    def assert_the_title_key_was_omitted_entirely(self) -> None:
        """The absent-key claim, stated against the bytes that were sent. The failure
        message names the null shape explicitly: it is the one regression this row
        exists to catch, and `{'title': None}` and a missing `title` are one character
        apart in a bare dict diff."""
        body = self._the_only_save_request().body
        assert body == NO_TITLE_INTENT_BODY, (
            f"expected a save with no title intent to put exactly "
            f"{NO_TITLE_INTENT_BODY!r} on the wire -- the title key must be OMITTED, "
            "since sending 'title': null instead makes the backend read clear() where "
            "it must read preserve(), silently converting scenario 2.1 into the null "
            f"row, got {body!r}"
        )

    def assert_the_title_key_was_sent(self) -> None:
        """The other half: omission must be CONDITIONAL, not unconditional. Without
        this, a client that dropped `title` in every case would satisfy the assertion
        above -- and the export-filename rows that need the title to reach the backend
        would be the ones to fail, three files away."""
        body = self._the_only_save_request().body
        assert body == TITLED_BODY, (
            f"expected a save carrying a title to put exactly {TITLED_BODY!r} on the "
            "wire -- dropping the title key unconditionally makes the absent-key "
            "assertion vacuous and breaks every row that stores a title through this "
            f"client, got {body!r}"
        )

    def assert_the_blank_title_key_was_sent(self) -> None:
        """The gap the other two rows leave open, one value wide.

        `assert_the_title_key_was_sent` uses a non-empty title, so it survives a
        tidy-up from `if title is not None` to `if title:` -- a MORE plausible edit
        than the dict-literal simplify those rows were written to kill. Under it,
        `title=""` stops being sent and 3.2's request becomes byte-identical to 2.1's:
        3.2 quietly stops testing its own premise and stays green, because both shapes
        preserve. Measured for `if title:` over THIS file: 1 failed, 7 passed, the
        failure being this row. Scoped deliberately: the repo-wide claim made here
        before ("the only assertion in the repo that reds on that edit") was never
        measurable, since a full `-m backend` run needs Docker and without it 60 of
        63 rows fail on infrastructure.

        Covers the EMPTY half of 3.2's two blank values (`["", "   "]`,
        `test_export_document_acceptance.py:142`); one row is right for `if title:`
        specifically, since `"   "` is truthy and survives that edit. The strip-
        normalising variant is what the whitespace row below exists for.
        """
        body = self._the_only_save_request().body
        assert body == BLANK_TITLED_BODY, (
            f"expected a save carrying a blank title to put exactly "
            f"{BLANK_TITLED_BODY!r} on the wire -- the title key must be PRESENT with "
            "an empty value, since dropping it for falsy titles makes scenario 3.2's "
            "request identical to scenario 2.1's, which turns 3.2's blank-title "
            f"premise into a second copy of the absent-key row, got {body!r}"
        )

    def assert_the_whitespace_title_key_was_sent(self) -> None:
        """The gap the blank row leaves open, one mutation over.

        `"   "` is TRUTHY, so it survives `if title:` -- why the blank row was
        correctly one row, and why that reasoning does not extend here. Two tidy-ups
        drop this value, both MEASURED against this file:

          `if title and title.strip()` -- key-absent for `"   "`. 3.2's
          `whitespace_title` parametrization then dispatches a request byte-identical
          to 2.1's and stays green for 2.1's reason. This reds the blank row TOO
          (`""` is falsy), so that row already bounds it: 2 failed, 6 passed.

          `payload["title"] = title.strip()` -- key PRESENT, value normalised to `""`.
          The blank row is blind to it: `"".strip()` is `""`, so its expected body is
          unchanged. 1 failed, 7 passed, and that one is this row. That is what makes
          this assertion non-redundant against its blank sibling, and why the message
          names the spaces rather than the key.

        Stripping decides MEANING, and that belongs to the backend: a client that
        normalises first has answered the question `model_fields_set` exists to ask,
        one layer too early.
        """
        body = self._the_only_save_request().body
        assert body == WHITESPACE_TITLED_BODY, (
            f"expected a save carrying a whitespace-only title to put exactly "
            f"{WHITESPACE_TITLED_BODY!r} on the wire -- the title key must be PRESENT "
            "with its spaces intact, since strip-normalising it away on the client "
            "makes scenario 3.2's whitespace_title request identical to scenario 2.1's "
            "and moves the blank-means-no-title-intent decision off the backend that "
            f"owns it, got {body!r}"
        )

    def assert_the_save_was_dispatched_as_an_authorized_put(self) -> None:
        """The envelope EVERY arrangement's save rides in, asserted by name.

        Formerly inside `_the_only_save_request()`, where it ran in all four body rows
        and destroyed their diagnostic split: a dropped Authorization header reddened
        every one with a message about a header none is named after. One dedicated row
        instead, parametrized over all four `given_*` -- arranging the titled save ALONE
        left 2.1's own content-only save unasserted. Mutation counts: the test class.
        """
        request = self._the_only_save_request()
        assert (request.method, request.path) == (SAVE_METHOD, SAVE_PATH), (
            f"expected the save to be dispatched as {SAVE_METHOD} {SAVE_PATH}, got "
            f"{request.method} {request.path}"
        )
        assert request.authorization == EXPECTED_AUTHORIZATION, (
            f"expected the save to carry {EXPECTED_AUTHORIZATION!r}, got "
            f"{request.authorization!r} -- the token every `given_*` passes must reach "
            "the wire in the Authorization header, or these rows assert the shape of a "
            "body no server would have accepted"
        )

    def _the_only_save_request(self) -> RecordedRequest:
        """Locates the one recorded request. The count check is this accessor's own
        contract -- "the only" is its name -- so it stays; request-line and token
        guarantees moved to the named row above."""
        requests = self._recording_client.recorded_requests
        assert len(requests) == DISPATCHES_PER_SAVE, (
            f"expected the save to dispatch exactly {DISPATCHES_PER_SAVE} request, got "
            f"{len(requests)}: {requests!r}"
        )
        return requests[0]
