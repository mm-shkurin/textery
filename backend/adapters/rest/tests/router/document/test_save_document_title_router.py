from document_router_fixtures import a_document

from document.save_document import SaveDocument


class TestSaveDocumentTitleRoute:
    """Scenario 3.1: a title in the save body must reach SaveDocument.execute.

    The exported filename is derived from the document title, so a save carrying a
    title has to forward it to the usecase. Today the PUT route reads only content
    and version, and SaveDocumentRequestDto's default extra="ignore" silently drops
    the title field before the route ever sees it.
    """

    async def test_should_forward_the_title_to_the_save_usecase(
        self, mocker, save_client, owner_id
    ):
        # No content/version overrides: this test never reads the response body, so
        # seeding them here would imply a coverage of the returned document that no
        # assertion below actually provides. The write shape is pinned whole in
        # test_save_document_router.py.
        document = a_document(owner_id)
        # Autospecced against the real SaveDocument, not a bare Mock: a free-form
        # mock accepts any signature, so a route that renamed or dropped `title`
        # would still satisfy assert_awaited_once_with and only fail in production
        # wiring -- which is precisely what this test exists to catch.
        usecase = mocker.create_autospec(SaveDocument, instance=True)
        usecase.execute.return_value = document

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={
                    "content": "<p>saved</p>",
                    "version": 1,
                    "title": "Привет Мир",
                },
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>saved</p>",
            version=1,
            title="Привет Мир",
        )
