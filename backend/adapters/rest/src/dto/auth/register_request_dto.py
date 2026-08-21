from typing import Any

from pydantic import BaseModel


class RegisterRequestDto(BaseModel):
    """The registration body, EXTENDED by Story 14 and not modified.

    The five `utm_*` are optional and typed `Any` rather than `str | None`. A
    strict annotation would make an over-long or non-string campaign parameter a
    **422 on registration** -- a new way for account creation to fail, invented
    by a marketing attribute, on the most sensitive route in the product. The
    governing decision of Story 14 forbids exactly that: attribution decides what
    is STORED, never what is ANSWERED (`endpoints.md`, "Attribution is fail-open
    on both auth routes"). Anything unusable is dropped as a set by
    `Attribution.of` and the registration proceeds unchanged.
    """

    email: str
    password: str
    confirm_password: str
    utm_source: Any = None
    utm_medium: Any = None
    utm_campaign: Any = None
    utm_content: Any = None
    utm_term: Any = None

    def campaign_parameters(self) -> dict[str, Any]:
        return {
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_content": self.utm_content,
            "utm_term": self.utm_term,
        }
