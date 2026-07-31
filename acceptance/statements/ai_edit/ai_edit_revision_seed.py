"""Recording a REAL revision on a document, through the public endpoints only.

A revision exists on a document exactly when a mutation applied to it — there is no
endpoint that writes one directly, and the spec puts the first one behind an AI edit
(01_API_Tests_Apply.md §7.2). So the seed queues an edit, waits for its terminal state,
and reads the recorded revision number back off the state endpoint.

The number is not merely well-formed, it is EXACT. `documents_revisions_list.yaml` fixes
what the first mutation of a never-edited document does: it writes TWO revisions in one
transaction — revision 1 carrying the pre-mutation content with source `manual`, then
revision 2 carrying the result. So one applied AI edit on a freshly created document
records revision 2, and nothing else. A `>= 1` check would have accepted revision 1 —
i.e. a backend that wrote only the baseline and never applied the edit at all — and the
cross-document refusal would then be trivially correct for the wrong reason.

The reported number is cross-checked against the document's own revision page by the
caller, which pins that page whole (`ai_edit_revision_expectations`). That is strictly
stronger than the membership check this module used to do, and it lives in one place.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit import ai_edit_queue_seed as queue_seed
from statements.ai_edit.ai_edit_edit_states import (
    DONE_STATUS,
    NON_TERMINAL_STATES,
    TERMINAL_STATES,
)
from statements.ai_edit.ai_edit_http_status import OK_STATUS
from statements.ai_edit.ai_edit_response_fields import DONE_EDIT_FIELDS
from statements.ai_edit.ai_edit_vocabulary import (
    SEEDED_REVISION_NUMBER,
    VERSION_AFTER_ONE_AI_EDIT,
)
from statements.response_assertions import assert_iso_timestamp_within

APPLY_TIMEOUT_SECONDS = 20.0
POLL_INTERVAL_SECONDS = 0.25
TERMINAL_EVENT_SEQ = 1


@dataclass(frozen=True)
class RecordedRevision:
    """The revision an applied edit wrote, and the window the whole seed ran in.

    The window bounds the `created_at` of both recorded revisions to the interval the
    test itself observed, rather than leaving them merely present.
    """

    revision_number: int
    window: tuple[datetime, datetime]


async def record_a_revision_on(
    client: DocumentEditClient, token: str, document_id: str
) -> RecordedRevision:
    before = datetime.now(timezone.utc)
    queued = await queue_seed.queue_edit_on(client, token, document_id)
    revision_number = await _await_the_applied_revision_number(
        client, token, document_id, queued
    )
    after = datetime.now(timezone.utc)
    return RecordedRevision(revision_number=revision_number, window=(before, after))


async def _await_the_applied_revision_number(
    client: DocumentEditClient,
    token: str,
    document_id: str,
    queued: queue_seed.QueuedEdit,
) -> int:
    """Poll the edit's own state endpoint until it is terminal, then require `done`.

    Bounded rather than unbounded: a never-terminating edit must fail the setup with a
    message naming the last state seen, not hang the suite.
    """
    edit_id = queued.edit_id
    deadline = asyncio.get_event_loop().time() + APPLY_TIMEOUT_SECONDS
    body: dict = {}
    response: RawResponseDto | None = None
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get_edit(token, document_id, edit_id)
        assert response.status_code == OK_STATUS, (
            f"setup: expected {OK_STATUS} reading the seeded edit {edit_id} under its "
            f"own document {document_id}, got status_code={response.status_code}, "
            f"body={response.text!r}"
        )
        body = response.body or {}
        if body.get("status") in TERMINAL_STATES:
            break
        assert body.get("status") in NON_TERMINAL_STATES, (
            f"setup: the seeded edit {edit_id} reported the unknown state "
            f"{body.get('status')!r}; expected one of "
            f"{NON_TERMINAL_STATES + TERMINAL_STATES}. body={response.text!r}"
        )
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    _assert_applied_as_done(body, response, queued, document_id)
    return SEEDED_REVISION_NUMBER


def _assert_applied_as_done(
    body: dict,
    response: RawResponseDto | None,
    queued: queue_seed.QueuedEdit,
    document_id: str,
) -> None:
    text = response.text if response else None
    edit_id = queued.edit_id
    assert body.get("status") == DONE_STATUS, (
        f"setup: the seeded edit {edit_id} had to reach {DONE_STATUS!r} within "
        f"{APPLY_TIMEOUT_SECONDS}s so that a revision is recorded on document "
        f"{document_id}; last state was {body.get('status')!r} in body={text!r}"
    )
    assert set(body) == DONE_EDIT_FIELDS, (
        f"setup: expected the {DONE_STATUS!r} edit {edit_id} to carry exactly "
        f"{sorted(DONE_EDIT_FIELDS)}, got {sorted(body)} in body={text!r}"
    )
    assert body.get("edit_id") == edit_id, (
        f"setup: expected the state endpoint to answer for the seeded edit {edit_id}, "
        f"got edit_id={body.get('edit_id')!r} in body={text!r}"
    )
    # `changed` false means the edit applied nothing, in which case the spec makes
    # version and revision_number null and NO revision is recorded — the scenario would
    # have no subject at all. It is the premise, so it is asserted, not assumed.
    assert body.get("changed") is True, (
        f"setup: the seeded edit {edit_id} had to actually change document "
        f"{document_id} for a revision to be recorded; got changed="
        f"{body.get('changed')!r} in body={text!r}"
    )
    observed = {key: body.get(key) for key in ("version", "revision_number")}
    expected = {
        "version": VERSION_AFTER_ONE_AI_EDIT,
        "revision_number": SEEDED_REVISION_NUMBER,
    }
    assert observed == expected, (
        f"setup: one applied AI edit on a freshly created document leaves it at "
        f"{expected} — the first mutation writes the pre-edit baseline as revision 1 and "
        f"its own result as revision {SEEDED_REVISION_NUMBER} "
        f"(documents_revisions_list.yaml). Got {observed} in body={text!r}"
    )
    # The edit was created by the queue call the seed itself bracketed, so its
    # `created_at` is boundable to that window — not merely present.
    assert_iso_timestamp_within(
        body.get("created_at"), "created_at", queued.queued_before, queued.queued_after
    )
    # `last_seq` counts the events the model's streaming produced, so its exact value is
    # the one field here the test cannot name. It is still bounded below: a `done` edit
    # has written at least its own terminal event, so the highest seq is at least 1.
    last_seq = body.get("last_seq")
    assert isinstance(last_seq, int) and not isinstance(last_seq, bool), (
        f"setup: documents_ai_edits_get.yaml carries an integer last_seq; got "
        f"{last_seq!r} in body={text!r}"
    )
    assert last_seq >= TERMINAL_EVENT_SEQ, (
        f"setup: a {DONE_STATUS!r} edit has written at least its terminal event, so "
        f"last_seq is at least {TERMINAL_EVENT_SEQ}; got {last_seq} in body={text!r}"
    )
