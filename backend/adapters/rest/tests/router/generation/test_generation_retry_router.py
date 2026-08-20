"""POST /generations/{id}/retry — what the optional body may carry, and what it may not.

The route had no test of its own while its body handling was changed twice: first
to admit «перегенерировать в другом стиле», then «изменить объём». Both changes live
in the same three lines, and both are silent when wrong — a dropped field simply
reruns the generation the user was trying to change.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from generation.generation import Generation

RETRY_KWARGS = {"generation_id", "owner_id", "idempotency_key", "text_style", "volume_pages"}


def _retry(owner_id, volume_pages: int = 3, text_style: str | None = None) -> Generation:
    """A saved retry row, built through __init__ — the storage hydration path.

    Not through `retry_of`: this stands in for what the usecase RETURNS, and
    building it with the factory under test would make these assertions depend on
    the very resolution rule the domain suite owns.
    """
    seed = Generation.create(
        owner_id=owner_id,
        topic="Тема",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="реферат",
    )
    return Generation(
        id=uuid4(),
        owner_id=owner_id,
        status="pending",
        created_at=seed.created_at,
        topic="Тема",
        volume_pages=volume_pages,
        requirements=None,
        extra_wishes=None,
        document_type="реферат",
        text_style=text_style,
        idempotency_key="key-1",
        source_generation_id=uuid4(),
    )


@pytest.fixture
def usecases(mocker, owner_id):
    retry = mocker.Mock()
    retry.execute = mocker.AsyncMock(return_value=(_retry(owner_id), True))
    generate = mocker.Mock()
    generate.execute = mocker.AsyncMock()
    return retry, generate


class TestRetryBody:
    async def test_should_accept_a_request_with_no_body_at_all(
        self, retry_client, usecases, owner_id
    ):
        retry, generate = usecases
        source_id = uuid4()

        async with retry_client(retry, generate) as client:
            response = await client.post(
                f"/api/v1/generations/{source_id}/retry", headers={"Idempotency-Key": "k1"}
            )

        assert response.status_code == 201, f"got {response.status_code}: {response.text}"
        # The plain «Повторить» must stay bodiless. Both overrides arrive absent
        # rather than defaulted: a default here would silently change what the user
        # asked to repeat.
        retry.execute.assert_awaited_once_with(
            generation_id=source_id,
            owner_id=owner_id,
            idempotency_key="k1",
            text_style=None,
            volume_pages=None,
        )

    async def test_should_forward_a_volume_override(self, retry_client, usecases):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            response = await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k2"},
                json={"volume_pages": 8},
            )

        assert response.status_code == 201
        assert retry.execute.await_args.kwargs["volume_pages"] == 8
        # Naming a length must not clear the register — the two travel independently.
        assert retry.execute.await_args.kwargs["text_style"] is None

    async def test_should_forward_a_style_override(self, retry_client, usecases):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k3"},
                json={"text_style": "научный"},
            )

        assert retry.execute.await_args.kwargs["text_style"] == "научный"
        assert retry.execute.await_args.kwargs["volume_pages"] is None

    async def test_should_forward_both_overrides_together(self, retry_client, usecases):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k4"},
                json={"text_style": "научный", "volume_pages": 5},
            )

        assert retry.execute.await_args.kwargs["text_style"] == "научный"
        assert retry.execute.await_args.kwargs["volume_pages"] == 5

    async def test_should_refuse_a_non_integer_volume_before_the_usecase(
        self, retry_client, usecases
    ):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            response = await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k5"},
                json={"volume_pages": "восемь"},
            )

        # The TYPE is Pydantic's to enforce; the RANGE is the domain's. A string
        # reaching the domain's range check would raise on a comparison rather than
        # refuse, so this one has to stop here.
        assert response.status_code == 422
        retry.execute.assert_not_awaited()

    async def test_should_refuse_a_boolean_volume_before_the_usecase(self, retry_client, usecases):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            response = await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k9"},
                json={"volume_pages": True},
            )

        # THIS is the layer that has to catch it. `bool` subclasses `int` and
        # Pydantic's lax mode coerces `true` to `1`, so by the time the value
        # reaches the domain it is a genuine in-range integer and every guard down
        # there passes it. Measured against the running stack before the fix: 201,
        # for a one-page generation the caller never asked for.
        assert response.status_code == 422, f"got {response.status_code}: {response.text}"
        retry.execute.assert_not_awaited()

    async def test_should_still_accept_a_numeric_string(self, retry_client, usecases):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            response = await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k10"},
                json={"volume_pages": "8"},
            )

        # The guard above is narrower than `StrictInt` on purpose. A numeric string
        # is a client being loose about JSON types, not one saying something it does
        # not mean — refusing it would be a contract change riding in on a bug fix.
        assert response.status_code == 201
        assert retry.execute.await_args.kwargs["volume_pages"] == 8

    async def test_should_ignore_a_field_the_body_may_not_carry(self, retry_client, usecases):
        retry, generate = usecases

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry",
                headers={"Idempotency-Key": "k6"},
                json={"owner_id": str(uuid4()), "status": "completed", "topic": "Чужая тема"},
            )

        # The whole reason the body is a narrow DTO: a client must not be able to
        # re-aim a retry at another account, mark it finished, or rewrite the topic.
        assert set(retry.execute.await_args.kwargs) == RETRY_KWARGS


class TestRetryEnqueue:
    async def test_should_enqueue_the_run_it_created(self, retry_client, usecases, owner_id):
        retry, generate = usecases
        created = _retry(owner_id)
        retry.execute = AsyncMock(return_value=(created, True))

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry", headers={"Idempotency-Key": "k7"}
            )

        generate.execute.assert_awaited_once_with(created.id, created.owner_id)

    async def test_should_start_nothing_for_a_replayed_key(self, retry_client, usecases, owner_id):
        retry, generate = usecases
        retry.execute = AsyncMock(return_value=(_retry(owner_id), False))

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry", headers={"Idempotency-Key": "k8"}
            )

        # A replay answers with the row the first attempt created and starts
        # nothing. Enqueuing here would run the work twice, which is what the key
        # exists to prevent — and this route is the one that spends money.
        generate.execute.assert_not_awaited()
