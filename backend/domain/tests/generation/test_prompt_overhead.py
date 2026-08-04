import pytest

from document.document_type import DOKLAD, ESSE, REFERAT, SOCHINENIE
from prompt_fixtures import (
    BAN_LINE_BYTES,
    VOLUME_PAGES,
    VOLUME_PAGES_TWO_DIGIT,
    prompt_for,
    types_requiring_the_ban_now,
)

# A one-character topic, subtracted back out to recover the empty-topic overhead.
# `topic=""` cannot be used directly: the ADR's Edge Cases table specifies that an
# empty or whitespace-only topic raises PromptBuildError, so a literal `topic=""`
# build would become unreachable the moment that edge case lands and this guard
# would have to be rewritten or deleted. Cyrillic so the sentinel itself cannot
# trip G13 if a future assertion reuses this build.
OVERHEAD_PROBE_TOPIC = "а"

# The three types `_plain` renders.
PLAIN_DOCUMENT_TYPES = (DOKLAD, ESSE, SOCHINENIE)

# `_plain`'s fixed overhead: its line less the interpolated `document_type`, `topic`
# and `volume_pages`, in UTF-8 bytes. One constant covers all three types precisely
# because all three variable parts are subtracted back out -- `_referat`'s constant
# cannot be reused, since that template hardcodes its type name and interpolates no
# volume. Pinning one type at one volume instead would be vacuous for the other two
# and blind to a digit-width change.
PLAIN_FIXED_OVERHEAD_BYTES = 27

# The реферат template's fixed overhead: the built prompt less the interpolated
# topic *and* the interpolated volume, measured in UTF-8 bytes. The unit is named
# because the template is Cyrillic -- a code-point bound and a byte bound differ by
# ~1.8x on exactly this text and a bare len() would silently assert the wrong one.
# Adding a sixth sentence moves this number, whether or not the user's fields are
# anywhere near their caps.
#
# Derived, not measured: 446 was the volume-less template's overhead (448 bytes at
# the one-character probe topic, less that topic's 2). `_referat` now carries the
# same ` ({volume_pages} стр.)` clause `_plain` does, which is 12 UTF-8 bytes with
# the volume itself excluded -- ` (`, ` `, `стр.` at 2 bytes per Cyrillic letter,
# `)`. 446 + 12 = 458 with the volume still counted; the volume is now subtracted
# back out the way `PLAIN_FIXED_OVERHEAD_BYTES` subtracts it, so that a change from
# a one-digit to a two-digit `volume_pages` cannot move a constant that claims to
# bound the *fixed* part. 458 - 1 = 457.
REFERAT_FIXED_OVERHEAD_BYTES = 457


class TestATemplateSFixedOverheadStaysAtItsDeclaredSize:
    """A template that grows a sentence grows every prompt built from it.

    The user's fields are capped; the template's own text is not, and a sixth
    sentence added during a later scenario is billed on every generation without
    anything else in the suite noticing. Both constants below measure the template
    alone, with every interpolated field subtracted back out.
    """

    @pytest.mark.parametrize("document_type", PLAIN_DOCUMENT_TYPES)
    @pytest.mark.parametrize("volume_pages", (VOLUME_PAGES, VOLUME_PAGES_TWO_DIGIT))
    def test_should_keep_the_plain_template_s_fixed_overhead_at_its_declared_size(
        self, document_type, volume_pages
    ):
        built = prompt_for(document_type, topic=OVERHEAD_PROBE_TOPIC, volume_pages=volume_pages)

        # The whole prompt, with the ban's own bytes *derived* and subtracted --
        # deliberately not `splitlines()[0]`. Taking the first line does keep the ban
        # out of a constant meant to bound this template, but it discards any second
        # line `_plain` itself grows, and "a sentence added to `_plain`" is the exact
        # hazard this guard exists for: the measurement would stay at 27 while the
        # template silently doubled in size. Subtracting `BAN_LINE_BYTES` gets the
        # same isolation from a value derived from the already-pinned sentence, so
        # one constant still covers the deferred type and the banned two alike.
        ban_bytes = BAN_LINE_BYTES if document_type in types_requiring_the_ban_now() else 0
        overhead_bytes = (
            len(built.encode("utf-8"))
            - len(document_type.encode("utf-8"))
            - len(OVERHEAD_PROBE_TOPIC.encode("utf-8"))
            - len(str(volume_pages).encode("utf-8"))
            - ban_bytes
        )

        assert overhead_bytes == PLAIN_FIXED_OVERHEAD_BYTES, (
            f"_plain fixed overhead moved, got {overhead_bytes} bytes: {built!r}"
        )

    def test_should_keep_the_referat_template_s_fixed_overhead_at_its_declared_size(self):
        # Measured on the whole build, ban line included, because
        # `REFERAT_FIXED_OVERHEAD_BYTES` is derived from the goldened text that
        # carries it. Only the two interpolated fields are subtracted back out.
        probe = prompt_for(REFERAT, topic=OVERHEAD_PROBE_TOPIC)

        overhead_bytes = (
            len(probe.encode("utf-8"))
            - len(OVERHEAD_PROBE_TOPIC.encode("utf-8"))
            - len(str(VOLUME_PAGES).encode("utf-8"))
        )

        assert overhead_bytes == REFERAT_FIXED_OVERHEAD_BYTES, (
            f"реферат fixed overhead moved, got {overhead_bytes} bytes: {probe}"
        )

    def test_should_probe_the_overhead_at_two_distinct_digit_widths(self):
        # `VOLUME_PAGES_TWO_DIGIT` is `MAX_VOLUME_PAGES`, which is 10 today. Lower the
        # cap to 9 -- a plausible product change, not a contrivance -- and the
        # digit-width dimension of the two guards above degenerates into two
        # single-digit cases that can never disagree, with nothing red to say so. A
        # module-level `assert` would not say it either: it fires at collection and
        # reddens the whole file, which reads as a broken import rather than as the
        # dimension it is.
        assert len(str(VOLUME_PAGES)) == 1, (
            f"VOLUME_PAGES must be the one-digit half of the pair, got {VOLUME_PAGES}"
        )
        assert len(str(VOLUME_PAGES_TWO_DIGIT)) == 2, (
            f"VOLUME_PAGES_TWO_DIGIT must be the two-digit half of the pair, got "
            f"{VOLUME_PAGES_TWO_DIGIT} -- MAX_VOLUME_PAGES has dropped below 10 and "
            f"the digit-width dimension of the overhead guards is now vacuous"
        )
