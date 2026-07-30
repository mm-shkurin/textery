import os

import httpx

from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.login_response_dto import LoginResponseDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from clients.application.dto.auth.resend_request_dto import ResendRequestDto
from clients.application.dto.auth.resend_response_dto import ResendResponseDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from clients.application.dto.auth.verify_response_dto import VerifyResponseDto
from clients.application.dto.auth.oauth_dtos import OAuthExchangeResponseDto, OAuthRedirectDto
from clients.application.dto.document.create_document_response_dto import CreateDocumentResponseDto
from clients.application.dto.document.export_response_dto import ExportResponseDto
from clients.application.dto.document.get_document_response_dto import GetDocumentResponseDto
from clients.application.dto.document.save_document_response_dto import SaveDocumentResponseDto
from clients.application.dto.generation.generation_request_dto import CreateGenerationRequestDto
from clients.application.dto.generation.generation_response_dto import GenerationResponseDto


class ApplicationClient:
    def __init__(self):
        backend_port = os.environ.get("BACKEND_PORT", "8000")
        self._client = httpx.AsyncClient(base_url=f"http://localhost:{backend_port}")

    async def register(self, request: RegisterRequestDto) -> RegisterResponseDto:
        response = await self._client.post("/api/v1/auth/register", json=request.to_json())
        return RegisterResponseDto(status_code=response.status_code, body=self._parsed_body(response))

    async def verify(self, request: VerifyRequestDto) -> VerifyResponseDto:
        response = await self._client.post("/api/v1/auth/verify", json=request.to_json())
        return VerifyResponseDto(status_code=response.status_code, body=self._parsed_body(response))

    async def resend_code(self, request: ResendRequestDto) -> ResendResponseDto:
        response = await self._client.post("/api/v1/auth/resend-code", json=request.to_json())
        return ResendResponseDto(status_code=response.status_code, body=self._parsed_body(response))

    async def login(self, request: LoginRequestDto) -> LoginResponseDto:
        response = await self._client.post("/api/v1/auth/login", json=request.to_json())
        return LoginResponseDto(status_code=response.status_code, body=self._parsed_body(response))

    async def oauth_start(self, provider: str, headers: dict | None = None) -> OAuthRedirectDto:
        # follow_redirects stays off on purpose: following would send the test at
        # the real provider, and the assertion surface is the Location header
        # itself, not the page behind it. `headers` lets a test spoof the source
        # (X-Forwarded-For) so the rate-limit bucket is per-caller.
        response = await self._client.get(
            f"/api/v1/auth/oauth/{provider}/start", headers=headers
        )
        return OAuthRedirectDto(
            status_code=response.status_code, location=response.headers.get("location")
        )

    async def oauth_callback(
        self, provider: str, params: dict, headers: dict | None = None
    ) -> OAuthRedirectDto:
        response = await self._client.get(
            f"/api/v1/auth/oauth/{provider}/callback", params=params, headers=headers
        )
        return OAuthRedirectDto(
            status_code=response.status_code, location=response.headers.get("location")
        )

    async def oauth_exchange(
        self, body: dict, headers: dict | None = None
    ) -> OAuthExchangeResponseDto:
        response = await self._client.post(
            "/api/v1/auth/oauth/exchange", json=body, headers=headers
        )
        return OAuthExchangeResponseDto(
            status_code=response.status_code, body=self._parsed_body(response)
        )

    async def create_generation(
        self, request: CreateGenerationRequestDto, idempotency_key: str
    ) -> GenerationResponseDto:
        response = await self._client.post(
            "/api/v1/generations",
            json=request.to_json(),
            headers={"Idempotency-Key": idempotency_key},
        )
        return GenerationResponseDto(status_code=response.status_code, body=self._parsed_body(response))

    async def get_generation(self, generation_id: str) -> GenerationResponseDto:
        response = await self._client.get(f"/api/v1/generations/{generation_id}")
        return GenerationResponseDto(status_code=response.status_code, body=self._parsed_body(response))

    async def create_document(
        self, document_type: str, access_token: str, idempotency_key: str
    ) -> CreateDocumentResponseDto:
        response = await self._client.post(
            "/api/v1/documents",
            json={"document_type": document_type},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Idempotency-Key": idempotency_key,
            },
        )
        return CreateDocumentResponseDto(
            status_code=response.status_code, body=self._parsed_body(response)
        )

    async def get_document(
        self, document_id: str, access_token: str
    ) -> GetDocumentResponseDto:
        response = await self._client.get(
            f"/api/v1/documents/{document_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return GetDocumentResponseDto(
            status_code=response.status_code, body=self._parsed_body(response)
        )

    async def save_document(
        self,
        document_id: str,
        content: str,
        version: int,
        access_token: str,
        title: str | None = None,
    ) -> SaveDocumentResponseDto:
        # title is threaded in as the Cyrillic-filename scenario's source of truth.
        # It is sent as an extra field on the save payload; whether the backend
        # persists it (story-5-extension) or drops it via Pydantic extra="ignore"
        # is exactly what the export filename assertion pins down.
        payload: dict = {"content": content, "version": version}
        if title is not None:
            payload["title"] = title
        response = await self._client.put(
            f"/api/v1/documents/{document_id}",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return SaveDocumentResponseDto(
            status_code=response.status_code, body=self._parsed_body(response)
        )

    async def export_document(
        self, document_id: str, export_format: str | None, access_token: str
    ) -> ExportResponseDto:
        # export_format is passed straight through so a test can exercise an
        # unsupported value ("xml"); None omits the query param entirely, which is
        # the "no format at all" case the format guard must also refuse.
        params = {} if export_format is None else {"format": export_format}
        response = await self._client.get(
            f"/api/v1/documents/{document_id}/export",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return ExportResponseDto(
            status_code=response.status_code,
            body=self._parsed_body(response),
            content_type=response.headers.get("content-type"),
            content_disposition=response.headers.get("content-disposition"),
            content=response.content,
        )

    @staticmethod
    def _parsed_body(response: httpx.Response) -> dict | None:
        try:
            return response.json()
        except ValueError:
            return None

    async def close(self) -> None:
        await self._client.aclose()
