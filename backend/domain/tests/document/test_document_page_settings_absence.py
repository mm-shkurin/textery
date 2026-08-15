"""Scenario 2.1, the Document half: absence is the state every document starts in.

Given a document whose page settings have never been set
When the caller reads it
Then the page settings are reported as absent
And the response does not carry a materialized default object

Split from `test_document_page_settings.py` at the 200-line limit. That file kept
the claims about the `PageSettings` value object itself -- what keys it declares,
that it presets none of them, that it compares by value. This one holds the claims
about `Document`: which factories refuse the field, and what survives a
reconstitute. See `decisions/page-settings-read-tristate-decision.md`.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from document.document import Document
from document.page_settings import PageSettings
from statements.page_settings_fakes import configured_page_settings

_CREATED_AT = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


class TestDocumentPageSettingsAbsentUntilConfigured:
    def test_should_leave_a_new_document_unconfigured(self):
        document = Document.create(
            owner_id=uuid4(),
            document_type="эссе",
            idempotency_key="key-1",
            created_at=_CREATED_AT,
        )

        assert document.page_settings is None, (
            "a document nobody has configured is None by construction, not a default preset"
        )

    def test_should_leave_a_converted_document_unconfigured(self):
        document = Document.create_from_generation(
            owner_id=uuid4(),
            document_type="доклад",
            generation_id=uuid4(),
            content="<p>текст</p>",
            title="Доклад",
            idempotency_key="key-2",
            created_at=_CREATED_AT,
        )

        assert document.page_settings is None, (
            "the conversion carries generated text, not page geometry — a generated "
            "document is as unconfigured as a manual one"
        )

    def test_should_refuse_page_settings_on_either_factory(self):
        # The mass-assignment guard shape already used for status/content/version
        # (Security 2.1): a parameter that does not exist cannot be passed, which
        # binds future callers in a way a DTO that omits the field does not.
        #
        # Built OUTSIDE the raises-blocks on purpose. Constructing PageSettings is
        # itself a nine-argument call that raises TypeError if the value object
        # ever loses a field -- inside the block that would satisfy the guard
        # while never reaching the factory it is supposed to be testing.
        settings = configured_page_settings()

        # `match=` for the same reason: TypeError is the most over-subscribed
        # exception in Python, and an unrelated signature change would otherwise
        # keep this green while the mass-assignment guard was gone.
        with pytest.raises(TypeError, match=r"unexpected keyword argument 'page_settings'"):
            Document.create(
                owner_id=uuid4(),
                document_type="эссе",
                idempotency_key="key-3",
                created_at=_CREATED_AT,
                page_settings=settings,
            )

        with pytest.raises(TypeError, match=r"unexpected keyword argument 'page_settings'"):
            Document.create_from_generation(
                owner_id=uuid4(),
                document_type="доклад",
                generation_id=uuid4(),
                content="<p>текст</p>",
                title="Доклад",
                idempotency_key="key-4",
                created_at=_CREATED_AT,
                page_settings=settings,
            )

    def test_should_round_trip_stored_page_settings_unchanged(self):
        document = _reconstituted(page_settings=configured_page_settings())

        assert document.page_settings == configured_page_settings(), (
            "every one of the nine keys must survive rehydration byte for byte — "
            "story 7's bug was a to_domain() that quietly rebuilt fields it read"
        )

    def test_should_keep_an_unconfigured_document_unconfigured_through_reconstitute(self):
        document = _reconstituted(page_settings=None)

        assert document.page_settings is None, (
            "SQL NULL rehydrates as None, never as a constructed default"
        )

    def test_should_default_to_unconfigured_when_reconstitute_is_not_told(self):
        document = Document.reconstitute(
            id=uuid4(),
            owner_id=uuid4(),
            document_type="эссе",
            status="draft",
            content="",
            version=1,
            idempotency_key="key-5",
            created_at=_CREATED_AT,
            updated_at=_CREATED_AT,
        )

        assert document.page_settings is None, (
            "rows written before the column existed reach reconstitute with nothing "
            "to pass, and must read as unconfigured rather than as a preset"
        )


def _reconstituted(page_settings: PageSettings | None) -> Document:
    return Document.reconstitute(
        id=uuid4(),
        owner_id=uuid4(),
        document_type="эссе",
        status="draft",
        content="<p>сохранено</p>",
        version=3,
        idempotency_key="key-stored",
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
        page_settings=page_settings,
    )
