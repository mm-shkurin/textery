from uuid import uuid4

from document_router_fixtures import (
    CREATED_AT_ON_THE_WIRE,
    a_document,
    a_generated_document,
    a_usecase,
)

from document.save_document import SaveDocument
from document.title_update import TitleUpdate


class TestSaveDocumentResponseShape:
    """Scenario 2.1 coverage: PUT's response body was only ever asserted on `version`.

    Scenario 2.1 split the read shape into GetDocumentResponseDto for GET
    /documents/{document_id} and left DocumentResponseDto as the WRITE shape that
    POST /documents, POST /documents/from-generation and PUT /documents/{id} share.
    GET and PUT sit on the same path literal roughly forty lines apart in
    document_router.py, so an edit that narrows the wrong decorator swaps PUT onto
    the read shape -- and `version` exists on BOTH DTOs, so the one body assertion
    the suite had for PUT survived that swap untouched. This class asserts the
    whole write body instead, with title and generation_id at NON-NULL values: a
    null-valued expectation would still pass if the keys were dropped from the DTO
    and re-defaulted, which is exactly the mutation being guarded against.
    """

    async def test_should_return_the_whole_write_shape_on_a_successful_save(
        self, mocker, save_client, owner_id
    ):
        generation_id = uuid4()
        document = a_generated_document(
            owner_id, generation_id, content="<p>отредактировано</p>", version=2
        )
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>отредактировано</p>", "version": 1},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "document_id": str(document.id),
            "document_type": "эссе",
            "status": "draft",
            "content": "<p>отредактировано</p>",
            "title": "Влияние климата на урожайность",
            "generation_id": str(generation_id),
            "version": 2,
            "created_at": CREATED_AT_ON_THE_WIRE,
            "updated_at": CREATED_AT_ON_THE_WIRE,
        }, f"unexpected body {response.json()}"

    async def test_should_call_the_save_usecase_with_the_path_id_and_the_bearer_owner(
        self, mocker, save_client, owner_id
    ):
        generation_id = uuid4()
        document = a_generated_document(owner_id, generation_id, version=2)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>c</p>", "version": 1, "title": "Новое имя"},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        # document_id comes from the PATH and owner_id from the BEARER token -- never
        # from the body. A route that hardcoded either, or crossed them over, passes
        # a status-code-only test.
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>c</p>",
            version=1,
            title=TitleUpdate.of("Новое имя"),
        )


class TestSaveDocumentRoute:
    async def test_should_return_200_with_the_stored_document(self, mocker, save_client, owner_id):
        document = a_document(owner_id, content="<p>saved</p>", version=2)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        # The whole body, not `version` alone. `version` is the one key that exists
        # on BOTH DTOs, so a single-key check here is exactly the assertion the class
        # above was written because it survives a swap of PUT onto the read shape.
        # This arm carries the NEVER-TITLED document, so it pins what the class above
        # cannot: that `title` and `generation_id` are still on the write shape as
        # present-and-null keys, the form `documentApi.ts` reads.
        assert response.json() == {
            "document_id": str(document.id),
            "document_type": "эссе",
            "status": "draft",
            "content": "<p>saved</p>",
            "title": None,
            "generation_id": None,
            "version": 2,
            "created_at": CREATED_AT_ON_THE_WIRE,
            "updated_at": CREATED_AT_ON_THE_WIRE,
        }, f"unexpected body {response.json()}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>saved</p>",
            version=1,
            title=TitleUpdate.preserve(),
        )

    async def test_should_ignore_server_owned_fields_in_the_save_body(
        self, mocker, save_client, owner_id
    ):
        # Scenario 5.4: only content and version are ever applied.
        document = a_document(owner_id, version=2)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={
                    "content": "<p>x</p>",
                    "version": 1,
                    "document_type": "реферат",
                    "id": str(uuid4()),
                    "status": "completed",
                },
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>x</p>",
            version=1,
            title=TitleUpdate.preserve(),
        )
