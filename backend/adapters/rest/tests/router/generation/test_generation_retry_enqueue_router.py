"""POST /generations/{id}/retry — whether the run it created is actually started.

Split from the body suite: the two concerns fail for different reasons and the
combined file crossed the repository's 200-line limit.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

from generation_retry_fixtures import a_retry


class TestRetryEnqueue:
    async def test_should_enqueue_the_run_it_created(self, retry_client, usecases, owner_id):
        retry, generate = usecases
        created = a_retry(owner_id)
        retry.execute = AsyncMock(return_value=(created, True))

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry", headers={"Idempotency-Key": "k7"}
            )

        generate.execute.assert_awaited_once_with(created.id, created.owner_id)

    async def test_should_start_nothing_for_a_replayed_key(self, retry_client, usecases, owner_id):
        retry, generate = usecases
        retry.execute = AsyncMock(return_value=(a_retry(owner_id), False))

        async with retry_client(retry, generate) as client:
            await client.post(
                f"/api/v1/generations/{uuid4()}/retry", headers={"Idempotency-Key": "k8"}
            )

        # A replay answers with the row the first attempt created and starts
        # nothing. Enqueuing here would run the work twice, which is what the key
        # exists to prevent — and this route is the one that spends money.
        generate.execute.assert_not_awaited()
