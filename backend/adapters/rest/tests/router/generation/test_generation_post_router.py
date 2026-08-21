from datetime import UTC, datetime
from uuid import uuid4

from generation.generation import Generation


class TestCreateGenerationHappyPath:
    """Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call."""

    async def test_should_return_201_with_pending_generation_and_enqueue_background_task(
        self, mocker, create_client, owner_id
    ):
        generation = Generation(
            id=uuid4(),
            owner_id=owner_id,
            status="pending",
            created_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=UTC),
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content=None,
        )
        mock_request_usecase = mocker.Mock()
        mock_request_usecase.execute = mocker.AsyncMock(return_value=generation)
        mock_generate_document = mocker.Mock()
        mock_generate_document.execute = mocker.AsyncMock()

        async with create_client(mock_request_usecase, mock_generate_document) as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "document_type": "доклад",
                    "topic": "Как работает фотосинтез",
                    "volume_pages": 3,
                },
                headers={"Idempotency-Key": "test-key"},
            )

        assert response.status_code == 201, (
            f"expected 201 Created, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "generation_id": str(generation.id),
            "status": "pending",
            "created_at": "2026-07-10T12:00:00Z",
            "topic": "Как работает фотосинтез",
            "volume_pages": 3,
            "document_type": "доклад",
            # Echoed even when unset: the response states what the row holds,
            # and an omitted key would be indistinguishable to a client from
            # a style the server silently dropped.
            "text_style": None,
        }, f"unexpected response body {response.json()}"
        # owner_id comes from the token, never the body -- a client that sent one
        # would have it ignored by Pydantic's extra="ignore".
        mock_request_usecase.execute.assert_awaited_once_with(
            owner_id=owner_id,
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            # A body that names no style forwards None rather than a default: the
            # register the model picks on its own is a different thing from the
            # user having chosen "научный", and only one of them may be recorded.
            text_style=None,
            # From the `X-Visitor-Id` header, which this request does not send.
            # Asserted rather than ignored: the route must pass the parameter
            # explicitly, so a browser that DOES send one cannot be silently
            # dropped by a route that forgot to read it.
            visitor_id=None,
        )
        # The background task carries the owner too: it re-reads through the
        # owner-filtered query, so an id alone would find nothing and the generation
        # would sit pending forever.
        mock_generate_document.execute.assert_awaited_once_with(generation.id, owner_id)


class TestCreateGenerationVolumeType:
    """The page count's TYPE, refused at the layer that can still see it.

    The range lives in the domain, so `volume_pages: 11` answers this API's
    {error_code, message}. A boolean is different in kind: `bool` subclasses `int`
    and Pydantic's lax mode coerces `true` to `1`, so by the time the request
    reaches the domain it carries a genuine in-range integer and every guard down
    there passes it. Measured against the running stack 2026-08-20, before the
    fix: 201, for a one-page generation the caller never asked for, billed.
    """

    async def test_should_refuse_a_boolean_volume(self, mocker, create_client):
        request_usecase = mocker.Mock()
        request_usecase.execute = mocker.AsyncMock()
        generate_document = mocker.Mock()
        generate_document.execute = mocker.AsyncMock()

        async with create_client(request_usecase, generate_document) as client:
            response = await client.post(
                "/api/v1/generations",
                json={"document_type": "доклад", "topic": "Тема", "volume_pages": True},
                headers={"Idempotency-Key": "bool-key"},
            )

        assert response.status_code == 422, f"got {response.status_code}: {response.text}"
        # Refused BEFORE the usecase: nothing is stored, and nothing is queued, so
        # no model call is ever billed for the malformed request.
        request_usecase.execute.assert_not_awaited()
        generate_document.execute.assert_not_awaited()

    async def test_should_still_accept_a_numeric_string(self, mocker, create_client, owner_id):
        generation = Generation.create(
            owner_id=owner_id,
            topic="Тема",
            volume_pages=8,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
        )
        request_usecase = mocker.Mock()
        request_usecase.execute = mocker.AsyncMock(return_value=generation)
        generate_document = mocker.Mock()
        generate_document.execute = mocker.AsyncMock()

        async with create_client(request_usecase, generate_document) as client:
            response = await client.post(
                "/api/v1/generations",
                json={"document_type": "доклад", "topic": "Тема", "volume_pages": "8"},
                headers={"Idempotency-Key": "string-key"},
            )

        # The boolean guard is narrower than `StrictInt` on purpose: a numeric
        # string is a client being loose about JSON types, not one saying something
        # it does not mean, and refusing it would be a contract change riding in on
        # a bug fix.
        assert response.status_code == 201, f"got {response.status_code}: {response.text}"
        assert request_usecase.execute.await_args.kwargs["volume_pages"] == 8
