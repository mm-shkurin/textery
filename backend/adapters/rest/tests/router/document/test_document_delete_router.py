"""DELETE /api/v1/documents/{id} — «удалить текст из истории», at the HTTP boundary."""

from uuid import uuid4

from conftest import OWNER_ID

from shared.exceptions import NotFoundException


class TestDeleteDocument:
    async def test_should_answer_204_with_no_body(self, mocker, delete_client):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)
        document_id = uuid4()

        async with delete_client(usecase) as client:
            response = await client.delete(f"/api/v1/documents/{document_id}")

        assert response.status_code == 204, f"got {response.status_code}: {response.text}"
        # A 204 carrying a JSON `null` is a contradiction some proxies and clients handle badly.
        assert response.content == b""

    async def test_should_pass_the_callers_own_owner_id_through(self, mocker, delete_client):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)
        document_id = uuid4()

        async with delete_client(usecase) as client:
            await client.delete(f"/api/v1/documents/{document_id}")

        # The owner comes from the token and is never a request parameter: without it in the call
        # the usecase would delete by id alone, which is an IDOR on an irreversible operation.
        usecase.execute.assert_awaited_once_with(document_id=document_id, owner_id=OWNER_ID)

    async def test_should_answer_404_when_nothing_of_the_callers_matched(
        self, mocker, delete_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(side_effect=NotFoundException("document not found"))

        async with delete_client(usecase) as client:
            response = await client.delete(f"/api/v1/documents/{uuid4()}")

        assert response.status_code == 404
        # The shared handler's shape, not FastAPI's `detail` envelope — and the body must not name
        # the resource kind, so a caller cannot tell "absent" from "someone else's".
        assert "error_code" in response.json()

    async def test_should_refuse_an_unauthenticated_delete_before_reaching_the_usecase(
        self, mocker, delete_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)

        async with delete_client(usecase, authenticated=False) as client:
            response = await client.delete(f"/api/v1/documents/{uuid4()}")

        assert response.status_code == 401
        usecase.execute.assert_not_awaited()

    async def test_should_refuse_an_id_that_is_not_a_uuid(self, mocker, delete_client):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)

        async with delete_client(usecase) as client:
            response = await client.delete("/api/v1/documents/not-a-uuid")

        assert response.status_code == 422
        usecase.execute.assert_not_awaited()
