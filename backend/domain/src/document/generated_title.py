import unicodedata

# The stored title is what the history list shows and what story 17 derives the
# export filename from. Capped because the topic it comes from is user input with
# its own 500-character bound (Generation.MAX_TOPIC_LENGTH) — a title that long is
# not a title, it is the first paragraph, and it would push every history row and
# every Content-Disposition header out of shape.
MAX_GENERATED_TITLE_LENGTH = 120

# What a document is called when its generation carries no usable topic. Not an
# empty string: an untitled document reaches the export filename derivation, and
# blank there means "fall back to a default" one layer further out — saying it
# once, here, keeps the history list and the filename agreeing.
UNTITLED_FALLBACK = "Без названия"


def derive_generated_title(topic: str | None) -> str:
    """The title a converted generation is stored under.

    Server-derived, never client-supplied: `documents_from_generation.yaml` lists
    `title` among the fields a request body cannot set. Taking it from the topic
    the user actually typed is what makes the history list readable — the
    alternative (the document type, four values shared by every document) makes
    every row say «доклад».

    Truncation cuts on a WORD boundary where one is available, because the title
    is read by a person: «Лексус LS 460 — история модели и техниче» reads as a
    bug, «Лексус LS 460 — история модели и» reads as a title. NFC-normalized
    first so the cap counts the same code points the storage layer will.
    """
    if topic is None:
        return UNTITLED_FALLBACK
    normalized = unicodedata.normalize("NFC", topic).strip()
    if not normalized:
        return UNTITLED_FALLBACK
    if len(normalized) <= MAX_GENERATED_TITLE_LENGTH:
        return normalized
    return _truncate_on_a_word_boundary(normalized)


def _truncate_on_a_word_boundary(normalized_topic: str) -> str:
    clipped = normalized_topic[:MAX_GENERATED_TITLE_LENGTH]
    last_space = clipped.rfind(" ")
    # A topic with no space inside the cap (one very long word, or a script that
    # does not space its words) has no boundary to find; the hard cut is then the
    # only answer, and it is still safe — Python slices code points, so it cannot
    # split a character the way a byte-oriented cut would.
    if last_space <= 0:
        return clipped.rstrip()
    return clipped[:last_space].rstrip()
