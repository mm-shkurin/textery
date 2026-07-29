"""Scenario 3.2 -- the three title intents must be three DISTINCT values.

`decisions/blank-title-semantics-decision.md` names three states: preserve
(absent or blank), clear (an explicit `null` -> `SET title = NULL`), and set (a
real string, stored verbatim). `TitleUpdate` is the domain's name for that
intent, and until now it has carried ONE field -- so `preserve()` is
`TitleUpdate(value=None)` and the only value a `clear()` could possibly take is
the same object. Under frozen-dataclass equality the two states are literally
equal, which makes every equality assertion in the suite blind to the exact swap
the ADR forbids: a green that routed BLANK titles to `clear()` would wipe stored
titles on ordinary autosaves and pass `assert_forwarded_title_update` untouched.

Each state is pinned STRUCTURALLY -- `TitleUpdate(value=..., clears=...)`,
naming both fields -- and never against another factory call. An earlier draft
of this file asserted only `clear() != preserve()`, and that inequality was
MEASURED to pass under `clear()` returning `TitleUpdate(value="__CLEARED__")`:
a magic sentinel string that the db CAS would then write as the user's title,
which is worse than the bug the discriminator exists to prevent. `!=` holds for
an infinite family of wrong representations, including an INVERTED
discriminator that flags `preserve()` instead. Only a literal expected value
rules them out, so distinctness is now a consequence of three pinned states
rather than the whole claim.

The last class below moves the blankness rule ONTO the type. Today it lives
only in `SaveDocument.execute`, so any other caller -- the scheduled rest
adapter, a create-with-title endpoint, an import -- can hand `of("")` straight to
the CAS and reopen `SET title = ''`. That is the ADR's own defense-in-depth
argument applied to the write side, where it was never made.

Blank NORMALISES to preserve rather than raising: `of()` is reached from the raw
wire arm with whatever the client sent, and a save must never fail over a blank
title (the ADR rejects the 422 alternative -- it would lose the content update
riding along with it).

Expected values are built INSIDE the test bodies, never at module scope. In RED
the `clears` field does not exist, so a module-level `TitleUpdate(value=None,
clears=False)` raises `TypeError` at import and ERRORS the whole module at
collection instead of FAILING the individual tests -- the defect found in
`65ec3fd`. Every skip marker below sits on a test confirmed to FAIL.
"""

import pytest

from document.title_update import TitleUpdate


class TestTitleUpdateStatesAreDistinguishable:
    """Each of the ADR's three intents has ONE fixed, named representation."""

    @pytest.mark.skip(reason="RED: TitleUpdate has no `clears` field -- the discriminator is gone")
    def test_should_represent_a_preserve_as_an_unflagged_absence(self):
        assert TitleUpdate.preserve() == TitleUpdate(value=None, clears=False), (
            "preserve names no title AND asks for no erasure -- it is the state that "
            "leaves storage alone, so the discriminator must be off"
        )

    @pytest.mark.skip(reason="RED: TitleUpdate has no `clears` field -- the discriminator is gone")
    def test_should_represent_a_clear_as_a_flagged_absence(self):
        assert TitleUpdate.clear() == TitleUpdate(value=None, clears=True), (
            "a clear carries NO title to write -- the erasure is spelled by the flag, "
            "never by a sentinel value, which the CAS would store as the title itself"
        )

    @pytest.mark.skip(reason="RED: TitleUpdate has no `clears` field -- the discriminator is gone")
    def test_should_represent_a_real_title_as_an_unflagged_value(self):
        assert TitleUpdate.of("Привет") == TitleUpdate(value="Привет", clears=False), (
            "a real title names the value to write and asks for no erasure"
        )

    @pytest.mark.skip(reason="RED: TitleUpdate has no `clears` field -- the discriminator is gone")
    def test_should_tell_a_clear_apart_from_a_preserve(self):
        """The ADR-level fact the three pins above imply, stated once on its own.

        Kept because it is the invariant that must survive any future change of
        representation: whatever the two states are made of, they are opposite
        instructions and must never compare equal.
        """
        assert TitleUpdate.clear() != TitleUpdate.preserve(), (
            "clear and preserve are opposite instructions -- SET title = NULL versus "
            "leave the stored title alone -- so they must not compare equal"
        )


class TestTitleUpdateRejectsABlankTitleAsAnIntent:
    """`of("")` and `of("   ")` are not a title -- they are the absence of one."""

    @pytest.mark.skip(
        reason="RED: of() accepts a blank title, so the rule lives only in SaveDocument"
    )
    @pytest.mark.parametrize("raw", ["", "   ", "\t\n"], ids=["empty", "spaces", "control"])
    def test_should_normalise_a_blank_title_to_preserve(self, raw):
        """Structural, not `== preserve()`.

        Compared against the factory, a green in which BOTH `of(blank)` and
        `preserve()` returned the same wrong object -- `clears=True` above all,
        which would make every blank autosave a title wipe -- passes all three
        params. The literal is what rules that out.
        """
        assert TitleUpdate.of(raw) == TitleUpdate(value=None, clears=False), (
            f"of({raw!r}) must carry no title intent and ask for no erasure, so no "
            f"caller can write a blank title and no blank can be mistaken for a clear"
        )

    @pytest.mark.skip(reason="RED: TitleUpdate has no `clears` field -- the discriminator is gone")
    def test_should_keep_a_padded_real_title_whole(self):
        """The byte-for-byte guard restated over BOTH fields.

        The `.value`-only guard below cannot see a green that trims nothing but
        flags `clears=True` on a real title. It stays as it is -- unskipped and
        passing -- because it is the regression guard that must be live DURING
        red; this is the same fact widened to the field that does not exist yet.
        """
        padded = " Отчёт "

        assert TitleUpdate.of(padded) == TitleUpdate(value=padded, clears=False), (
            "a real title keeps its padding and asks for no erasure"
        )

    def test_should_keep_a_padded_real_title_byte_for_byte(self):
        """The guard against fixing blankness with `value.strip() or None`.

        Normalising blank to preserve is wanted; trimming every legitimate title
        as a side effect is the exact rewrite the ADR rejects. This one PASSES
        today by design -- it is the tripwire green must not trip, so unlike its
        widened twin above it carries no skip marker and stays live.
        """
        padded = " Отчёт "

        assert TitleUpdate.of(padded).value == padded, (
            "blankness is TESTED, never applied -- a real title keeps its padding"
        )
