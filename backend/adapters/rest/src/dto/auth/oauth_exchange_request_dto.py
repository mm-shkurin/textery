from pydantic import BaseModel


class OAuthExchangeRequestDto(BaseModel):
    """The one-time handoff code the frontend trades for a session.

    Only the code — nothing a caller adds to this body can widen what the exchange
    does, which is what keeps privileged fields out of the auto-created session
    (Security 6.1). Length and validity are the usecase's business, not a schema
    constraint that would answer a different error shape.
    """

    code: str
