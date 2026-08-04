import copy

import pytest

from document.document_type import (
    DOKLAD,
    ESSE,
    REFERAT,
    SOCHINENIE,
    SUPPORTED_DOCUMENT_TYPES,
)
from generation.prompt_template import _TEMPLATES, build_prompt
from prompt_fixtures import (
    VOLUME_PAGES,
    VOLUME_PAGES_TWO_DIGIT,
    non_cyrillic_letters,
    prompt_for,
    prompt_request,
)

# The prompt each type must build, byte for byte. Hand-typed rather than composed
# from the module's own constants: a golden assembled out of `_plain`'s f-string
# would move with it, which is the one thing this scenario exists to forbid. The
# доклад text is the string `GigaChatProvider` composed before this story
# (`gigachat_provider.py:113-116`); the other three are that same text plus the ban
# line, because they are in `TYPES_REQUIRING_SOURCE_BAN` and outside `_BAN_DEFERRED`
# -- writing them against the bare pre-change text is red on arrival, and the
# cheapest-looking fix (widening `_BAN_DEFERRED`) silently unbans half the types.
GOLDEN_PROMPTS = {
    DOKLAD: "доклад на тему: Как работает фотосинтез (5 стр.)",
    ESSE: (
        "эссе на тему: Как работает фотосинтез (5 стр.)\n"
        "Не включай список литературы и не ссылайся на источники."
    ),
    SOCHINENIE: (
        "сочинение на тему: Как работает фотосинтез (5 стр.)\n"
        "Не включай список литературы и не ссылайся на источники."
    ),
    # The volume clause is on реферат too, before the sentence-ending period, the
    # way доклад/`_plain` reads it. `GigaChatProvider` sends ` ({volume_pages} стр.)`
    # for every type today with no branching, and `volume_pages` is required on the
    # request, validated 1..10, and echoed back in the response DTO -- a реферат
    # prompt that omitted it would be the one type that refuses to build on a bad
    # volume and then never states the good one.
    REFERAT: (
        "Напиши реферат на тему: Как работает фотосинтез (5 стр.).\n"
        "Во введении обоснуй актуальность темы и сформулируй цель работы.\n"
        "В основной части раскрой разделы по теме.\n"
        "В заключении сформулируй выводы по проделанной работе.\n"
        "Не включай список литературы и не ссылайся на источники."
    ),
}


class TestADokladPromptIsUnchangedByTheMoveIntoTheDomain:
    """Moving prompt composition into the domain must not reword a single prompt.

    Story 1 is being finished elsewhere against the exact доклад text
    `GigaChatProvider` composes today, so a refactor that "improves" the wording
    changes what a live model returns for work already signed off. The goldens
    below pin all four types rather than доклад alone -- the refactor is asserted
    lossless for every type, not asserted for one and assumed for the rest.

    Rendering `volume_pages` is what makes the доклад text byte-identical. That it
    also puts a user-controlled `int | None` into the prompt for the first time is
    what `test_prompt_build_refusals.py` exists for.
    """

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    def test_should_build_the_prompt_the_provider_composed_before_this_story(self, document_type):
        # `==` on the whole string, not `in` on a fragment: "unchanged" is a claim
        # about every byte, including the ones no other test in this file reads --
        # the spacing around the volume clause, the trailing `)`, the newline
        # before the ban.
        assert prompt_for(document_type) == GOLDEN_PROMPTS[document_type], (
            f"the {document_type} prompt drifted from the text the provider composed "
            f"before this story"
        )

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    def test_should_build_the_same_prompt_twice_from_one_unmutated_request(self, document_type):
        request = prompt_request(document_type)
        # `deepcopy`, not `dict(...)`: a shallow baseline compares equal after an
        # in-place mutation of a field's *value*. Latent while all three fields are
        # `str`/`int`, but 1.6 adds two more and the guard would rot silently.
        before = copy.deepcopy(vars(request))
        templates_before = dict(_TEMPLATES)

        first = build_prompt(request)
        second = build_prompt(request)

        # Both calls against the golden, not `second == first`. The relative form is
        # satisfied by a builder that memoizes the *wrong* string and returns it
        # identically twice; pinning both to the golden asserts which string is the
        # one being repeated, and it is what makes this guard red today rather than
        # a green ratchet.
        assert first == GOLDEN_PROMPTS[document_type], (
            f"the first {document_type} build drifted from the golden"
        )
        assert second == GOLDEN_PROMPTS[document_type], (
            f"the second {document_type} build differs from the first -- the retry "
            f"path would send a different prompt on attempt 2"
        )
        assert vars(request) == before, (
            f"build_prompt mutated its request: {before} -> {vars(request)}"
        )
        # The other half of G9 as the ADR states it. `_TEMPLATES` is the module state
        # the nonce rejection rests on: compared by key *and* callable identity, so a
        # builder that rebound a template to a memoizing wrapper is caught even
        # though the key set is unchanged.
        assert dict(_TEMPLATES) == templates_before, (
            f"build_prompt rewrote module state: {templates_before} -> {dict(_TEMPLATES)}"
        )

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    @pytest.mark.parametrize("volume_pages", (VOLUME_PAGES, VOLUME_PAGES_TWO_DIGIT))
    def test_should_state_the_requested_volume_in_every_type_s_prompt(
        self, document_type, volume_pages
    ):
        # The guard whose absence let the omission through. Every golden above pins
        # one type's whole string, so a type that silently dropped the volume clause
        # was caught only if someone noticed while typing that type's golden -- and
        # for реферат nobody did: the clause was written out of `_referat` in 1.1 and
        # both review passes over 7690851a had to find it by reading
        # `gigachat_provider.py:113-116` and diffing the branch-free behaviour there
        # against the new template.
        #
        # Stated as a cross-type invariant rather than as four more golden bytes so
        # that a fifth type cannot join `SUPPORTED_DOCUMENT_TYPES` with a template
        # that quietly discards a required, range-validated, DTO-echoed field. Both
        # digit widths, because a clause built by slicing or padding a fixed-width
        # number would satisfy the single-digit arm alone.
        prompt = prompt_for(document_type, volume_pages=volume_pages)

        assert str(volume_pages) in prompt, (
            f"the {document_type} prompt does not communicate volume_pages="
            f"{volume_pages}, a field the request requires and the response echoes: "
            f"{prompt!r}"
        )

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    def test_should_spell_every_type_s_prompt_entirely_in_cyrillic(self, document_type):
        # Restated per type at G6's scope, because this scenario goldens `на тему:`
        # and `стр.` for the first time and four of the five homoglyph-bearing
        # characters live in those two fragments (`а`/`е` in `на тему:`, `с`/`р` in
        # `стр.`). A Latin `c` in `стр.` renders identically and would pass a
        # hand-typed golden carrying the same mistake.
        latin_lookalikes = non_cyrillic_letters(prompt_for(document_type))

        assert latin_lookalikes == [], (
            f"non-Cyrillic letters in the {document_type} prompt: {latin_lookalikes}"
        )
