import pytest

from document.document_type import SUPPORTED_DOCUMENT_TYPES
from generation.generation import MAX_VOLUME_PAGES
from prompt_fixtures import prompt_for
from shared.exceptions import DomainException, ValidationException

# The volumes `__init__` accepts today but that must never render, and the topics
# likewise. `MAX_VOLUME_PAGES + 1` rather than a literal: the bound is declared in
# `generation.py` and a test restating it as `11` keeps asserting the old ceiling
# the day the constant moves.
UNRENDERABLE_VOLUMES = (None, 0, -3, MAX_VOLUME_PAGES + 1)
UNRENDERABLE_TOPICS = (None, "", "   ")

# The two refusal messages, decided here rather than deferred to green. They name
# the offending *field* and never interpolate its *value*: `generate_document.py`
# interpolates the caught error into the log, so a message quoting the rejected
# `topic` would put user text in the log through the error path. Asserting `==` on
# a constant with no interpolation slot is what makes that structural rather than
# a promise -- a message that grew a value would no longer equal this string.
VOLUME_PAGES_ERROR_MESSAGE = "volume_pages is not renderable in a prompt"
TOPIC_ERROR_MESSAGE = "topic is not renderable in a prompt"


def _prompt_build_error() -> type[Exception]:
    """`PromptBuildError`, imported at call time rather than at module scope.

    The name did not exist when these guards were written, and a module-level
    import of a missing name is a *collection* error, which reddens every other
    test in this file and cannot be silenced by a skip marker.
    """
    from generation.prompt_template import PromptBuildError  # noqa: PLC0415

    return PromptBuildError


class TestAPromptRefusesAFieldItCannotRender:
    """Rendering `volume_pages` puts a user-controlled `int | None` into the prompt.

    The hydration path applies no range check, so `(None стр.)` and `(-3 стр.)` are
    reachable today and would be billed by a third-party model. A refusal that
    reaches the call site as a *terminal* failure is what keeps a value that cannot
    change on attempt 2 from burning the whole retry budget.
    """

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    @pytest.mark.parametrize("volume_pages", UNRENDERABLE_VOLUMES)
    def test_should_refuse_to_build_a_prompt_for_an_unrenderable_volume(
        self, document_type, volume_pages
    ):
        # Every type, not доклад plus реферат. `_plain` is the template that
        # interpolates the value, so доклад is where the bad render is visible --
        # but a guard written inside `_plain` alone would let реферат keep building
        # from a request no caller should have been allowed to construct, and G3 is
        # stated per type, so the day эссе gets its own template the hole is silent.
        with pytest.raises(_prompt_build_error()) as exc_info:
            prompt_for(document_type, volume_pages=volume_pages)

        # `type(...) is`, not `isinstance`: `PromptBuildError` is deliberately the
        # base of a family, so an implementation that raised
        # `UnsupportedDocumentTypeError` for a `volume_pages` of `-3` would satisfy
        # `pytest.raises` alone while reporting the wrong field to the call site.
        assert type(exc_info.value) is _prompt_build_error(), (
            f"a bad volume must raise the base PromptBuildError itself, got "
            f"{type(exc_info.value).__name__}"
        )
        # `==` on a constant with no interpolation slot, which is also what keeps
        # the rejected value out of the message: `generate_document.py` interpolates
        # the caught error into the log, so a message that quoted `volume_pages`
        # would put a user-supplied value there through the error path.
        assert str(exc_info.value) == VOLUME_PAGES_ERROR_MESSAGE, (
            f"unexpected refusal message: {str(exc_info.value)!r}"
        )

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    @pytest.mark.parametrize("topic", UNRENDERABLE_TOPICS)
    def test_should_refuse_to_build_a_prompt_for_a_missing_or_blank_topic(
        self, document_type, topic
    ):
        # `_required_topic` runs in `Generation.create` and not in `__init__`, so a
        # hydrated generation carries whatever the row holds. `на тему: None` has
        # been reachable since 1.1; it is guarded here because this is the scenario
        # that first builds the exception to raise.
        with pytest.raises(_prompt_build_error()) as exc_info:
            prompt_for(document_type, topic=topic)

        assert type(exc_info.value) is _prompt_build_error(), (
            f"a bad topic must raise the base PromptBuildError itself, got "
            f"{type(exc_info.value).__name__}"
        )
        # The exact-equality form matters more here than on the volume: `topic` is
        # free user text, and the natural implementation quotes the offending value.
        # A message equal to this constant cannot have quoted anything.
        assert str(exc_info.value) == TOPIC_ERROR_MESSAGE, (
            f"unexpected refusal message: {str(exc_info.value)!r}"
        )

    def test_should_raise_a_build_failure_the_call_site_must_not_retry(self):
        error = _prompt_build_error()

        # The base class is 1.3's to choose, not green's to happen upon. Deferring
        # the call-site *mapping* to G5/2.1 does not defer the *default*:
        # `generate_document.py:61` catches bare `Exception` and retries, so an
        # error outside the domain family is retried as if it were transient, and a
        # value that cannot change on attempt 2 burns the whole budget.
        assert issubclass(error, DomainException), (
            f"PromptBuildError must be a domain exception, got bases {error.__bases__}"
        )
        # `ValidationException` is the other wrong answer: it drags in
        # `error_code`/`message` and the REST handler's 422 mapping, which is
        # meaningless on a BackgroundTask path and pre-empts G5's choice.
        assert not issubclass(error, ValidationException), (
            "PromptBuildError must not derive from ValidationException -- that "
            "inherits the REST 422 mapping onto a worker-only failure"
        )
