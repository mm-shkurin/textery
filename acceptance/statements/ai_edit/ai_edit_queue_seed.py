"""Queueing a REAL edit through the public endpoint, shared by scenarios 1.2 and 1.3.

Scenario 1.2 needs the queued edit as its probe subject; scenario 1.3 needs it only as
the thing that records a revision. Both need the identical seed, and both need it
strictly asserted — an edit that was not actually accepted as `queued` seeds a scenario
that no longer means what its name says. One copy, so the seed's expectations are stated
in one place and cannot drift between the two guard scenarios.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit.ai_edit_edit_states import QUEUED_STATUS
from statements.ai_edit.ai_edit_endpoint_probes import PROBE_INSTRUCTION
from statements.ai_edit.ai_edit_http_status import ACCEPTED_STATUS
from statements.response_assertions import assert_is_valid_uuid
from statements.test_data import TestData

ACCEPTED_FIELDS = {"edit_id", "status"}


@dataclass(frozen=True)
class QueuedEdit:
    """The accepted edit, plus the window the queue call was bracketed in.

    The bracket lets a server-set `created_at` be bounded to the interval the test
    itself observed rather than merely checked for presence.
    """

    edit_id: str
    queued_before: datetime
    queued_after: datetime


async def queue_edit_on(
    client: DocumentEditClient, token: str, document_id: str
) -> QueuedEdit:
    """Queue one edit on `document_id` through the public endpoint.

    `base_version` is the literal first version, which `create_document_owned_by` has
    just pinned — not a value read back at runtime, so the request stays dumb.
    """
    before = datetime.now(timezone.utc)
    response = await client.queue_edit(
        token,
        document_id,
        {"message": PROBE_INSTRUCTION, "base_version": seed.FIRST_VERSION},
        TestData.unique_idempotency_key(),
    )
    after = datetime.now(timezone.utc)
    _assert_accepted_as_queued(response, document_id)
    return QueuedEdit(
        edit_id=str((response.body or {})["edit_id"]),
        queued_before=before,
        queued_after=after,
    )


def _assert_accepted_as_queued(response: RawResponseDto, document_id: str) -> None:
    assert response.status_code == ACCEPTED_STATUS, (
        f"setup: expected {ACCEPTED_STATUS} queueing an edit on the caller's first "
        f"document {document_id}, got status_code={response.status_code}, "
        f"body={response.text!r}"
    )
    body = response.body or {}
    assert set(body) == ACCEPTED_FIELDS, (
        f"setup: expected the accepted edit to carry exactly "
        f"{sorted(ACCEPTED_FIELDS)}, got {sorted(body)} in body={response.text!r}"
    )
    assert_is_valid_uuid(body.get("edit_id"), field_name="edit_id")
    # documents_ai_edits_create.yaml: on a FIRST submission status is server-set to
    # exactly `queued`. The idempotency key is fresh, so this IS a first submission —
    # any other value means the seeded edit is not the one the scenario describes.
    assert body.get("status") == QUEUED_STATUS, (
        f"setup: a first submission is server-set to {QUEUED_STATUS!r}, got "
        f"status={body.get('status')!r} in body={response.text!r}"
    )
