"""«Изменить объём текста» — the length a retry may re-choose.

The sibling of the style override, and asserted separately because the two are
resolved by the same rule but validated by different ones: a register outside the
allowlist and a length outside 1..10 are different refusals, and folding them into
one suite is how one of them quietly stops being checked.
"""

from uuid import uuid4

import pytest

from document.document_type import REFERAT
from generation.generation import (
    MAX_VOLUME_PAGES,
    MIN_VOLUME_PAGES,
    OUT_OF_RANGE_VOLUME_MESSAGE,
    Generation,
)
from generation.text_style import NAUCHNY
from shared.exceptions import ValidationException


def _source(volume_pages: int = 3, text_style: str | None = None) -> Generation:
    return Generation.create(
        owner_id=uuid4(),
        topic="Тема",
        volume_pages=volume_pages,
        requirements=None,
        extra_wishes=None,
        document_type=REFERAT,
        text_style=text_style,
    )


class TestVolumeOverride:
    def test_should_keep_the_sources_volume_when_a_retry_names_none(self):
        source = _source(volume_pages=7)

        # The plain «Повторить» is bodiless, so it must reproduce the run it
        # repeats. Silently changing the length would be a different request.
        assert Generation.retry_of(source, idempotency_key="k").volume_pages == 7

    def test_should_take_the_override_when_a_retry_names_a_length(self):
        source = _source(volume_pages=3)

        retry = Generation.retry_of(source, idempotency_key="k", volume_pages=9)

        assert retry.volume_pages == 9
        assert source.volume_pages == 3, "the source row must not be rewritten by its retry"

    @pytest.mark.parametrize("volume_pages", [MIN_VOLUME_PAGES, MAX_VOLUME_PAGES])
    def test_should_accept_both_ends_of_the_allowed_range(self, volume_pages):
        # The boundaries themselves, so the refusal below cannot be satisfied by an
        # off-by-one that rejects the shortest or the longest legal length.
        retry = Generation.retry_of(_source(), idempotency_key="k", volume_pages=volume_pages)

        assert retry.volume_pages == volume_pages

    @pytest.mark.parametrize("volume_pages", [0, MAX_VOLUME_PAGES + 1, 500, -3])
    def test_should_refuse_a_length_the_form_would_have_refused(self, volume_pages):
        # Without this the row would store 500, and `build_prompt` would reject the
        # value as unrenderable — turning a client mistake into a generation that
        # fails after the work was queued.
        with pytest.raises(ValidationException) as caught:
            Generation.retry_of(_source(), idempotency_key="k", volume_pages=volume_pages)

        assert caught.value.message == OUT_OF_RANGE_VOLUME_MESSAGE

    @pytest.mark.parametrize("volume_pages", [True, False])
    def test_should_refuse_a_boolean_rather_than_read_it_as_a_page_count(self, volume_pages):
        # `bool` subclasses `int`, so Pydantic coerces a JSON `true` to 1 on the way
        # in and a bare range check then passes it. Measured against the running
        # stack: `{"volume_pages": true}` produced a one-page generation the caller
        # never asked for — and billed it.
        with pytest.raises(ValidationException) as caught:
            Generation.retry_of(_source(), idempotency_key="k", volume_pages=volume_pages)

        assert caught.value.message == OUT_OF_RANGE_VOLUME_MESSAGE

    def test_should_not_revalidate_a_volume_it_merely_copies(self):
        # A row stored under an older, wider rule must stay retryable: refusing here
        # would strand its owner with a button that can never succeed. Built through
        # `__init__` — the storage hydration path — which applies no range check.
        stored_under_an_older_rule = Generation(
            id=uuid4(),
            owner_id=uuid4(),
            status="failed",
            created_at=_source().created_at,
            topic="Тема",
            volume_pages=50,
            requirements=None,
            extra_wishes=None,
            document_type=REFERAT,
        )

        assert Generation.retry_of(stored_under_an_older_rule, "k").volume_pages == 50


class TestOverridesAreIndependent:
    def test_should_change_only_the_length_when_only_the_length_is_named(self):
        source = _source(volume_pages=3, text_style=NAUCHNY)

        retry = Generation.retry_of(source, idempotency_key="k", volume_pages=8)

        assert retry.volume_pages == 8
        assert retry.text_style == NAUCHNY, "naming a length must not clear the register"

    def test_should_change_only_the_register_when_only_the_register_is_named(self):
        source = _source(volume_pages=3, text_style=None)

        retry = Generation.retry_of(source, idempotency_key="k", text_style=NAUCHNY)

        assert retry.text_style == NAUCHNY
        assert retry.volume_pages == 3, "naming a register must not change the length"

    def test_should_apply_both_when_both_are_named(self):
        retry = Generation.retry_of(
            _source(volume_pages=2), idempotency_key="k", text_style=NAUCHNY, volume_pages=6
        )

        assert (retry.text_style, retry.volume_pages) == (NAUCHNY, 6)

    def test_should_refuse_the_whole_retry_when_one_override_is_invalid(self):
        # No partial application: a retry carrying one good override and one bad one
        # must not start work under half of what the user asked for.
        with pytest.raises(ValidationException):
            Generation.retry_of(_source(), idempotency_key="k", text_style=NAUCHNY, volume_pages=99)
