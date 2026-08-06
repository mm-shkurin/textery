import pytest

from document.document_type import (
    DOKLAD,
    ESSE,
    REFERAT,
    SOCHINENIE,
    SUPPORTED_DOCUMENT_TYPES,
)
from generation.prompt_template import _TEMPLATES
from prompt_fixtures import BAN_SENTENCE, last_line, prompt_for

# Which side of the ban each type lands on, **declared by hand** -- the one place
# in these files where a hand-maintained table is the right answer, and the inverse
# of the ADR's reasoning for `TYPES_REQUIRING_SOURCE_BAN`.
#
# Deriving it the way production does (`t in requiring and t not in deferred`)
# restates `_requires_ban` over the same two constants, so both sides move
# together: flip `_BAN_DEFERRED` to `(REFERAT,)` and this stays green with реферат
# unbanned, the exact guard G18 exists to hold. A fifth type would also inherit its
# side silently, "with no case exercising it".
#
# It doubles as this file's non-vacuity anchor -- see the completeness test.
#
# Accepted cost: emptying `_BAN_DEFERRED` when story 1 lands is an edit here too --
# that second red is the coordination check, not a surprise.
EXPECTED_BAN_SIDE = {DOKLAD: False, ESSE: True, SOCHINENIE: True, REFERAT: True}


class TestEverySupportedDocumentTypeYieldsAPrompt:
    """Every supported type has a template, and each template answers to its own type.

    Two claims. (b) the *completeness* claim the module-scope `assert` at
    `prompt_template.py:98` makes today and `python -O` strips, asserted where `-O`
    cannot reach it. (c) that the per-type check discriminates by type rather than
    by truthiness.

    (a), the refusal *mechanism* for a type with no template, lives in
    `test_prompt_type_refusal.py` -- split out when this file hit the 200-line limit.
    """

    def test_should_hold_a_template_for_exactly_the_supported_types(self):
        # G17(b), and the half that the removal test in the refusal file does *not*
        # cover: that test exercises the refusal mechanism and is green whether
        # `_TEMPLATES` covers `SUPPORTED_DOCUMENT_TYPES` or not, so the named hazard
        # -- a fifth type added to the tuple before the dict -- passes it unchanged.
        # This is the deleted module-scope `assert`'s claim, moved somewhere
        # `python -O` cannot strip it.
        #
        # Both directions, spelled as two sets rather than one `==`, so the failure
        # message names which type is on which side. The stale-template direction
        # (a key for a type dropped from the tuple) is caught by nothing else today.
        #
        # The anchor that keeps both differences from being vacuously empty. Two
        # empty sets satisfy the equality, and an empty `SUPPORTED_DOCUMENT_TYPES`
        # is not a hypothetical failure mode here: the two parametrized guards
        # below would collect **zero cases** and report as skipped rather than
        # failed, so the whole file would go quiet at once.
        #
        # Anchored against `EXPECTED_BAN_SIDE` rather than a retyped set literal:
        # `==`, not the `>=` this used to carry, because a superset check is silent
        # about a type that joined the allowlist and it is the *equality* that makes
        # a fifth type one deliberate red in one place. Reusing the hand-declared
        # table rather than typing the four names a third time (they are already in
        # `EXPECTED_BAN_SIDE` and in `test_referat_ban.py`) keeps that one place one.
        assert set(SUPPORTED_DOCUMENT_TYPES) == set(EXPECTED_BAN_SIDE), (
            f"SUPPORTED_DOCUMENT_TYPES and the hand-declared EXPECTED_BAN_SIDE have "
            f"diverged -- declare the new type's side of the ban deliberately: "
            f"supported {sorted(SUPPORTED_DOCUMENT_TYPES)}, declared "
            f"{sorted(EXPECTED_BAN_SIDE)}"
        )

        missing = sorted(set(SUPPORTED_DOCUMENT_TYPES) - set(_TEMPLATES))
        stale = sorted(set(_TEMPLATES) - set(SUPPORTED_DOCUMENT_TYPES))

        assert missing == [], f"these supported document types have no prompt template: {missing}"
        assert stale == [], (
            f"these templates are keyed by a type no longer in SUPPORTED_DOCUMENT_TYPES: {stale}"
        )

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    def test_should_build_a_prompt_that_names_its_own_type(self, document_type):
        # G18's first half. `assert built` is satisfied by a prompt built for the
        # *wrong* type, so the check has to discriminate. `test_prompt_goldens.py`
        # pins today's four byte for byte, but a golden is a hand-typed literal per
        # type: a fifth type joins SUPPORTED_DOCUMENT_TYPES with no golden and
        # `KeyError`s there. This one is parametrized over the tuple.
        prompt = prompt_for(document_type)
        lines = prompt.splitlines()

        # Multiplicity and position, not bare membership. A plain `in` is satisfied
        # by the type name emitted anywhere, any number of times -- including spliced
        # into the ban line or repeated once per section. Both halves are checkable
        # for a type that has no golden yet, which is the whole reason this guard is
        # parametrized instead of hand-typed; where *within* the first line the name
        # sits is what `test_prompt_goldens.py` pins, byte for byte, for the four
        # types that exist today.
        assert prompt.count(document_type) == 1, (
            f"the {document_type} prompt must name its own type exactly once, got "
            f"{prompt.count(document_type)}: {prompt!r}"
        )
        assert document_type in lines[0], (
            f"the {document_type} prompt does not name its own type on its first line: {prompt!r}"
        )

        # The naming check alone is a tautology for реферат: `_referat` hardcodes
        # "реферат" in `Напиши реферат на тему:` rather than interpolating
        # `request.document_type`. Rewrite the dispatch to a constant
        # `_TEMPLATES[REFERAT](request)` and that parameter still passes -- the
        # "fifth key pointed at `_referat`" hazard this test is named for, green on
        # the one type it is easiest to check. Distinctness closes it: a dispatch
        # that ignores the request makes every prompt identical.
        collisions = sorted(
            other
            for other in SUPPORTED_DOCUMENT_TYPES
            if other != document_type and prompt_for(other) == prompt
        )

        assert collisions == [], (
            f"the {document_type} prompt is byte-identical to {collisions} -- the "
            f"template dispatch is not reading the requested type: {prompt!r}"
        )

    @pytest.mark.parametrize("document_type", SUPPORTED_DOCUMENT_TYPES)
    def test_should_land_every_type_on_its_declared_side_of_the_ban(self, document_type):
        # G18's second half. `test_referat_ban.py` asserts the ban over
        # `types_requiring_the_ban_now()` and its absence over `_BAN_DEFERRED` --
        # both derived sets, one collection assertion each. Restated here per type
        # because the derived-set form reports "these types lack the ban" without a
        # case existing for a type that is in neither derived set.
        #
        # The *scope* is not re-asserted here:
        # `test_should_derive_the_ban_s_scope_from_the_supported_types` owns it, and
        # pinning it twice makes a scope change two edits in two files.
        #
        # A missing key is failed explicitly rather than left to raise `KeyError`:
        # a fifth type with no declared side should report as "declare which side
        # this type is on", not as a dict lookup.
        assert document_type in EXPECTED_BAN_SIDE, (
            f"{document_type} joined SUPPORTED_DOCUMENT_TYPES with no declared side of "
            f"the source ban -- add it to EXPECTED_BAN_SIDE deliberately"
        )
        should_carry_ban = EXPECTED_BAN_SIDE[document_type]

        prompt = prompt_for(document_type)

        # `last_line(...) ==` rather than `BAN_SENTENCE in`, because the ban's
        # position is its contract: a substring check is satisfied by the ban folded
        # into a neighbouring sentence, or emitted before the user's own `topic`,
        # where a hostile topic countermands it. This is also `last_line`'s second
        # consumer -- the reason it moved into `prompt_fixtures`.
        assert (last_line(prompt) == BAN_SENTENCE) is should_carry_ban, (
            f"{document_type} should{'' if should_carry_ban else ' not'} carry the "
            f"source ban as its last line and does{' not' if should_carry_ban else ''}: "
            f"{prompt!r}"
        )

        # The count is what makes the two branches equally strong. On its own the
        # position check above degrades, on the negative branch, to "the ban is not
        # the *last* line" -- which a доклад prompt carrying the ban in the middle
        # satisfies while shipping exactly the text `_BAN_DEFERRED` freezes out.
        # On the positive branch it rules out the ban being repeated, with only the
        # final copy checked. `test_referat_ban.py` owns both claims for реферат and
        # for the derived sets; this is them restated at G18's per-type scope.
        expected_occurrences = 1 if should_carry_ban else 0
        assert prompt.count(BAN_SENTENCE) == expected_occurrences, (
            f"the {document_type} prompt must contain the source ban exactly "
            f"{expected_occurrences} time(s), got {prompt.count(BAN_SENTENCE)}: {prompt!r}"
        )
