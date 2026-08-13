"""Statements for `/api/v1/auth/me` — the four claims asserted over real HTTP.

Setup goes through the public API only (register → verify → login), never the
database, so every assertion here is one a browser could have made.
"""

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.profile_response_dto import ProfileResponseDto
from statements.account_setup import authenticated_access_token

# 60 code points, 120 UTF-16 units, 240 UTF-8 bytes. The three numbers differ on
# purpose: a bound implemented in bytes or in UTF-16 units refuses this name, and
# only a bound in code points accepts it.
SIXTY_EMOJI = "\U0001f600" * 60

# U+0000. Under both length bounds and invisible to any "has visible characters"
# filter, so a predicate borrowed from the topic rules lets it through -- and
# Postgres's `text` type then refuses it from the driver, turning a documented 400
# into a 500.
LONE_NUL = "\x00"

INVALID_NAME = "INVALID_NAME"
UNAUTHORIZED_STATUS = 401
FORGED_TOKEN = "not.a.real.token"


class ProfileStatements:
    def __init__(self, client: ApplicationClient) -> None:
        self._client = client

    async def given_an_authenticated_account(self) -> str:
        return await authenticated_access_token(self._client)

    async def set_name_then_clear_it(self) -> tuple[ProfileResponseDto, ProfileResponseDto]:
        token = await self.given_an_authenticated_account()
        await self._client.patch_me({"name": "Иван"}, token)
        # The empty string, not null: the two are specified to be indistinguishable,
        # and "" is the one a form submits when the user deletes what they typed.
        cleared = await self._client.patch_me({"name": ""}, token)
        return cleared, await self._client.get_me(token)

    async def store_a_sixty_emoji_name(self) -> tuple[ProfileResponseDto, ProfileResponseDto]:
        token = await self.given_an_authenticated_account()
        stored = await self._client.patch_me({"name": SIXTY_EMOJI}, token)
        return stored, await self._client.get_me(token)

    async def call_both_routes_without_a_valid_token(self) -> list[ProfileResponseDto]:
        # Two distinct refusals per route: no header at all, and a token that is not
        # a token. Both must answer identically -- distinguishing them tells a caller
        # which half of the header they got right.
        return [
            await self._client.get_me(None),
            await self._client.get_me(FORGED_TOKEN),
            await self._client.patch_me({"name": "Иван"}, None),
            await self._client.patch_me({"name": "Иван"}, FORGED_TOKEN),
        ]

    async def submit_a_name_of_one_nul(self) -> ProfileResponseDto:
        token = await self.given_an_authenticated_account()
        return await self._client.patch_me({"name": LONE_NUL}, token)

    def assert_the_name_was_cleared(
        self, cleared: ProfileResponseDto, reread: ProfileResponseDto
    ) -> None:
        self._assert_ok(cleared, "clearing the name")
        self._assert_ok(reread, "re-reading the profile")
        # `is None` and not falsiness: `""` is also falsy, and storing `""` instead
        # of NULL is exactly the bug the null here rules out.
        assert cleared.body["name"] is None, (
            f"expected the clearing PATCH to answer name=None, got {cleared.body!r}"
        )
        # The key must be PRESENT and null, never omitted: the header decides
        # between the display name and its email fallback on this key.
        assert "name" in reread.body and reread.body["name"] is None, (
            f"expected the re-read profile to carry name=None, got {reread.body!r}"
        )

    def assert_the_emoji_name_round_tripped(
        self, stored: ProfileResponseDto, reread: ProfileResponseDto
    ) -> None:
        self._assert_ok(stored, "storing a 60-code-point name")
        self._assert_ok(reread, "re-reading the profile")
        assert stored.body["name"] == SIXTY_EMOJI, (
            f"expected PATCH to answer the stored 60-code-point name, got {stored.body!r}"
        )
        assert reread.body["name"] == SIXTY_EMOJI, (
            f"expected GET to return the same 60-code-point name byte for byte, "
            f"got {reread.body!r}"
        )

    def assert_every_call_was_refused_identically(
        self, responses: list[ProfileResponseDto]
    ) -> None:
        actual = [(response.status_code, response.body) for response in responses]
        expected = [(UNAUTHORIZED_STATUS, actual[0][1])] * len(actual)
        assert all(status == UNAUTHORIZED_STATUS for status, _ in actual), (
            f"expected 401 from both routes for every invalid credential, got {actual!r}"
        )
        # One body for all four, so a caller cannot tell a missing header from a
        # forged token, or GET from PATCH.
        assert actual == expected, (
            f"expected one identical refusal from all four calls, got {actual!r}"
        )
        assert actual[0][1] is not None and "error_code" in actual[0][1], (
            f"expected the canonical {{error_code, message}} envelope, got {actual[0][1]!r}"
        )

    def assert_the_nul_name_was_refused_in_the_canonical_envelope(
        self, response: ProfileResponseDto
    ) -> None:
        # The status is asserted before the code, because the failure this test
        # exists for is a 500 from the Postgres driver, and reporting it as
        # "error_code missing" would name the wrong cause.
        assert response.status_code == 400, (
            f"expected 400 for a name of one NUL, got status_code={response.status_code}, "
            f"body={response.body!r}. A 500 here means the value reached the `text` "
            "column instead of being refused by AccountName."
        )
        assert response.body is not None and response.body.get("error_code") == INVALID_NAME, (
            f"expected the canonical {{error_code: {INVALID_NAME}, message}} envelope, "
            f"got {response.body!r}"
        )
        assert "message" in response.body, (
            f"expected the envelope to carry a message, got {response.body!r}"
        )

    @staticmethod
    def _assert_ok(response: ProfileResponseDto, described_as: str) -> None:
        assert response.status_code == 200 and response.body is not None, (
            f"expected 200 with a body from {described_as}, got "
            f"status_code={response.status_code}, body={response.body!r}"
        )
