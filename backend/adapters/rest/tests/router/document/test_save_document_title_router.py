import pytest
from document_router_fixtures import a_document, a_usecase

from document.save_document import SaveDocument
from document.title_update import TitleUpdate


@pytest.mark.skip(
    reason="RED: expected await not found — the PUT route forwards request.title raw, so all "
    "four wire shapes reach SaveDocument.execute as title=None / title='' / title='<str>' "
    "instead of TitleUpdate.preserve() / clear() / of(...)"
)
class TestSaveDocumentTitleIntent:
    """The three-state title contract, at the ONE layer that can express it.

    `decisions/blank-title-semantics-decision.md` (story 17) makes the title field
    three-state and distinguishes the states by what the client SENT, not by the
    value alone. Four wire shapes map onto those three states:

        key absent        -> preserve the stored title
        "title": ""/"   " -> preserve the stored title
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

    Every mapping is asserted, not one: the ADR calls for it by name, because a
    route that mapped every shape to a single constant intent satisfies any one of
    these methods on its own.

    Blankness ("" and whitespace-only) is asserted here too, as the ADR's second
    row. An earlier revision of this docstring argued it away -- blankness is an
    invariant of the type, `TitleUpdate.__post_init__` folds a blank down to
    preserve on every construction path, so the route needs no branch and a test
    here could only pin a guard that cannot fire -- and that argument was FALSE.
    The fold runs only on the arm that CARRIES a value. `clear()` is spelled by a
    FLAG, with `value=None`, so a route that hands a blank string to `clear()`
    never presents that string to `__post_init__` at all and nothing folds. The
    route decides WHICH constructor is called, and that decision is what is
    unpinned without the blank arm below.
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

    @pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "whitespace-only"])
    async def test_should_map_a_blank_title_to_preserve(
        self, mocker, save_client, owner_id, blank
    ):
        """The ADR's second row: a blank title is no intent, never an erasure.

        It is what a mount/hydration race, a half-initialised form or a client
        that always serialises the field emits -- the default shape of "I have
        nothing to say about the title". The ADR chose preserve precisely so that
        silent data loss is not the failure mode of an ordinary frontend bug.

        BOTH blanks are exercised, and that is not thoroughness theatre -- each
        catches a wrong green the other lets through. Spelling the null arm
        `if not request.title` instead of `if request.title is None` routes `""`
        into `clear()`, while `"   "` is truthy and survives it untouched. The
        ADR's rejected "blank clears" reading is the mirror image: spelled with a
        truthiness guard so `None.strip()` cannot raise -- `if request.title and
        not request.title.strip()` -- it lets a falsy `""` slip past into `of()`,
        which folds it to preserve, and reaches `clear()` only for `"   "`. Drop
        either case and one of those two goes green. A spelling that clears on
        every blank, and the 422-on-blank the ADR also rejected, are caught by
        either case alone -- those are not what the second parameter is for.

        The expectation is genuinely distinguishable from the clear below: both
        carry `value=None` and only `clears` separates them, which is exactly the
        field a mis-routed blank flips. A correct route needs no blank branch of
        its own -- handing `""` to `of()` folds it here -- but it must not hand it
        to `clear()`, and only asserting the intent that arrives can tell those
        two apart.

        Blankness is TESTED, never applied: the ADR forbids trimming, so a
        legitimate `" Отчёт "` is a set intent carrying its padding byte for byte,
        not a blank and not a rewrite.
        """
        document = a_document(owner_id)
        usecase = a_usecase(mocker, SaveDocument, returns=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1, "title": blank},
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
