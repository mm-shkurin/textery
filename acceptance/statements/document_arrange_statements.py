"""The account+document arrange every document scenario shares.

Neutral base for document Statements: it carries only the setup steps (register a
verified account, create a document owned by it) and no scenario contract of its
own. Scenarios that need that arrange without inheriting an unrelated contract —
e.g. the page-settings read — subclass this directly; the export family subclasses
DocumentExportStatements, which adds the export contract on top.
"""

import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto

ACCOUNT_PASSWORD = "Str0ng!Pass"
SUPPORTED_DOCUMENT_TYPE = "доклад"


class DocumentArrangeStatements:
    def __init__(self, client: ApplicationClient):
        self._client = client

    async def _authenticated_access_token(self) -> str:
        email = f"user-{uuid.uuid4()}@example.com"
        register_response = await self._client.register(
            RegisterRequestDto(
                email=email,
                password=ACCOUNT_PASSWORD,
                confirm_password=ACCOUNT_PASSWORD,
            )
        )
        code = register_response.body.get("verification_code")
        assert code is not None, (
            f"setup: expected registration to issue a verification_code, got body="
            f"{register_response.body}"
        )
        await self._client.verify(VerifyRequestDto(email=email, code=code))
        login_response = await self._client.login(
            LoginRequestDto(email=email, password=ACCOUNT_PASSWORD)
        )
        token = (login_response.body or {}).get("access_token")
        assert token is not None, (
            f"setup: expected login to issue an access_token, got body={login_response.body}"
        )
        return token

    async def _create_document_owned_by(self, access_token: str) -> str:
        response = await self._client.create_document(
            document_type=SUPPORTED_DOCUMENT_TYPE,
            access_token=access_token,
            idempotency_key=str(uuid.uuid4()),
        )
        document_id = (response.body or {}).get("document_id")
        assert document_id is not None, (
            f"setup: expected document creation to return a document_id, got "
            f"status_code={response.status_code}, body={response.body}"
        )
        return document_id
