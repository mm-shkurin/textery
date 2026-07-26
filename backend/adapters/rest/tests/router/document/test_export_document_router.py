from uuid import uuid4

import pytest


@pytest.mark.skip(
    reason="RED: GET /api/v1/documents/{id}/export route does not exist yet, so the "
    "request hits Starlette's default {'detail':'Not Found'} 404 body instead of the "
    "sanctioned {'error_code':'NOT_FOUND', ...} shape"
)
class TestExportDocumentRoute:
    """Scenario 1.1: export of a non-existent document is refused with the sanctioned 404."""

    async def test_should_return_404_when_the_usecase_finds_nothing(self, mocker, export_client):
        # Absent and foreign both arrive as None from the owner-scoped usecase; the
        # route must translate that into the sanctioned NOT_FOUND body, never leak it.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export")

        assert response.status_code == 404, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "NOT_FOUND",
            "message": "The requested resource was not found.",
        }
