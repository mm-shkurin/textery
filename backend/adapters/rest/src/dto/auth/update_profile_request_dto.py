from pydantic import BaseModel

NAME_FIELD = "name"


class UpdateProfileRequestDto(BaseModel):
    """The `PATCH /api/v1/auth/me` body: `name`, and only `name`.

    Its own DTO rather than a reuse of the response shape, because the two are not
    the same object: the response carries `email` and `created_at`, neither of
    which a client may write, and a shared model would make them look writable.

    **The field is typed `object` on purpose.** `{"name": 123}` must answer
    `400 {error_code, message}` from the domain. A `str | None` annotation would
    make Pydantic refuse it first, and FastAPI renders that as a **422 in a
    different envelope which echoes the rejected input back** -- a shape this
    contract does not own and a body that reflects unvalidated client data. Typing
    it loosely is what lets the value reach `AccountName`, which refuses it in the
    canonical envelope. The same applies to an over-length name.

    **Presence is carried, not collapsed.** Three distinct requests:

    - `{}`               -- key absent: the name is NOT touched (fail closed)
    - `{"name": null}`   -- clear it
    - `{"name": ""}`     -- clear it, identically to null

    A default of `None` alone cannot express that: absent and explicit-null would
    both arrive as `None` and the route would have to guess, which is how `{}`
    becomes a destructive request. Pydantic records which keys the payload
    actually carried in `model_fields_set`, and `has_name()` below reads it.

    This reads like over-engineering while `name` is the only writable field. It
    stops reading that way the moment story 8 or 14 adds a second one: retrofitting
    presence after clients are already sending `{}` means auditing every one of
    them, and until that audit is done every partial update silently erases the
    field it did not mention.
    """

    name: object = None

    def has_name(self) -> bool:
        return NAME_FIELD in self.model_fields_set
