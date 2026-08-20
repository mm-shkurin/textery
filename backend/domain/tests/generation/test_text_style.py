"""The register a generated text is written in: what is accepted, and what reaches the prompt."""

from uuid import uuid4

import pytest

from document.document_type import REFERAT
from generation.generation import Generation
from generation.prompt_request import PromptRequest
from generation.prompt_template import build_prompt
from generation.text_style import (
    HUDOZHESTVENNY,
    INVALID_TEXT_STYLE_MESSAGE,
    NAUCHNY,
    PUBLICISTICHESKY,
    SUPPORTED_TEXT_STYLES,
    style_instruction,
    validate_text_style,
)
from shared.exceptions import ValidationException


class TestValidation:
    """The allowlist, and the one value outside it that is nonetheless accepted."""

    @pytest.mark.parametrize("style", SUPPORTED_TEXT_STYLES)
    def test_should_accept_each_supported_register(self, style):
        assert validate_text_style(style) == style, (
            f"{style!r} is in SUPPORTED_TEXT_STYLES and must be accepted unchanged"
        )

    def test_should_accept_absence_as_no_register_chosen(self):
        # NOT a rejection and NOT a default. A request naming no style is asking for the model's
        # own register, which is what every generation made before this field existed received.
        assert validate_text_style(None) is None

    def test_should_refuse_a_register_outside_the_allowlist(self):
        with pytest.raises(ValidationException) as caught:
            validate_text_style("канцелярский")

        assert caught.value.error_code == "INVALID_TEXT_STYLE", (
            "the code names the offending field so a client can react to it without parsing prose"
        )
        assert caught.value.message == INVALID_TEXT_STYLE_MESSAGE

    def test_should_refuse_the_empty_string_rather_than_read_it_as_absence(self):
        # The distinction the whole design rests on: '' is a client that sent the field and named
        # nothing. Folding it into None here would let a broken form silently record "no register".
        with pytest.raises(ValidationException):
            validate_text_style("")


class TestPromptInstruction:
    """What a register turns into inside the prompt."""

    @pytest.mark.parametrize("style", SUPPORTED_TEXT_STYLES)
    def test_should_give_every_supported_register_its_own_sentence(self, style):
        instruction = style_instruction(style)

        assert instruction is not None, (
            f"{style!r} is offered to users but adds nothing to the prompt"
        )
        assert instruction.endswith("."), (
            "each instruction is one sentence, per the template contract"
        )

    def test_should_give_distinct_instructions_to_distinct_registers(self):
        # Three identical sentences would satisfy the check above while making the picker a control
        # that changes the stored value and nothing the user can read in the result.
        instructions = {style_instruction(style) for style in SUPPORTED_TEXT_STYLES}

        assert len(instructions) == len(SUPPORTED_TEXT_STYLES)

    def test_should_add_nothing_when_no_register_was_chosen(self):
        assert style_instruction(None) is None

    def test_should_degrade_an_unrecognised_register_to_no_instruction(self):
        # This path also serves rows hydrated straight from storage, including one written under an
        # allowlist that has since changed. A generation the user is waiting on must not die
        # because the register it recorded is no longer offered.
        assert style_instruction("канцелярский") is None


class TestPromptComposition:
    def _request(self, style):
        return PromptRequest(
            document_type=REFERAT,
            topic="Квантовые вычисления",
            volume_pages=3,
            text_style=style,
        )

    def test_should_place_the_register_before_the_users_own_fields(self):
        prompt = build_prompt(
            PromptRequest(
                document_type=REFERAT,
                topic="Квантовые вычисления",
                volume_pages=3,
                requirements="Ссылки на источники",
                text_style=NAUCHNY,
            )
        )

        instruction = style_instruction(NAUCHNY)
        assert instruction in prompt
        # The register describes the work the template just asked for; a user requirement that
        # contradicts it should read as the later, more specific word.
        assert prompt.index(instruction) < prompt.index("Ссылки на источники")

    def test_should_leave_the_prompt_untouched_when_no_register_was_chosen(self):
        with_none = build_prompt(self._request(None))

        for style in SUPPORTED_TEXT_STYLES:
            assert style_instruction(style) not in with_none, (
                "a request naming no register must not pick one up from anywhere"
            )

    @pytest.mark.parametrize("style", [NAUCHNY, PUBLICISTICHESKY, HUDOZHESTVENNY])
    def test_should_carry_the_chosen_register_into_the_prompt(self, style):
        assert style_instruction(style) in build_prompt(self._request(style))


class TestGenerationEntity:
    def test_should_validate_the_register_on_create(self):
        with pytest.raises(ValidationException):
            Generation.create(
                owner_id=uuid4(),
                topic="Тема",
                volume_pages=3,
                requirements=None,
                extra_wishes=None,
                document_type=REFERAT,
                text_style="канцелярский",
            )

    def test_should_keep_the_sources_register_when_a_retry_names_none(self):
        source = Generation.create(
            owner_id=uuid4(),
            topic="Тема",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type=REFERAT,
            text_style=NAUCHNY,
        )

        # The plain «Повторить» is bodiless, so it must reproduce the run it repeats — including
        # the register. Dropping it here would silently change what the user asked for.
        assert Generation.retry_of(source, idempotency_key="k").text_style == NAUCHNY

    def test_should_take_the_override_when_a_retry_names_a_register(self):
        source = Generation.create(
            owner_id=uuid4(),
            topic="Тема",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type=REFERAT,
            text_style=NAUCHNY,
        )

        retry = Generation.retry_of(source, idempotency_key="k", text_style=HUDOZHESTVENNY)

        assert retry.text_style == HUDOZHESTVENNY
        assert source.text_style == NAUCHNY, "the source row must not be rewritten by its retry"

    def test_should_refuse_a_style_override_outside_the_allowlist(self):
        source = Generation.create(
            owner_id=uuid4(),
            topic="Тема",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type=REFERAT,
            text_style=None,
        )

        # Validated even though nothing else on the retry path is: every other field is copied
        # from a stored row, while this one is a fresh client-supplied value.
        with pytest.raises(ValidationException):
            Generation.retry_of(source, idempotency_key="k", text_style="канцелярский")
