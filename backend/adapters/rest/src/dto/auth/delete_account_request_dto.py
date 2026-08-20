from pydantic import BaseModel


class DeleteAccountRequestDto(BaseModel):
    """The confirmation body for `POST /api/v1/auth/me/deletion`.

    Exactly one of the two fields is meaningful, and WHICH one is decided by the
    account, not by this model: an account with a password is confirmed by
    password, an OAuth-only account by retyping its address. So this DTO
    deliberately validates neither exclusivity nor presence -- sending both, or
    neither, is simply a confirmation that does not match, answered with the one
    refusal this endpoint has. A schema that rejected those shapes itself would
    answer in FastAPI's 422 envelope instead, and would also tell the caller which
    field the server cares about for their account.

    Both fields are typed `object` for the reason the profile DTO's `name` is: a
    `str | None` annotation makes Pydantic refuse `{"password": 123}` first, and
    FastAPI renders that as a 422 in a different envelope THAT ECHOES THE REJECTED
    INPUT BACK -- here, a field that carries a password.

    Neither value is ever logged, and neither appears in any response.
    """

    password: object = None
    confirm_email: object = None
