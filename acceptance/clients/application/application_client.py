import os

import httpx

from clients.application.dto.generation.generation_request_dto import CreateGenerationRequestDto
from clients.application.dto.generation.generation_response_dto import GenerationResponseDto


class ApplicationClient:
    def __init__(self):
        backend_port = os.environ.get("BACKEND_PORT", "8000")
        self._client = httpx.AsyncClient(base_url=f"http://localhost:{backend_port}")

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
