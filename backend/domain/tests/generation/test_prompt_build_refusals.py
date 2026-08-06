import pytest

from document.document_type import SUPPORTED_DOCUMENT_TYPES
from generation.generation import MAX_VOLUME_PAGES
from generation.prompt_template import PromptBuildError
from prompt_fixtures import assert_refusal, prompt_for
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
#
# Retyped here rather than imported from `prompt_template`, deliberately. Importing
# the production constant would turn every assertion below into
# `str(exc) == the string the code just raised` -- a tautology that passes for any
# message the implementation happens to hold, including one that grew a slot and
# quoted the rejected `topic`. The duplication *is* the guard; do not de-duplicate it.
VOLUME_PAGES_ERROR_MESSAGE = "volume_pages is not renderable in a prompt"
TOPIC_ERROR_MESSAGE = "topic is not renderable in a prompt"


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
        with pytest.raises(PromptBuildError) as exc_info:
            prompt_for(document_type, volume_pages=volume_pages)

        assert_refusal(exc_info, VOLUME_PAGES_ERROR_MESSAGE)

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    @pytest.mark.parametrize("topic", UNRENDERABLE_TOPICS)
    def test_should_refuse_to_build_a_prompt_for_a_missing_or_blank_topic(
        self, document_type, topic
    ):
        # `_required_topic` runs in `Generation.create` and not in `__init__`, so a
        # hydrated generation carries whatever the row holds. `на тему: None` has
        # been reachable since 1.1; it is guarded here because this is the scenario
        # that first builds the exception to raise.
        with pytest.raises(PromptBuildError) as exc_info:
            prompt_for(document_type, topic=topic)

        assert_refusal(exc_info, TOPIC_ERROR_MESSAGE)

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    def test_should_refuse_a_boolean_volume_the_range_check_cannot_catch(self, document_type):
        # Its own test rather than a fifth member of UNRENDERABLE_VOLUMES, because
        # `True` is the one unrenderable volume that is *inside* the accepted range.
        # The other four are refused by the range comparison; a reader who saw
        # `True` sitting beside `-3` would reasonably assume the same branch covers
        # it, and would delete the type check as redundant.
        #
        # The numeric twin is what makes that assumption checkable rather than
        # folklore, and it is checked against the production builder rather than
        # against the two bound constants: `MIN_VOLUME_PAGES <= True <=
        # MAX_VOLUME_PAGES` restates arithmetic that is true of the constants alone
        # and exercises no code. Building at `int(True)` states the same premise by
        # observing it -- if this build raised, `True` would be out of range and the
        # bool arm below would be the redundancy the reader suspected.
        numeric_twin = int(True)
        twin_prompt = prompt_for(document_type, volume_pages=numeric_twin)

        # And this is the harm itself, asserted rather than described. It is a
        # *rendered* harm: `True == 1`, so with the bool arm gone `_plain` builds
        # `... (True стр.)` and `_referat` builds `(True стр.).` -- Latin letters in
        # a Russian prompt, billed to the provider and shipped to the student. The
        # refusal below produces no string to inspect, so the clause is pinned here,
        # on the one input that differs from `True` by type alone. `count(...) == 1`
        # rather than `in`: the clause appears exactly once, and an implementation
        # that emitted it twice or appended a second volume clause would satisfy a
        # containment check.
        #
        # Only the clause, not the character class: `test_prompt_goldens.py`'s
        # `test_should_spell_every_type_s_prompt_entirely_in_cyrillic` already owns
        # the no-Latin-letters guard per type, and restating it here at volume 1
        # instead of volume 5 would assert nothing that guard does not.
        assert twin_prompt.count(f"({numeric_twin} стр.)") == 1, (
            f"the volume clause must render the digit exactly once, got {twin_prompt!r}"
        )

        # Same numeric value, `bool` instead of `int` -- and now it must be refused.
        with pytest.raises(PromptBuildError) as exc_info:
            prompt_for(document_type, volume_pages=True)

        # The same message as every other unrenderable volume: the call site maps on
        # the type, and a bool is not a distinct user-facing failure mode.
        assert_refusal(exc_info, VOLUME_PAGES_ERROR_MESSAGE)

    def test_should_raise_a_build_failure_the_call_site_must_not_retry(self):
        error = PromptBuildError

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
