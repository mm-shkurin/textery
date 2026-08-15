"""The `/api/v1/auth/me` calls, as a base class `ApplicationClient` inherits.

A base class rather than six more methods on `ApplicationClient`: that file is at
the 200-line cap, and this group grows with every profile endpoint. Tests still
call `client.get_me(...)` — the entry point is unchanged.

Each method is one line over `profile_api`, which owns the paths, the headers and
the response parsing.
"""

import httpx

from clients.application import profile_api
from clients.application.dto.auth.avatar_response_dto import AvatarResponseDto
from clients.application.dto.auth.deletion_response_dto import DeletionResponseDto
from clients.application.dto.auth.profile_response_dto import ProfileResponseDto


class ProfileApiClient:
    # Set by ApplicationClient.__init__; declared here so this class states what
    # it needs rather than relying on the subclass by accident.
    _client: httpx.AsyncClient

    async def get_me(self, access_token: str | None) -> ProfileResponseDto:
        return await profile_api.get_me(self._client, access_token)

    async def patch_me(self, body: dict, access_token: str | None) -> ProfileResponseDto:
        return await profile_api.patch_me(self._client, body, access_token)

    async def put_avatar(
        self, data: bytes, content_type: str, access_token: str | None
    ) -> ProfileResponseDto:
        return await profile_api.put_avatar(self._client, data, content_type, access_token)

    async def delete_avatar(self, access_token: str | None) -> ProfileResponseDto:
        return await profile_api.delete_avatar(self._client, access_token)

    async def get_avatar(self, access_token: str | None) -> AvatarResponseDto:
        return await profile_api.get_avatar(self._client, access_token)

    async def delete_account(self, body: dict, access_token: str | None) -> DeletionResponseDto:
        return await profile_api.delete_account(self._client, body, access_token)
