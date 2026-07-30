from document.generated_title import (
    MAX_GENERATED_TITLE_LENGTH,
    UNTITLED_FALLBACK,
    derive_generated_title,
)


class TestTitleComesFromTheTopicTheUserTyped:
    """The history list is the reason this is not the document type.

    All four document types are shared by every document, so deriving from the
    type would make every history row read «доклад». The topic is the only field
    that distinguishes one generated document from another.
    """

    def test_should_use_the_topic_verbatim_when_it_fits(self):
        assert derive_generated_title("Лексус LS 460") == "Лексус LS 460"

    def test_should_strip_surrounding_whitespace(self):
        assert derive_generated_title("  Лексус LS 460  ") == "Лексус LS 460"

    def test_should_normalize_to_nfc_so_the_cap_counts_stored_code_points(self):
        # "й" decomposed is и + U+0306 (two code points), composed it is
        # one. Spelled in escapes rather than literal glyphs so the test states
        # which form it means instead of depending on how an editor saved the file.
        decomposed = "й обзор"
        composed = "й обзор"
        assert len(decomposed) == len(composed) + 1, "the two forms must differ in length"

        assert derive_generated_title(decomposed) == composed


class TestAnAbsentTopicStillYieldsAReadableTitle:
    """A titleless document reaches the history list AND the export filename.

    Saying the fallback once, here, is what keeps those two agreeing.
    """

    def test_should_fall_back_when_the_topic_is_missing(self):
        assert derive_generated_title(None) == UNTITLED_FALLBACK

    def test_should_fall_back_when_the_topic_is_empty(self):
        assert derive_generated_title("") == UNTITLED_FALLBACK

    def test_should_fall_back_when_the_topic_is_only_whitespace(self):
        assert derive_generated_title("   \n\t ") == UNTITLED_FALLBACK


class TestALongTopicIsTruncatedForAPersonToRead:
    """The topic's own bound is 500 characters; a title that long is a paragraph."""

    def test_should_not_exceed_the_cap(self):
        topic = "слово " * 100

        assert len(derive_generated_title(topic)) <= MAX_GENERATED_TITLE_LENGTH

    def test_should_cut_on_a_word_boundary_rather_than_mid_word(self):
        topic = "Лексус " * 40

        result = derive_generated_title(topic)

        assert result.endswith("Лексус"), f"cut mid-word: {result!r}"

    def test_should_hard_cut_a_single_unbroken_word(self):
        # No boundary exists inside the cap, so the hard cut is the only answer —
        # and it is still character-safe, because Python slices code points.
        topic = "а" * 300

        result = derive_generated_title(topic)

        assert result == "а" * MAX_GENERATED_TITLE_LENGTH

    def test_should_not_leave_trailing_whitespace_after_the_cut(self):
        topic = "Лексус " * 40

        assert derive_generated_title(topic) == derive_generated_title(topic).rstrip()
