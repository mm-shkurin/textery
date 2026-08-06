"""Scenario 2.1: a never-configured document reads as unconfigured, not as the defaults.

Given a document whose page settings have never been set
When the caller reads it
Then the page settings are reported as absent
And the response does not carry a materialized default object

GetDocument is unchanged by this story and stays that way -- these tests exist to
pin that. The whole point of the design is that nothing on the read path decides
what a document's page geometry should be; the value travels unresolved from
column to wire. A usecase that grew a `or PageSettings.default()` would freeze
today's preset into every old document, and that is what fails here.
See `decisions/page-settings-read-tristate-decision.md`.
"""

from uuid import uuid4

from document.get_document import GetDocument
from statements.document_fakes import (
    STORED_AT,
    configured_document,
    seeded,
    stored_document,
)
from statements.page_settings_fakes import configured_page_settings


class TestGetDocumentReportsPageSettingsUnresolved:
    async def test_should_report_a_never_configured_document_as_unconfigured(self):
        owner_id = uuid4()
        document = stored_document(owner_id)
        document_id = document.id
        usecase = GetDocument(await seeded(document))

        found = await usecase.execute(document_id=document_id, owner_id=owner_id)

        assert found.id == document_id, (
            "the assertion below is only about page settings if this is the document "
            "that was asked for — a usecase handing back a freshly constructed blank "
            "one would otherwise read as a correct absence"
        )
        assert found.page_settings is None, (
            "absent must stay absent — materializing the preset here would make a "
            "document nobody configured indistinguishable from one configured to "
            "today's defaults, and would freeze those defaults into it forever"
        )

    async def test_should_hand_back_stored_page_settings_untouched(self):
        owner_id = uuid4()
        document = configured_document(owner_id, configured_page_settings())
        document_id = document.id
        usecase = GetDocument(await seeded(document))

        found = await usecase.execute(document_id=document_id, owner_id=owner_id)

        assert found.id == document_id, "the settings below must belong to this document"
        assert found.page_settings == configured_page_settings(), (
            "a configured document's nine keys reach the caller exactly as stored; "
            "the usecase resolves nothing"
        )

    async def test_should_read_an_unconfigured_document_twice_without_configuring_it(self):
        owner_id = uuid4()
        document = stored_document(owner_id)
        usecase = GetDocument(await seeded(document))

        first = await usecase.execute(document_id=document.id, owner_id=owner_id)
        second = await usecase.execute(document_id=document.id, owner_id=owner_id)

        # Compared against LITERALS, never against `document.<field>`. The fake
        # repository returns the instance it was seeded with, so `first`, `second`
        # and `document` are all one object: `second.updated_at ==
        # document.updated_at` is the same attribute on both sides and stays true
        # however hard the usecase stamps it. The literals are what actually fail.
        assert first.page_settings is None, "the first read constructs no default"
        assert first.version == 1, "nor does it move the CAS token"
        assert first.updated_at == STORED_AT, "nor the modification stamp"

        assert second.page_settings is None, (
            "and the second sees the same absence — a read that wrote a preset back "
            "would show up here as the second read disagreeing with the first"
        )
        assert second.version == 1, "reading is not an edit: the CAS token does not move"
        assert second.updated_at == STORED_AT, "nor does the modification stamp"
