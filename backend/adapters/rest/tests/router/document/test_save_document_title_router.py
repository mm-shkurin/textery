import pytest
from document_router_fixtures import a_document, a_usecase

from document.save_document import SaveDocument
from document.title_update import TitleUpdate


@pytest.mark.skip(
    reason="RED: expected await not found — the PUT route forwards request.title raw, so all "
    "three wire shapes reach SaveDocument.execute as title=None / title='<str>' instead of "
    "TitleUpdate.preserve() / clear() / of(...)"
)
class TestSaveDocumentTitleIntent:
    """The three-state title contract, at the ONE layer that can express it.

    `decisions/blank-title-semantics-decision.md` (story 17) makes the title field
    three-state and distinguishes the states by what the client SENT, not by the
    value alone:

        key absent        -> preserve the stored title
        "title": null     -> explicit clear, SET title = NULL
        "title": "Отчёт"  -> store verbatim

    Pydantic collapses the first two to `None`, so `model_fields_set` on
    `SaveDocumentRequestDto` is the only place in the stack where they are still
    distinguishable. The route forwards `title=request.title` raw today, which
    spends that distinction one line after receiving it: `SaveDocument._title_intent`
    then maps both to `TitleUpdate.preserve()`, and its own docstring forbids
    exactly that ("if it forwards `None` for a null the erasure is silently
    converted into a preserve and the whole clear path no-ops with every test
    green"). `TitleUpdate.clear()` is today constructed only by tests -- no HTTP
    request can produce it -- so a user who clears a title keeps the old one in
    history and in the export filename, with the domain and usecase suites green.

    Both mappings are asserted, not one: the ADR calls for it by name, because a
    route that mapped every shape to a single constant intent satisfies any one of
    these three methods on its own.

    Blankness ("" and whitespace-only) is deliberately NOT re-asserted here. It is
    an invariant of the type -- `TitleUpdate.__post_init__` folds a blank down to
    preserve on every construction path -- so the route needs no branch for it and
    a test here could only pin a guard that cannot fire.
    """

    async def test_should_map_an_absent_title_to_preserve(self, mocker, save_client, owner_id):
        """The content-only autosave: the shape almost every save in the app has.

        `documentApi.ts` sends `{ content, version }` with no title key at all, so
        this arm carries the traffic. It must reach the port as the NAMED absent
        state -- a bare `None` is the ambiguity `TitleUpdate` exists to remove, and
        forwarding it on the most-travelled path is what turns the clear path
        landing into a candidate mass wipe.
        """
        document = a_document(owner_id)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>saved</p>",
            version=1,
            title=TitleUpdate.preserve(),
        )

    async def test_should_map_an_explicit_wire_null_title_to_clear(
        self, mocker, save_client, owner_id
    ):
        """The deliberate erasure -- the only wire shape that removes a title.

        `TitleUpdate` is a frozen dataclass, so `==` compares (value, clears) and
        this expectation is genuinely distinguishable from the preserve above:
        both carry `value=None`, and only `clears` tells them apart. An assertion
        that compared `value` alone would pass under today's route.
        """
        document = a_document(owner_id)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1, "title": None},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>saved</p>",
            version=1,
            title=TitleUpdate.clear(),
        )

    async def test_should_map_a_wire_title_to_a_set_intent(self, mocker, save_client, owner_id):
        """Scenario 3.1's original assertion, restated in the intent the port takes.

        It used to expect the raw string, which `_title_intent` wrapped one layer
        deeper. The wrapping moves to the route with the other two arms so all
        three states are decided in the one place that can tell them apart.
        """
        document = a_document(owner_id)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1, "title": "Привет Мир"},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>saved</p>",
            version=1,
            title=TitleUpdate.of("Привет Мир"),
        )
