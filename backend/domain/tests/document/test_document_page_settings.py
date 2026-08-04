"""Scenario 2.1: a never-configured document reads as unconfigured, not as the defaults.

Given a document whose page settings have never been set
When the caller reads it
Then the page settings are reported as absent
And the response does not carry a materialized default object

The domain half of that: absence is a real state a Document can be in, and it is
the state every Document starts in. See
`decisions/page-settings-read-tristate-decision.md`.
"""

import dataclasses
import typing
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from document.document import Document
from document.page_settings import PageSettings
from statements.page_settings_fakes import configured_page_settings

_CREATED_AT = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)

# The read contract of `documents_get.yaml`, as (name, type) pairs. Names alone
# would let a green phase retype `show_page_numbers` to `str` under the guard and
# change the wire body without failing anything.
_READ_SIDE_CONTRACT = [
    ("page_size", str),
    ("orientation", str),
    ("margins_mm", Mapping[str, float]),
    ("font_size_pt", float),
    ("line_height", float),
    ("header_text", str | None),
    ("footer_text", str | None),
    ("show_page_numbers", bool),
    ("skip_number_on_first_page", bool),
]


class TestPageSettingsIsTheReadContractAndCarriesNoPreset:
    """The value-object half, which runs NOW — deliberately not skip-marked.

    These three touch `PageSettings` only, and this commit lands it complete, so the
    RED reason on the sibling class ('Document carries no page_settings') never fires
    for them. Skipping them anyway would suppress green-capable guards — and
    `test_should_give_no_key_a_default` is the one that fails the instant a green
    phase writes `page_size: str = "A4"`, which is the story's central prohibition.
    Under a shared skip marker that line could land unnoticed.
    """

    def test_should_declare_exactly_the_nine_read_side_keys(self):
        # get_type_hints, not `field.type`: the latter is whatever the annotation
        # was spelled as, which is a string under PEP 563 and an object without it.
        hints = typing.get_type_hints(PageSettings)
        contract = [(field.name, hints[field.name]) for field in dataclasses.fields(PageSettings)]

        assert contract == _READ_SIDE_CONTRACT, (
            f"the value object is the read contract of documents_get.yaml — a key added "
            f"here without the spec, dropped from it, or retyped, silently changes the "
            f"wire body; got {contract}"
        )

    def test_should_give_no_key_a_default(self):
        # The sharpest form of the story's premise. A field-level `page_size: str
        # = "A4"` IS a materialized default preset -- it just hides inside the
        # constructor instead of behind a `PageSettings.default()`, and the
        # nine-key guard above cannot see it. The ADR rejects materializing
        # defaults anywhere on the read path; this is where that gets enforced.
        defaulted = [
            field.name
            for field in dataclasses.fields(PageSettings)
            if field.default is not dataclasses.MISSING
            or field.default_factory is not dataclasses.MISSING
        ]

        assert defaulted == [], (
            f"every key must be supplied by whoever configured the document — a default "
            f"here is today's preset frozen into the value object, which is exactly what "
            f"the story exists to prevent; defaulted: {defaulted}"
        )

    def test_should_compare_by_value_and_refuse_mutation(self):
        # Both round-trip assertions below are `==` against a separately built
        # object. That is a nine-field comparison only while `eq=True` holds, and
        # `frozen=True` is what stops the read path mutating a stored settings
        # object in place. Neither is visible to any other test here.
        params = PageSettings.__dataclass_params__

        assert params.eq, "round-trip assertions degrade to identity checks without eq"
        assert params.frozen, "stored page settings are a value, not a mutable buffer"

        with pytest.raises(dataclasses.FrozenInstanceError):
            configured_page_settings().page_size = "A4"  # type: ignore[misc]


@pytest.mark.skip(
    reason="RED: Document carries no page_settings — "
    "AttributeError: 'Document' object has no attribute 'page_settings'; "
    "TypeError: Document.reconstitute() got an unexpected keyword argument 'page_settings'"
)
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
