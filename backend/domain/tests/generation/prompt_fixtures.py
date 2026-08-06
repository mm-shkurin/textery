"""Constants and helpers shared by the four prompt-template test files.

A sibling module rather than a `conftest.py`, mirroring `gigachat_fixtures`:
these are plain callables a test body reads top-to-bottom, not pytest fixtures,
and `conftest.py` is the one path `[tool.mypy]` excludes -- moving this reasoning
there would take it out of type checking for no gain.

Only names with two or more consumers live here. A helper used by exactly one of
the four files stays in that file, where the guard it serves can be read next to
it.
"""

import unicodedata
from typing import cast

import pytest

from generation.generation import MAX_VOLUME_PAGES
from generation.prompt_template import (
    _BAN_DEFERRED,
    TYPES_REQUIRING_SOURCE_BAN,
    PromptBuildError,
    PromptRequest,
    build_prompt,
)

TOPIC = "Как работает фотосинтез"

# The volume every prompt is built at, unless a test varies it deliberately.
# A single digit on purpose: `VOLUME_PAGES_TWO_DIGIT` is the other half of the pair
# G15 needs, and naming both makes the digit-width variation a stated dimension of
# the overhead guard rather than an accident of whichever number was typed first.
VOLUME_PAGES = 5
VOLUME_PAGES_TWO_DIGIT = MAX_VOLUME_PAGES

# Pinned verbatim from the ADR's Model section. G11 asserts this sentence's
# position and G13 its character class, and neither is writable against a
# paraphrase or an unquoted string.
BAN_SENTENCE = "Не включай список литературы и не ссылайся на источники."

# The ban line's own byte cost, derived from the sentence already pinned above
# rather than hand-typed a second time. `_plain`'s overhead guard subtracts this
# from the whole built prompt, which is what lets one constant cover the banned
# and the deferred type alike.
BAN_LINE_BYTES = len(("\n" + BAN_SENTENCE).encode("utf-8"))


def prompt_request(
    document_type: str,
    topic: object = TOPIC,
    volume_pages: object = VOLUME_PAGES,
) -> PromptRequest:
    """The request every build in these files is composed from.

    Extracted so that `PromptRequest(...)` is constructed in exactly one place: the
    determinism guard needs the request itself rather than the built string, and
    constructing it inline there would put the reasoning below in two shapes, one of
    which a future field addition would be edited out of.

    The *default* `volume_pages` is a renderable value rather than `None`, so that
    scenario 1.1/1.2's builds keep succeeding: an optional field defaulting to
    `None` would make every one of them raise once the range guard landed, and the
    seven tests routing through here would go red for a reason that has nothing to
    do with what they assert. Passing an *unrenderable* value explicitly is a
    supported use, and 1.3's refusal guards depend on it.

    Both parameters are typed `object` rather than `str`/`int` for that reason. The
    narrow annotations were a lie the refusal tests already contradict -- `None` is
    not an `int`, and `bool` *is* one to mypy, so `volume_pages: int` asserted the
    exact opposite of what the bool guard exists to prove. `object` states what the
    helper is: a pass-through for values under test, renderable or not.

    The two `cast`s are where that honesty stops and `PromptRequest.__init__`'s own
    annotations begin. They are not a silencing of a real error: the refusal guards
    exist precisely because the hydration path constructs a request whose fields do
    not match those annotations, so the cast is the test-side statement that an
    unrenderable value is *constructible* -- which is the premise
    `_reject_unrenderable_fields` is written against.
    """
    return PromptRequest(
        document_type=document_type,
        topic=cast(str, topic),
        volume_pages=cast(int, volume_pages),
    )


def prompt_for(
    document_type: str,
    topic: object = TOPIC,
    volume_pages: object = VOLUME_PAGES,
) -> str:
    """The built prompt, exactly as the model would receive it.

    Kept raw: the ban sentence is pinned verbatim, so the assertions reading it see
    a capital `Н` that a lowercasing helper would erase.
    """
    return build_prompt(prompt_request(document_type, topic=topic, volume_pages=volume_pages))


def assert_refusal(
    exc_info: pytest.ExceptionInfo[PromptBuildError], expected_message: str
) -> None:
    """The two things every refusal in these files must be, asserted together.

    Extracted because the pair was written out three times in
    `test_prompt_build_refusals.py`: a wording change to either failure text used to
    be three edits, and a fourth refusal guard could have been added with only one of
    the two halves. Moved here from that file when `test_prompt_type_refusal.py`
    became its second consumer and retyped both halves twice more -- the same reason
    `last_line` moved, and the same fail-open: a fifth guard written against only the
    message would have been green on a subclass.

    The `with pytest.raises(...)` act stays inline at each call site -- folding it in
    here would hide which request is being built, which is the one thing the call
    sites differ on.

    `type(...) is`, not `isinstance`: `PromptBuildError` is deliberately the base of
    a family, so an implementation that raised `UnsupportedDocumentTypeError` for a
    `volume_pages` of `-3` would satisfy `pytest.raises` alone while reporting the
    wrong cause to the call site.

    `==` on a constant with no interpolation slot, which is also what keeps the
    rejected value out of the message: `generate_document.py` interpolates the caught
    error into the log, so a message that quoted the offending field would put
    user-supplied text there through the error path. It matters most on `topic`,
    which is free user text the natural implementation would quote. The missing
    template refusal is the stated exception -- the ADR specifies that one verbatim
    with the offending type interpolated -- and it passes its own interpolated
    constant in, so the `==` is unchanged.
    """
    assert type(exc_info.value) is PromptBuildError, (
        f"a refusal must raise the base PromptBuildError itself, got "
        f"{type(exc_info.value).__name__}"
    )
    assert str(exc_info.value) == expected_message, (
        f"unexpected refusal message: {str(exc_info.value)!r}"
    )


def last_line(prompt: str) -> str:
    """The final line of `prompt`.

    Moved here from `test_referat_ban.py` when the per-type ban guard became its
    second consumer. The ban's *position* is the contract, and spelled inline in
    two files a change to what "last" means (trailing newline, \\r\\n) is two edits
    in two shapes -- with the per-type guard's negative branch the one that would
    silently keep passing.
    """
    return prompt.splitlines()[-1]


def ban_scope() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`(TYPES_REQUIRING_SOURCE_BAN, _BAN_DEFERRED)`, exactly as the module declares them.

    Both names are imported at module scope. They were once imported inside this
    helper because neither existed and a module-level import of a missing name is a
    *collection* error that no skip marker can silence -- but scenario 1.2 landed
    both, so the local import and its `noqa` were guarding nothing and hiding a real
    coupling. `test_prompt_build_refusals.py` has since shed its own deferred
    `PromptBuildError` import for the same reason and on the same evidence.
    """
    return TYPES_REQUIRING_SOURCE_BAN, _BAN_DEFERRED


def types_requiring_the_ban_now() -> list[str]:
    """The types whose template must carry the ban today.

    Pure derivation, no assertion: the two operands are pinned by
    `test_should_derive_the_ban_s_scope_from_the_supported_types`. Asserting the
    scope in here instead would attribute a mis-declared set to whichever ban test
    happened to call the helper first, and both callers are named after the ban
    text rather than after the set.
    """
    requiring, deferred = ban_scope()
    return sorted(set(requiring) - set(deferred))


def non_cyrillic_letters(prompt: str) -> list[str]:
    """The letters of `prompt` that are not Cyrillic, in order.

    `name(ch, "")` rather than `name(ch)`: an unnamed code point makes the bare
    call raise ValueError, which surfaces as a test *error* whose message names
    unicodedata rather than the offending prompt. With the default it fails the
    startswith and is reported as the violation it is.
    """
    return [
        ch for ch in prompt if ch.isalpha() and not unicodedata.name(ch, "").startswith("CYRILLIC")
    ]
