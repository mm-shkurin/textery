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

import pytest

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
