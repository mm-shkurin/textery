"""Shared arrange helpers for account + document setup over the public API.

Every backend acceptance scenario that needs "a verified account holding a document"
repeats the same register -> verify -> login -> create-document sequence. Five export
Statements classes each carry a private copy of it; this module is the single version
new scenarios use (folding the existing copies in belongs to a refactor pass, not to a
red step).

Setup goes through the public HTTP API only -- never the database.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto

ACCOUNT_PASSWORD = "Str0ng!Pass"
SUPPORTED_DOCUMENT_TYPE = "доклад"
# Document.create builds an empty draft: status draft, content "", no title, and
# created_at == updated_at. Scenarios that assert how a freshly created document is
# projected read these instead of restating the literals.
NEW_DOCUMENT_STATUS = "draft"
NEW_DOCUMENT_CONTENT = ""
NEW_DOCUMENT_TITLE = None


@dataclass(frozen=True)
class CreatedDocument:
    """What setup knows about the document it just made.

    Carries `created_at` because the create response reports it: the instant is
    therefore capturable from setup, and a scenario that projects this document can
    assert the exact timestamp rather than bounding it against "roughly now".
    """

    id: str
    created_at: datetime


async def authenticated_access_token(client: ApplicationClient) -> str:
    email = f"user-{uuid.uuid4()}@example.com"
    register_response = await client.register(
        RegisterRequestDto(
            email=email,
            password=ACCOUNT_PASSWORD,
            confirm_password=ACCOUNT_PASSWORD,
        )
    )
    code = (register_response.body or {}).get("verification_code")
    assert code is not None, (
        f"setup: expected registration to issue a verification_code, got "
        f"status_code={register_response.status_code}, body={register_response.body}"
    )
    await client.verify(VerifyRequestDto(email=email, code=code))
    login_response = await client.login(
        LoginRequestDto(email=email, password=ACCOUNT_PASSWORD)
    )
    token = (login_response.body or {}).get("access_token")
    assert token is not None, (
        f"setup: expected login to issue an access_token, got "
        f"status_code={login_response.status_code}, body={login_response.body}"
    )
    return token


async def create_document_owned_by(
    client: ApplicationClient, access_token: str
) -> CreatedDocument:
    response = await client.create_document(
        document_type=SUPPORTED_DOCUMENT_TYPE,
        access_token=access_token,
        idempotency_key=str(uuid.uuid4()),
    )
    body = response.body or {}
    document_id = body.get("document_id")
    assert document_id is not None, (
        f"setup: expected document creation to return a document_id, got "
        f"status_code={response.status_code}, body={response.body}"
    )
    created_at = body.get("created_at")
    assert created_at is not None, (
        f"setup: expected document creation to report created_at, got "
        f"status_code={response.status_code}, body={response.body}"
    )
    return CreatedDocument(id=document_id, created_at=_as_utc_instant(created_at))


def _as_utc_instant(raw: str) -> datetime:
    """Read the create response's timestamp as an absolute instant.

    A naive value is read as UTC rather than rejected: whether POST /api/v1/documents
    serializes an explicit offset is that endpoint's contract, not something a setup
    helper should pin on its callers' behalf. The feed's own offset-explicitness IS
    asserted, at its parse (see clients/.../project_list_response_dto.py).
    """
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
