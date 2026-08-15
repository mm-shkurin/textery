"""Statements for `/api/v1/auth/me/avatar` over real HTTP.

Setup goes through the public API only (register -> verify -> login), so every
assertion is one a browser could have made.
"""

from dataclasses import dataclass

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.avatar_response_dto import AvatarResponseDto
from clients.application.dto.auth.profile_response_dto import ProfileResponseDto
from statements.account_setup import authenticated_access_token
from statements.avatar_fixtures import PDF, PNG, SVG, WEBP, png, webp

UNSUPPORTED_TYPE = "AVATAR_UNSUPPORTED_TYPE"
NO_SNIFF = "nosniff"
EXPECTED_CACHE_CONTROL = "private, no-cache"


@dataclass(frozen=True)
class RemovalOutcome:
    first_delete: ProfileResponseDto
    second_delete: ProfileResponseDto
    profile: ProfileResponseDto
    avatar: AvatarResponseDto


@dataclass(frozen=True)
class RefusedUpload:
    described_as: str
    response: ProfileResponseDto
    avatar_after: AvatarResponseDto


class AvatarStatements:
    def __init__(self, client: ApplicationClient) -> None:
        self._client = client

    async def upload_then_delete_twice(self) -> RemovalOutcome:
        token = await authenticated_access_token(self._client)
        await self._client.put_avatar(webp(), WEBP, token)
        first = await self._client.delete_avatar(token)
        # The second call is the point: a client retrying after a dropped response
        # must not be told it failed.
        second = await self._client.delete_avatar(token)
        return RemovalOutcome(
            first_delete=first,
            second_delete=second,
            profile=await self._client.get_me(token),
            avatar=await self._client.get_avatar(token),
        )

    async def upload_a_document_pretending_to_be_an_image(self) -> list[RefusedUpload]:
        token = await authenticated_access_token(self._client)
        refusals = []
        for described_as, data in (("an SVG", SVG), ("a PDF", PDF)):
            # The Content-Type says image/png in both cases -- if the server
            # believed the header instead of the bytes, these would be stored and
            # later served back as images from this origin.
            response = await self._client.put_avatar(data, PNG, token)
            refusals.append(
                RefusedUpload(
                    described_as=described_as,
                    response=response,
                    avatar_after=await self._client.get_avatar(token),
                )
            )
        return refusals

    async def upload_a_png_and_fetch_it(self) -> AvatarResponseDto:
        token = await authenticated_access_token(self._client)
        # Uploaded as a PNG while the header claims WebP. The response must carry
        # the type derived from the magic bytes, so image/png is the assertion and
        # image/webp is the failure.
        await self._client.put_avatar(png(), WEBP, token)
        return await self._client.get_avatar(token)

    def assert_removal_is_idempotent_and_complete(self, outcome: RemovalOutcome) -> None:
        for described_as, response in (
            ("the first delete", outcome.first_delete),
            ("the second delete", outcome.second_delete),
        ):
            assert response.status_code == 200, (
                f"expected {described_as} to answer 200 -- removal is idempotent and a "
                f"missing avatar is not an error -- got status_code={response.status_code}, "
                f"body={response.body!r}"
            )
        assert outcome.profile.body is not None, "expected a profile body after removal"
        # avatar_updated_at back to null: the timestamp column is cleared, not left
        # pointing at the moment the image was deleted.
        assert outcome.profile.body.get("avatar_updated_at") is None, (
            f"expected the profile to report avatar_updated_at=None after removal, "
            f"got {outcome.profile.body!r}"
        )
        # And the bytes and their media type are gone too -- this route answers 404
        # only when find_avatar sees both columns NULL.
        assert outcome.avatar.status_code == 404, (
            f"expected the image to be gone (404), got status_code="
            f"{outcome.avatar.status_code}, {len(outcome.avatar.content)} bytes"
        )

    def assert_every_document_was_refused_and_nothing_stored(
        self, refusals: list[RefusedUpload]
    ) -> None:
        for refusal in refusals:
            response = refusal.response
            assert response.status_code == 400, (
                f"expected {refusal.described_as} to be refused with 400, got "
                f"status_code={response.status_code}, body={response.body!r}"
            )
            assert response.body is not None and (
                response.body.get("error_code") == UNSUPPORTED_TYPE
            ), (
                f"expected {refusal.described_as} to answer error_code={UNSUPPORTED_TYPE} "
                f"in the canonical envelope, got {response.body!r}"
            )
            # The refusal is worthless if the bytes landed anyway: an SVG stored
            # here and served back from this origin is stored XSS.
            assert refusal.avatar_after.status_code == 404, (
                f"expected nothing to be stored after {refusal.described_as} was refused, "
                f"got status_code={refusal.avatar_after.status_code} with "
                f"{len(refusal.avatar_after.content)} bytes"
            )

    def assert_the_image_is_served_safely(self, avatar: AvatarResponseDto) -> None:
        assert avatar.status_code == 200, (
            f"expected the uploaded image to be served, got status_code="
            f"{avatar.status_code}, body={avatar.body!r}"
        )
        assert avatar.x_content_type_options == NO_SNIFF, (
            f"expected X-Content-Type-Options: {NO_SNIFF} -- without it a browser may "
            f"ignore the declared type and sniff the content -- got "
            f"{avatar.x_content_type_options!r}"
        )
        # The type from the MAGIC BYTES, not the image/webp the upload declared.
        assert avatar.content_type == PNG, (
            f"expected the allowlisted type derived from the bytes ({PNG}), not the one the "
            f"client declared, got {avatar.content_type!r}"
        )
        assert avatar.cache_control == EXPECTED_CACHE_CONTROL, (
            f"expected Cache-Control: {EXPECTED_CACHE_CONTROL} -- the image is one "
            f"account's and must not be reused by a shared cache -- got "
            f"{avatar.cache_control!r}"
        )
