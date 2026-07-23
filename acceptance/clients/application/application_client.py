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

    async def oauth_start(self, provider: str) -> OAuthRedirectDto:
        # follow_redirects stays off on purpose: following would send the test at
        # the real provider, and the assertion surface is the Location header
        # itself, not the page behind it.
        response = await self._client.get(f"/api/v1/auth/oauth/{provider}/start")
        return OAuthRedirectDto(
            status_code=response.status_code, location=response.headers.get("location")
        )

    async def oauth_callback(self, provider: str, params: dict) -> OAuthRedirectDto:
        response = await self._client.get(
            f"/api/v1/auth/oauth/{provider}/callback", params=params
        )
        return OAuthRedirectDto(
            status_code=response.status_code, location=response.headers.get("location")
        )

    async def oauth_exchange(self, body: dict) -> OAuthExchangeResponseDto:
        response = await self._client.post("/api/v1/auth/oauth/exchange", json=body)
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

    @staticmethod
    def _parsed_body(response: httpx.Response) -> dict | None:
        try:
            return response.json()
        except ValueError:
            return None

    async def close(self) -> None:
        await self._client.aclose()
