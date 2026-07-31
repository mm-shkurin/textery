"""Seeding a document through the public create endpoint, shared by scenarios 1.1/1.2.

Both scenarios need "a document owned by this account" and both were creating it with
their own private copy of the same call, the same status assert and the same id check.
One copy means one place for the seed's expectations to be stated strictly.

The create response is pinned FIELD BY FIELD, not merely to 201 + a well-formed id.
Every field but the id is a value the test chose or the spec fixes, so a backend that
returned someone else's document, a non-empty draft, or a version other than 1 would
otherwise seed a scenario that no longer means what its name says.
"""

from datetime import datetime, timezone

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit.ai_edit_http_status import CREATED_STATUS, OK_STATUS
from statements.response_assertions import (
    assert_iso_timestamp_within,
    assert_is_valid_uuid,
)
from statements.test_data import TestData

DOCUMENT_TYPE = "доклад"
DRAFT_STATUS = "draft"
EMPTY_CONTENT = ""
FIRST_VERSION = 1

DOCUMENT_FIELDS = {
    "document_id",
    "document_type",
    "status",
    "content",
    "version",
    "created_at",
    "updated_at",
}


async def create_document_owned_by(client: DocumentEditClient, token: str) -> str:
    """Create one document for `token`'s account and return its id."""
    before = datetime.now(timezone.utc)
    response = await client.create_document(
        token, DOCUMENT_TYPE, TestData.unique_idempotency_key()
    )
    after = datetime.now(timezone.utc)
    assert response.status_code == CREATED_STATUS, (
        f"setup: expected {CREATED_STATUS} creating a document for the account under "
        f"test, got status_code={response.status_code}, body={response.text!r}"
    )
    body = response.body or {}
    _assert_is_a_freshly_created_draft(body, response, before, after)
    return str(body["document_id"])


def _assert_is_a_freshly_created_draft(
    body: dict, response: RawResponseDto, before: datetime, after: datetime
) -> None:
    assert set(body) == DOCUMENT_FIELDS, (
        f"setup: expected the created document to carry exactly {sorted(DOCUMENT_FIELDS)}, "
        f"got {sorted(body)} in body={response.text!r}"
    )
    # A well-formed id, not merely a present one: every probe interpolates this into its
    # path, and a junk id would make the refusals 404 for the wrong reason — the guard
    # would look green while never having been exercised.
    assert_is_valid_uuid(body.get("document_id"), field_name="document_id")
    chosen = {key: body.get(key) for key in ("document_type", "status", "content", "version")}
    expected = {
        "document_type": DOCUMENT_TYPE,
        "status": DRAFT_STATUS,
        "content": EMPTY_CONTENT,
        "version": FIRST_VERSION,
    }
    assert chosen == expected, (
        f"setup: expected a freshly created draft {expected}, got {chosen} in "
        f"body={response.text!r}"
    )
    created_at = assert_iso_timestamp_within(
        body.get("created_at"), "created_at", before, after
    )
    updated_at = assert_iso_timestamp_within(
        body.get("updated_at"), "updated_at", before, after
    )
    assert updated_at == created_at, (
        f"setup: documents_create.yaml fixes updated_at to equal created_at on creation, "
        f"got created_at={created_at.isoformat()}, updated_at={updated_at.isoformat()}"
    )


async def read_document(
    client: DocumentEditClient, token: str, document_id: str
) -> RawResponseDto:
    """Read a document as its own owner — the baseline for "it was untouched"."""
    response = await client.get_document(token, document_id)
    assert response.status_code == OK_STATUS, (
        f"setup: expected {OK_STATUS} with the owner reading their own document "
        f"{document_id}, got status_code={response.status_code}, body={response.text!r}"
    )
    return response
