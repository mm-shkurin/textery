from pydantic import BaseModel


class RegisterRequestDto(BaseModel):
    """The registration body, EXTENDED by Story 14 and not modified.

    The five `utm_*` are optional and typed `object` rather than `str | None`. A
    strict annotation would make an over-long or non-string campaign parameter a
    **422 on registration** -- a new way for account creation to fail, invented
    by a marketing attribute, on the most sensitive route in the product. The
    governing decision of Story 14 forbids exactly that: attribution decides what
    is STORED, never what is ANSWERED (`endpoints.md`, "Attribution is fail-open
    on both auth routes"). Anything unusable is dropped as a set by
    `Attribution.of` and the registration proceeds unchanged.

    `object`, not `Any`, and the difference is the point: both accept whatever
    the request carried, but `Any` also switches type checking OFF downstream,
    so a caller could pass one of these straight into a `str` parameter and mypy
    would say nothing. `object` forces the narrowing that `Attribution.of`
    already performs.
    """

    email: str
    password: str
    confirm_password: str
    utm_source: object = None
    utm_medium: object = None
    utm_campaign: object = None
    utm_content: object = None
    utm_term: object = None

    def campaign_parameters(self) -> dict[str, object]:
        return {
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_content": self.utm_content,
            "utm_term": self.utm_term,
        }
