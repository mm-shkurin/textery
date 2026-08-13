"""The two `/api/v1/auth/me` calls, as functions over the shared httpx client.

Split out of `ApplicationClient` only because that file is at the 200-line cap;
`ApplicationClient` delegates here and remains the single entry point tests use.
"""

import httpx

from clients.application.dto.auth.profile_response_dto import ProfileResponseDto


async def get_me(client: httpx.AsyncClient, access_token: str | None) -> ProfileResponseDto:
    # `access_token=None` sends NO Authorization header at all, which is one of the
    # refusals this route owes an identical 401 to. A helper that always sent a
    # header could not express it.
    response = await client.get("/api/v1/auth/me", headers=_bearer(access_token))
    return _profile(response)


async def patch_me(
    client: httpx.AsyncClient, body: dict, access_token: str | None
) -> ProfileResponseDto:
    # `body` is passed through verbatim rather than built from typed arguments: the
    # scenarios turn on shapes a typed helper would refuse to construct -- an absent
    # key, an explicit null, a non-string, a lone NUL.
    response = await client.patch("/api/v1/auth/me", json=body, headers=_bearer(access_token))
    return _profile(response)


def _profile(response: httpx.Response) -> ProfileResponseDto:
    return ProfileResponseDto(
        status_code=response.status_code,
        body=_parsed_body(response),
        cache_control=response.headers.get("cache-control"),
    )


def _parsed_body(response: httpx.Response) -> dict | None:
    try:
        return response.json()
    except ValueError:
        return None


def _bearer(access_token: str | None) -> dict:
    return {} if access_token is None else {"Authorization": f"Bearer {access_token}"}
