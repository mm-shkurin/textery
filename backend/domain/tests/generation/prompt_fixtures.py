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

from generation.generation import MAX_VOLUME_PAGES
from generation.prompt_template import (
    _BAN_DEFERRED,
    TYPES_REQUIRING_SOURCE_BAN,
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
    topic: str = TOPIC,
    volume_pages: int = VOLUME_PAGES,
) -> PromptRequest:
    """The request every build in these files is composed from.

    Extracted so that `PromptRequest(...)` is constructed in exactly one place: the
    determinism guard needs the request itself rather than the built string, and
    constructing it inline there would put the reasoning below in two shapes, one of
    which a future field addition would be edited out of.

    `volume_pages` is passed on every build rather than defaulted inside
    `PromptRequest`: an optional field defaulting to `None` would make every one of
    scenario 1.1/1.2's builds raise once the range guard below lands, so the
    seven tests routing through here would go red for a reason that has nothing to
    do with what they assert.
    """
    return PromptRequest(document_type=document_type, topic=topic, volume_pages=volume_pages)


def prompt_for(
    document_type: str,
    topic: str = TOPIC,
    volume_pages: int = VOLUME_PAGES,
) -> str:
    """The built prompt, exactly as the model would receive it.

    Kept raw: the ban sentence is pinned verbatim, so the assertions reading it see
    a capital `Н` that a lowercasing helper would erase.
    """
    return build_prompt(prompt_request(document_type, topic=topic, volume_pages=volume_pages))


def ban_scope():
    """`(TYPES_REQUIRING_SOURCE_BAN, _BAN_DEFERRED)`, exactly as the module declares them.

    Both names are imported at module scope. They were once imported inside this
    helper because neither existed and a module-level import of a missing name is a
    *collection* error that no skip marker can silence -- but scenario 1.2 landed
    both, so the local import and its `noqa` were guarding nothing and hiding a real
    coupling. `_prompt_build_error` in `test_prompt_build_refusals.py` keeps the
    deferred form, because `PromptBuildError` genuinely does not exist yet.
    """
    return TYPES_REQUIRING_SOURCE_BAN, _BAN_DEFERRED


def types_requiring_the_ban_now():
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
