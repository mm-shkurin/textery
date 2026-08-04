from uuid import uuid4

from document_router_fixtures import CREATED_AT_ON_THE_WIRE, a_generated_document

from document.document_creation_result import DocumentCreationResult


class TestCreateDocumentFromGenerationRoute:
    """Scenario 2.1 coverage: POST /documents/from-generation had no test at all.

    The route returns the shared DocumentResponseDto, and the editor
    (frontend/src/features/generation/api/documentFromGenerationApi.ts) reads
    `title` and `generation_id` off it as non-nullable. Before this class, dropping
    either key from that DTO broke the editor while every backend test stayed green.
    """

    async def test_should_return_201_and_the_whole_document_body(
        self, mocker, from_generation_client, owner_id
    ):
        generation_id = uuid4()
        document = a_generated_document(owner_id, generation_id)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=DocumentCreationResult(document=document, is_replay=False)
        )

        async with from_generation_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents/from-generation",
                json={"generation_id": str(generation_id)},
                headers={"Idempotency-Key": "gen-key-1"},
            )

        assert response.status_code == 201, f"got {response.status_code}: {response.text}"
        # Whole-body equality, not key-by-key: this and the replay test's twin are
        # what fail if a key is REMOVED from DocumentResponseDto. Verified by
        # mutation -- deleting title/generation_id from the DTO fails both, because
        # pydantic's extra="ignore" makes from_domain drop the kwarg silently rather
        # than raise. Neither is redundant; do not delete one as "covered by the other".
        assert response.json() == {
            "document_id": str(document.id),
            "document_type": "эссе",
            "status": "draft",
            "content": "<p>сгенерированный текст</p>",
            "title": "Влияние климата на урожайность",
            "generation_id": str(generation_id),
            "version": 1,
            "created_at": CREATED_AT_ON_THE_WIRE,
            "updated_at": CREATED_AT_ON_THE_WIRE,
        }, f"unexpected body {response.json()}"

    async def test_should_forward_the_owner_generation_and_idempotency_key(
        self, mocker, from_generation_client, owner_id
    ):
        generation_id = uuid4()
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=DocumentCreationResult(
                document=a_generated_document(owner_id, generation_id), is_replay=False
            )
        )

        async with from_generation_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents/from-generation",
                json={"generation_id": str(generation_id)},
                headers={"Idempotency-Key": "gen-key-1"},
            )

        assert response.status_code == 201, f"got {response.status_code}: {response.text}"
        # The header is the whole replay guard: if the route stopped forwarding it,
        # every conversion would look like a fresh one to the usecase.
        usecase.execute.assert_awaited_once_with(
            owner_id=owner_id, generation_id=generation_id, idempotency_key="gen-key-1"
        )

    async def test_should_return_200_when_the_generation_was_already_converted(
        self, mocker, from_generation_client, owner_id
    ):
        generation_id = uuid4()
        document = a_generated_document(owner_id, generation_id)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=DocumentCreationResult(document=document, is_replay=True)
        )

        async with from_generation_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents/from-generation",
                json={"generation_id": str(generation_id)},
                headers={"Idempotency-Key": "gen-key-1"},
            )

        assert response.status_code == 200, (
            f"a replay -- or the loser of a concurrent conversion race -- must be 200, not 201: "
            f"the client uses the distinction to know it did not create a second document. "
            f"Got {response.status_code}: {response.text}"
        )
        # The replay body is asserted whole, not just on generation_id: that one key
        # is echoed from the request, so a route that replied with a fresh or blank
        # document -- dropping title, losing content -- would still have passed.
        assert response.json() == {
            "document_id": str(document.id),
            "document_type": "эссе",
            "status": "draft",
            "content": "<p>сгенерированный текст</p>",
            "title": "Влияние климата на урожайность",
            "generation_id": str(generation_id),
            "version": 1,
            "created_at": CREATED_AT_ON_THE_WIRE,
            "updated_at": CREATED_AT_ON_THE_WIRE,
        }, f"unexpected replay body {response.json()}"
