import pytest

from document.document_content import MAX_CONTENT_LENGTH, DocumentContent
from document.document_type import DocumentType
from document.idempotency_key import MAX_KEY_LENGTH, IdempotencyKey


class TestDocumentTypeAllowedValues:
    """Scenario 1.1: Reject unsupported document type.

    Given a document type outside the 4 supported values
    When it is constructed
    Then it is rejected
    """

    @pytest.mark.parametrize("raw", ["доклад", "эссе", "сочинение", "реферат"])
    def test_should_accept_each_supported_type(self, raw):
        assert DocumentType(raw).value == raw, f"{raw} should round-trip unchanged"

    @pytest.mark.parametrize(
        "raw",
        ["диссертация", "", "ДОКЛАД", "report", None, 5],
        ids=["unsupported", "empty", "wrong-case", "english", "none", "int"],
    )
    def test_should_reject_anything_else(self, raw):
        with pytest.raises(ValueError) as excinfo:
            DocumentType(raw)

        assert str(excinfo.value) == "Invalid document type.", (
            f"unexpected message for {raw!r}: {excinfo.value}"
        )


class TestDocumentContentLengthBoundary:
    """Scenario 5.2: Accept content exactly at the maximum length, reject one past it.

    The cap is measured on the NFC-normalized string in code points, before
    sanitization. Rejected whole, never truncated.
    """

    def test_should_accept_content_at_exactly_the_maximum(self):
        raw = "a" * MAX_CONTENT_LENGTH

        assert len(DocumentContent(raw).value) == MAX_CONTENT_LENGTH, (
            "content at exactly the cap must be accepted unchanged"
        )

    def test_should_reject_content_one_character_past_the_maximum(self):
        with pytest.raises(ValueError) as excinfo:
            DocumentContent("a" * (MAX_CONTENT_LENGTH + 1))

        assert str(excinfo.value) == "Invalid content.", f"unexpected message: {excinfo.value}"

    def test_should_accept_empty_content(self):
        assert DocumentContent("").value == "", "empty content is valid — a new document has none"


class TestDocumentContentNormalization:
    """Scenario 6.6: canonically-equivalent content compares consistently.

    NFD and NFC of the same visible text must produce the identical stored value,
    or the duplicate-save comparison in 6.2 compares two spellings of one string.
    """

    def test_should_normalize_decomposed_content_to_the_same_value_as_precomposed(self):
        decomposed = "Приве́т"  # 'е' + combining acute
        precomposed = "Приве́т"

        assert DocumentContent(decomposed).value == DocumentContent(precomposed).value, (
            "NFD and NFC of the same visible text must store identically"
        )

    def test_should_cap_the_raw_input_before_normalizing(self):
        # MAX+1 combining pairs: over the cap raw, and still over once NFC composes
        # them. The raw cap is the fail-fast guard; the post-NFC cap is authoritative.
        raw = "é" * (MAX_CONTENT_LENGTH + 1)

        with pytest.raises(ValueError) as excinfo:
            DocumentContent(raw)

        assert str(excinfo.value) == "Invalid content.", f"unexpected message: {excinfo.value}"


class TestDocumentContentAstralPlane:
    """Scenario 6.5: the boundary counts code points, never splitting a character.

    Python's len() counts code points, so an astral emoji is 1 — the surrogate-pair
    split this scenario fears is a JS/Java hazard, not Python's. And nothing is ever
    truncated, so no boundary can cut a character in half.
    """

    def test_should_count_an_astral_emoji_as_one_character(self):
        raw = "\U0001f600" * MAX_CONTENT_LENGTH  # 200_000 code points, 800_000 bytes

        assert DocumentContent(raw).value == raw, (
            "astral content at the cap must round-trip byte-for-byte"
        )

    def test_should_reject_one_astral_character_past_the_maximum(self):
        with pytest.raises(ValueError):
            DocumentContent("\U0001f600" * (MAX_CONTENT_LENGTH + 1))


class TestIdempotencyKey:
    """documents_create.yaml: Idempotency-Key, required, 1-128 characters."""

    def test_should_accept_a_key_at_the_maximum_length(self):
        raw = "k" * MAX_KEY_LENGTH

        assert IdempotencyKey(raw).value == raw

    @pytest.mark.parametrize(
        "raw",
        ["", "k" * (MAX_KEY_LENGTH + 1), None, 5],
        ids=["empty", "too-long", "none", "int"],
    )
    def test_should_reject_an_unusable_key(self, raw):
        with pytest.raises(ValueError) as excinfo:
            IdempotencyKey(raw)

        assert str(excinfo.value) == "Invalid idempotency key.", (
            f"unexpected message for {raw!r}: {excinfo.value}"
        )
