import os

import httpx

from clients.application.dto.document.raw_response_dto import RawResponseDto

DOCUMENTS_PATH = "/api/v1/documents"


class DocumentEditClient:
    """HTTP client for story 19's seven AI-edit endpoints plus the story 5 document
    create they hang off.

    Every method returns the raw response so the guard scenarios can compare wire
    bodies byte for byte. Requests carry the caller's bearer token explicitly rather
    than holding session state, because the guard scenarios need two distinct
    authenticated accounts within a single test.
    """

    def __init__(self):
        backend_port = os.environ.get("BACKEND_PORT", "8000")
        self._client = httpx.AsyncClient(base_url=f"http://localhost:{backend_port}")

    async def create_document(
        self, token: str, document_type: str, idempotency_key: str
    ) -> RawResponseDto:
        return await self._request(
            "POST",
            DOCUMENTS_PATH,
            token,
            json={"document_type": document_type},
            headers={"Idempotency-Key": idempotency_key},
        )

    async def get_document(self, token: str, document_id: str) -> RawResponseDto:
        """Story 5's read, used here as the baseline for "the document was untouched"."""
        return await self._request("GET", f"{DOCUMENTS_PATH}/{document_id}", token)

    async def queue_edit(
        self, token: str, document_id: str, body: dict, idempotency_key: str
    ) -> RawResponseDto:
        return await self._request(
            "POST",
            f"{DOCUMENTS_PATH}/{document_id}/ai-edits",
            token,
            json=body,
            headers={"Idempotency-Key": idempotency_key},
        )

    async def stream_edit(self, token: str, document_id: str, edit_id: str) -> RawResponseDto:
        return await self._request(
            "GET", f"{DOCUMENTS_PATH}/{document_id}/ai-edits/{edit_id}/stream", token
        )

    async def get_edit(self, token: str, document_id: str, edit_id: str) -> RawResponseDto:
        return await self._request(
            "GET", f"{DOCUMENTS_PATH}/{document_id}/ai-edits/{edit_id}", token
        )

    async def cancel_edit(self, token: str, document_id: str, edit_id: str) -> RawResponseDto:
        return await self._request(
            "POST", f"{DOCUMENTS_PATH}/{document_id}/ai-edits/{edit_id}/cancel", token
        )

    async def list_messages(self, token: str, document_id: str) -> RawResponseDto:
        return await self._request("GET", f"{DOCUMENTS_PATH}/{document_id}/messages", token)

    async def list_revisions(self, token: str, document_id: str) -> RawResponseDto:
        return await self._request("GET", f"{DOCUMENTS_PATH}/{document_id}/revisions", token)

    async def restore_revision(
        self, token: str, document_id: str, revision_number: str
    ) -> RawResponseDto:
        return await self._request(
            "POST",
            f"{DOCUMENTS_PATH}/{document_id}/revisions/{revision_number}/restore",
            token,
        )

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> RawResponseDto:
        request_headers = {"Authorization": f"Bearer {token}"}
        request_headers.update(headers or {})
        response = await self._client.request(
            method, path, json=json, headers=request_headers
        )
        return RawResponseDto(
            status_code=response.status_code,
            text=response.text,
            body=self._parsed_body(response),
        )

    @staticmethod
    def _parsed_body(response: httpx.Response) -> dict | None:
        try:
            parsed = response.json()
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None

    async def close(self) -> None:
        await self._client.aclose()
