from pydantic import BaseModel


class GenerationRequestDto(BaseModel):
    document_type: str
    topic: str | None = None
    volume_pages: int | None = None
    requirements: str | None = None
    extra_wishes: str | None = None
    # Optional, and typed `str | None` rather than an Enum: the three registers are
    # the domain's allowlist, and declaring them here would answer a bad value in
    # Pydantic's envelope instead of this API's {error_code, message}. Same reason
    # `document_type` is a bare `str`.
    text_style: str | None = None


class RetryGenerationRequestDto(BaseModel):
    """The optional body of «перегенерировать в другом стиле».

    Every other retry parameter is copied from the stored source row, which is
    what keeps the plain «Повторить» button bodiless — this carries the ONE value
    the user re-chooses at the moment of the retry. Absent (or an absent body
    entirely) keeps the source generation's own style.
    """

    text_style: str | None = None
