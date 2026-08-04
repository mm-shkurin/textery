from uuid import UUID

import pytest
from document_router_fixtures import CREATED_AT, CREATED_AT_ON_THE_WIRE

from document.document import Document
from document.page_settings import PageSettings

# Pinned rather than uuid4(): the expected body must be a literal the route has
# to produce, not a value read back out of the object the route was handed. With
# a random id, `"document_id": str(document.id)` passes for any id that merely
# round-trips -- including one the route echoed from the wrong source.
DOCUMENT_ID = UUID("6f1d0a2c-3b47-4e58-9c10-2a7e5d84b6f3")
DOCUMENT_ID_ON_THE_WIRE = "6f1d0a2c-3b47-4e58-9c10-2a7e5d84b6f3"

# The stored document's non-geometry fields, named once and used by both the
# builder and the expected body so the two cannot drift apart.
A_DOCUMENT_TYPE = "эссе"
A_STATUS = "draft"
A_CONTENT = "<p>текст</p>"
A_VERSION = 3

# The nine read-side keys documents_get.yaml declares under PageSettings, as a
# concrete object rather than a builder with defaults. There is deliberately no
# PageSettings.default() in the domain (the story exists to keep "never
# configured" distinguishable from "configured to today's preset"), so the
# configured case has to name every value it expects to see on the wire.
A_CONFIGURED_GEOMETRY = PageSettings(
    page_size="A5",
    orientation="landscape",
    margins_mm={"top": 15.0, "right": 12.5, "bottom": 15.0, "left": 12.5},
    font_size_pt=11.0,
    line_height=1.15,
    header_text="Отчёт",
    footer_text=None,
    show_page_numbers=True,
    skip_number_on_first_page=False,
)

A_CONFIGURED_GEOMETRY_ON_THE_WIRE = {
    "page_size": "A5",
    "orientation": "landscape",
    "margins_mm": {"top": 15.0, "right": 12.5, "bottom": 15.0, "left": 12.5},
    "font_size_pt": 11.0,
    "line_height": 1.15,
    "header_text": "Отчёт",
    "footer_text": None,
    "show_page_numbers": True,
    "skip_number_on_first_page": False,
}


def a_stored_document(owner_id, page_settings: PageSettings | None) -> Document:
    """A stored document as GetDocument returns it.

    `reconstitute`, not `create`: the read path rehydrates a persisted row, and
    `create` cannot carry page_settings at all (endpoints.md — there is no
    page_settings on POST /documents).

    The owner is a parameter rather than a module constant read from `conftest`:
    several conftest modules sit on this suite's import path, so `from conftest
    import OWNER_ID` binds whichever landed there first.
    """
    return Document.reconstitute(
        id=DOCUMENT_ID,
        owner_id=owner_id,
        document_type=A_DOCUMENT_TYPE,
        status=A_STATUS,
        content=A_CONTENT,
        version=A_VERSION,
        idempotency_key="key-1",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        # Named explicitly even though both default to None: these are the two
        # fields the scenario is ABOUT -- documents_get.yaml does not declare
        # them, and the RED failure is them leaking onto the read body. Left to
        # the signature default, a later change there (say `title: str = ""`)
        # would silently change what this test proves.
        title=None,
        generation_id=None,
        page_settings=page_settings,
    )


def expected_body(page_settings: dict | None) -> dict:
    """Exactly the eight keys documents_get.yaml declares on DocumentResponse.

    Written as a whole-body literal, not as per-field extraction, because the
    key SET is half the contract: `title` and `generation_id` — which the shared
    DocumentResponseDto carries for the three write-shaped routes — are not
    declared by documents_get.yaml, and the frozen 2.1 acceptance assertion
    rejects the read body unless its keys are exactly these eight. A per-field
    assertion would pass with both of them still leaking onto the read.

    `page_settings` is the WIRE form (a plain dict or None), not the domain
    PageSettings the document was built with: the two shapes are asserted
    independently, so the expected body never restates what the route was given.
    """
    return {
        "document_id": DOCUMENT_ID_ON_THE_WIRE,
        "document_type": A_DOCUMENT_TYPE,
        "status": A_STATUS,
        "content": A_CONTENT,
        "version": A_VERSION,
        "page_settings": page_settings,
        "created_at": CREATED_AT_ON_THE_WIRE,
        "updated_at": CREATED_AT_ON_THE_WIRE,
    }


@pytest.mark.skip(
    reason="RED: GET /documents/{id} is wired to the shared DocumentResponseDto, which has "
    "no 'page_settings' field and carries 'title'/'generation_id' — documents_get.yaml "
    "declares neither. Body has 9 keys, not the declared 8: left contains "
    "{'title': None, 'generation_id': None}, right contains {'page_settings': ...}. "
    "Needs GetDocumentResponseDto (see decisions/page-settings-read-tristate-decision.md)."
)
class TestGetDocumentPageSettingsResponseShape:
    """Scenario 2.1: a never-configured document reads as unconfigured, not as the defaults.

    Given a document whose page settings have never been configured
    When its owner reads it
    Then page_settings is present and null, and no default preset is materialized
    """

    async def test_should_read_a_never_configured_document_as_page_settings_null(
        self, mocker, get_client, owner_id
    ):
        document = a_stored_document(owner_id, page_settings=None)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=document)

        async with get_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{DOCUMENT_ID}")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        # The route must ask for THIS document on behalf of THIS owner. Without
        # this, a route that ignored the path id, or passed a hardcoded owner,
        # still returns the stubbed document and the body assertion passes.
        usecase.execute.assert_awaited_once_with(
            document_id=DOCUMENT_ID, owner_id=owner_id
        )
        # `page_settings: None` with the KEY PRESENT — an omitted key would say
        # "this server does not know the field", which is a different answer.
        assert response.json() == expected_body(page_settings=None), (
            f"unexpected body {response.json()}"
        )

    async def test_should_read_a_configured_document_as_the_stored_geometry(
        self, mocker, get_client, owner_id
    ):
        # The other half of the tri-state. Without this, a route that hardcoded
        # `page_settings: None` onto every read would satisfy the test above.
        document = a_stored_document(owner_id, page_settings=A_CONFIGURED_GEOMETRY)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=document)

        async with get_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{DOCUMENT_ID}")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=DOCUMENT_ID, owner_id=owner_id
        )
        assert response.json() == expected_body(
            page_settings=A_CONFIGURED_GEOMETRY_ON_THE_WIRE
        ), f"unexpected body {response.json()}"
