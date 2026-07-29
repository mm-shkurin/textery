from dataclasses import dataclass

from shared.exceptions import ValidationException

INVALID_TITLE_INTENT_ERROR_CODE = "INVALID_TITLE_INTENT"

# CLIENT-FACING, and the only handler in the stack that echoes `exc.message`
# verbatim is the one this code routes to -- `validation_exception_handler`
# returns `{"error_code": exc.error_code, "message": exc.message}` unsubstituted,
# where the 404/409/500 handlers all swap in a fixed constant. So this sentence
# is read by a client, and it says what was wrong without naming a domain class
# or a constructor signature (Security 5.1 -- the same reason that file gives for
# not echoing `str(exc)`). The developer-facing detail lives on
# `_CONTRADICTION_DETAIL`, off the wire, exactly as `ExportFormat.parse` keeps its
# internal ValueError text off the wire.
INVALID_TITLE_INTENT_MESSAGE = "A title cannot be set and cleared at the same time."

# STAGED, NOT YET DELIVERED ANYWHERE -- do not read the `from` chain below as a
# working diagnostic. `validation_exception_handler` is the one handler in
# `exception_handlers.py` with no `logger` call at all (404, 409 and 500 all log),
# so this string currently reaches neither the wire (correct) nor the log (not
# yet). It is kept rather than deleted because the missing log line is already
# chartered to adapters-discovery, alongside the `_ERROR_CODE_STATUS_MAP` entry;
# it becomes load-bearing the moment that guard lands. Until then nothing pins it
# -- blanking this constant, or dropping the `from` clause, fails no test.
_CONTRADICTION_DETAIL = (
    "a clear carries no title to write: TitleUpdate(value=..., clears=True) "
    "asks for an erasure and a write at once, and its readers disagree"
)


@dataclass(frozen=True)
class TitleUpdate:
    """Three-state title intent carried across the save port.

    `title: str | None` can no longer express intent once a blank title means
    "preserve" -- `None` would be ambiguous between preserve and clear. This
    value object names the intent instead, so the rest adapter's Pydantic
    details never reach the usecase.

    The three states, and the ONLY three the constructor can produce:

        preserve  (value=None,  clears=False)  leave the stored title alone
        clear     (value=None,  clears=True)   SET title = NULL
        set       (value=<str>, clears=False)  store the string verbatim

    `clears` carries a default so a two-state expectation reads as the state it
    names, but it is NOT a fourth degree of freedom: `__post_init__` rejects the
    contradictory `(value=<str>, clears=True)` outright and folds a blank string
    down to preserve, so the 2x2 product collapses back to the three-point sum.
    Both rules live on the TYPE rather than on one classmethod or one caller --
    see decisions/blank-title-semantics-decision.md.
    """

    # No default: `TitleUpdate()` would be a second, unnamed way to build the
    # preserve state, which is the ambiguity the named factories below exist to
    # remove. `preserve()`, `clear()` and `of()` are the only doors.
    value: str | None
    clears: bool = False

    def __post_init__(self) -> None:
        """Reject the contradiction, THEN normalise blank -- on every construction path.

        That order is load-bearing and is why these are two statements rather
        than one expression. Normalising first folds `(value="", clears=True)`
        down to `(value=None, clears=True)`, which is indistinguishable from a
        legitimate `clear()` -- so a caller confusing "the user emptied the
        field" with "the user asked for an erasure" gets its wipe honoured
        instead of refused. Exactly one test catches the swap:
        `TestTitleUpdateRefusesToCarryAValueAndAClearAtOnce
        ::test_should_reject_a_flagged_blank_before_normalising_it_away`.

        Blankness used to be decided by `SaveDocument._title_intent`, one caller
        deep. Anything else that built an intent -- the rest route mapping a
        Pydantic field, a create-with-title endpoint, an import -- could hand
        `TitleUpdate(value="")` straight to the CAS and reopen `SET title = ''`
        over a stored title. Here it is unreachable by construction.

        A blank NORMALISES rather than raising: `of()` is reached from the raw
        wire arm with whatever the client sent, and a save must never fail over a
        blank title -- the content update riding along with it would be lost.

        Blankness is TESTED, never applied: only an all-whitespace value is
        replaced, so a legitimate `" Отчёт "` keeps its padding byte for byte.
        The rejected `value.strip() or None` would have trimmed every real title
        as a side effect.

        A value plus `clears` is a CONTRADICTION, not a state, and its two readers
        resolve it oppositely -- the db CAS writes the value and ignores the flag,
        a clears-first reader nulls the column and discards the value. Raising is
        what stops "which consumer read it" from deciding a user's data.

        It raises a `ValidationException`, never a builtin: the rest stack
        registers handlers for that family only, so a `ValueError` here would
        leave as a mute `500 INTERNAL_ERROR` telling the caller nothing, on the
        same save whose content update is already lost.
        """
        if self.clears and self.value is not None:
            raise ValidationException(
                error_code=INVALID_TITLE_INTENT_ERROR_CODE,
                message=INVALID_TITLE_INTENT_MESSAGE,
            ) from ValueError(_CONTRADICTION_DETAIL)
        if self.value is not None and self.value.strip() == "":
            object.__setattr__(self, "value", None)

    @classmethod
    def preserve(cls) -> "TitleUpdate":
        return cls(value=None)

    @classmethod
    def clear(cls) -> "TitleUpdate":
        """The deliberate erasure -- the wire's explicit `"title": null`.

        Spelled by a FLAG, never by a sentinel value: any string standing in for
        "cleared" is a string the CAS would faithfully store as the user's title.
        """
        return cls(value=None, clears=True)

    @classmethod
    def of(cls, value: str) -> "TitleUpdate":
        return cls(value=value)

    def carries_a_value(self) -> bool:
        """Does this intent name a title to WRITE into the title column?

        The three-state intent is what this VO exists to express, so reading it
        must not mean null-testing `value` at the call site -- that is exactly the
        `str | None` ambiguity the class replaces, re-derived one layer out.

        False for BOTH title-less states -- `preserve()` and `clear()` -- which is
        why it is not sufficient on its own: a consumer that omits the title
        column whenever this is false turns every clear into a silent no-op. Pair
        it with `erases()`, which must be asked FIRST.
        """
        return self.value is not None

    def erases(self) -> bool:
        """Does this intent ask for the stored title to be removed?

        Exists so consumers stop reaching for the raw `clears` field: a bare
        attribute read is intent re-derived at the call site, the very ambiguity
        this class removes. Only `clear()` is true.
        """
        return self.clears
