from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator


def _reject_boolean(value: Any) -> Any:
    """Refuse a JSON boolean where a page count is expected.

    `bool` subclasses `int`, and Pydantic's lax mode coerces `true` to `1` — so a
    plain `int` annotation accepts `{"volume_pages": true}` and the request
    reaches the domain carrying a genuine `1`. Every guard below this point then
    sees an in-range integer and passes it: measured against the running stack
    2026-08-20, both `POST /generations` and the retry answered 201 for a one-page
    generation the caller never asked for, and billed it.

    The domain refuses a `bool` too (`is_out_of_range_volume`), but that guard can
    only fire for a caller that hands it one — and no REST caller ever does,
    because the coercion happens HERE, one layer above. This is the layer where
    the value is still a boolean, so this is the only layer that can tell.

    Deliberately narrower than `StrictInt`, which would also refuse `"8"`. A
    numeric string is a client being loose about JSON types, not a client saying
    something it does not mean; refusing it would be a contract change riding in
    on a bug fix.
    """
    if isinstance(value, bool):
        raise ValueError("volume_pages must be an integer, not a boolean")
    return value


# The page count as it arrives on the wire. Named once and shared by both request
# bodies: the create form and the retry override are the same field with the same
# hole, and a guard applied to one of them is the version that gets forgotten.
VolumePages = Annotated[int, BeforeValidator(_reject_boolean)]


class GenerationRequestDto(BaseModel):
    document_type: str
    topic: str | None = None
    volume_pages: VolumePages | None = None
    requirements: str | None = None
    extra_wishes: str | None = None
    # Optional, and typed `str | None` rather than an Enum: the three registers are
    # the domain's allowlist, and declaring them here would answer a bad value in
    # Pydantic's envelope instead of this API's {error_code, message}. Same reason
    # `document_type` is a bare `str`.
    text_style: str | None = None


class RetryGenerationRequestDto(BaseModel):
    """The optional body of «перегенерировать в другом стиле» / «изменить объём».

    Every other retry parameter is copied from the stored source row, which is what
    keeps the plain «Повторить» button bodiless — these two carry the only values a
    user re-chooses at the moment of a retry. An absent field (or an absent body
    entirely) keeps the source generation's own value.

    `volume_pages` is a bare `int | None` rather than `Field(ge=..., le=...)` for
    the reason the create DTO gives: the bounds live in the domain, so a violation
    answers this API's {error_code, message} instead of Pydantic's envelope. What
    Pydantic still enforces here is the TYPE — a non-integer never reaches the
    domain's range check, which would raise on a comparison rather than refuse.
    """

    text_style: str | None = None
    volume_pages: VolumePages | None = None
