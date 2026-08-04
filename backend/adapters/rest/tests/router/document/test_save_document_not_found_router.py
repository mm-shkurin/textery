from uuid import uuid4

from document_router_fixtures import a_document, a_usecase

from document.save_document import SaveDocument
from shared.exceptions import NotFoundException


class TestSaveDocumentNotFound:
    """PUT's write-path 404 -- the one exit from `save_document` nothing asserted.

    GET /{id} and GET /{id}/export both have a 404 test, and both reach it the same
    way: the usecase returns `None` and the ROUTE raises. PUT does not. Its usecase
    raises `NotFoundException` itself, from `SaveDocument._explain_miss`, when the
    CAS matched nothing and the re-read finds no document the caller owns -- a tab
    left open on a document that was since deleted, or a document that was never
    the caller's. No test in this suite has ever driven that path: the PUT tests
    all stub `execute` with a return value and none with a `side_effect`.

    The distinction that makes it worth pinning is the client's, not the server's:
    the editor autosaves, and 5xx is retryable where 404 is terminal. A regression
    that dropped `NotFoundException` from the handler registry -- or that wrapped
    the usecase call in a `try` -- turns every save against a deleted document into
    a 500, and the autosave loop retries it forever against a row that will never
    come back.

    Unlike the title-intent class next door this is a REGRESSION GUARD, not a red:
    `not_found_exception_handler` is already registered for `NotFoundException`
    (`main.py:155`, and the `document_app` fixture mirrors it), so the mapping is
    already correct and this test passes on arrival. It is unskipped for that
    reason.
    """

    async def test_should_return_404_when_the_save_usecase_reports_the_document_gone(
        self, mocker, save_client
    ):
        document_id = uuid4()
        usecase = a_usecase(mocker, SaveDocument)
        usecase.execute.side_effect = NotFoundException(f"document {document_id} not found")

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document_id}",
                json={"content": "<p>saved</p>", "version": 1},
            )

        assert response.status_code == 404, f"got {response.status_code}: {response.text}"
        # The whole body, not just the status: the exception is raised carrying the
        # document id, and echoing `str(exc)` is the leak Security 5.1 names. The
        # fixed sanctioned message is what must reach the wire.
        assert response.json() == {
            "error_code": "NOT_FOUND",
            "message": "The requested resource was not found.",
        }, f"unexpected body {response.json()}"

    async def test_should_not_answer_404_on_the_ordinary_save(self, mocker, save_client):
        """The negative control for the class above.

        Without it, a route that answered 404 unconditionally -- or a fixture that
        wired the wrong dependency and 404'd on the path itself -- would satisfy
        the assertion above while proving nothing about `NotFoundException`.
        """
        document = a_document(uuid4(), content="<p>saved</p>", version=2)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
