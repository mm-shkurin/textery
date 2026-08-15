"""`GET` and `PATCH /api/v1/auth/me`: the body shape and the presence rule."""

import pytest
from httpx import ASGITransport, AsyncClient
from profile_router_fixtures import (
    AVATAR_UPDATED_AT,
    EMAIL,
    OWNER_ID,
    RecordingUsecase,
    an_account,
    build_app,
)

from shared.exceptions import ValidationException

PATH = "/api/v1/auth/me"


async def _call(method: str, app, **kwargs):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await getattr(client, method)(PATH, **kwargs)


class TestReadingTheProfile:
    async def test_should_answer_with_the_declared_fields_and_no_others(self):
        read = RecordingUsecase(an_account(name="Ada", avatar_updated_at=AVATAR_UPDATED_AT))

        response = await _call("get", build_app(get_profile=read))

        assert response.status_code == 200
        assert set(response.json()) == {
            "email",
            "name",
            "created_at",
            "avatar_updated_at",
            "has_password",
        }

    async def test_should_never_put_the_password_hash_on_the_wire(self):
        read = RecordingUsecase(an_account())

        response = await _call("get", build_app(get_profile=read))

        assert "password_hash" not in response.text
        assert "hashed::" not in response.text

    async def test_should_emit_a_null_name_rather_than_omitting_the_key(self):
        # The header chooses its email fallback on this key; a client that has to
        # tell "absent" from "null" is a client the contract failed to describe.
        read = RecordingUsecase(an_account(name=None))

        response = await _call("get", build_app(get_profile=read))

        assert response.json()["name"] is None

    async def test_should_emit_a_null_avatar_timestamp_rather_than_omitting_the_key(self):
        read = RecordingUsecase(an_account(avatar_updated_at=None))

        response = await _call("get", build_app(get_profile=read))

        assert response.json()["avatar_updated_at"] is None

    async def test_should_report_which_confirmation_the_deletion_route_will_accept(self):
        # Without this key the client falls back to the address form for everyone,
        # and every password account is refused on a form with no alternative on
        # screen -- deletion becomes impossible for them.
        with_password = RecordingUsecase(an_account())
        oauth_only = RecordingUsecase(an_account(password_hash=""))

        answers = [
            (await _call("get", build_app(get_profile=with_password))).json()["has_password"],
            (await _call("get", build_app(get_profile=oauth_only))).json()["has_password"],
        ]

        assert answers == [True, False]

    async def test_should_resolve_the_account_from_the_token_subject(self):
        read = RecordingUsecase(an_account())

        await _call("get", build_app(get_profile=read))

        assert read.last_call == {"account_id": OWNER_ID}

    async def test_should_emit_the_timestamps_with_an_offset(self):
        read = RecordingUsecase(an_account(avatar_updated_at=AVATAR_UPDATED_AT))

        body = (await _call("get", build_app(get_profile=read))).json()

        assert body["avatar_updated_at"].endswith("Z") or "+00:00" in body["avatar_updated_at"]


class TestPatchPresenceRule:
    async def test_should_take_the_read_path_when_the_name_key_is_absent(self):
        # `{}` means "change nothing", so it must never reach an UPDATE.
        read = RecordingUsecase(an_account(name="Ada"))
        rename = RecordingUsecase(an_account(name="Ada"))

        response = await _call("patch", build_app(get_profile=read, rename_account=rename), json={})

        assert response.status_code == 200
        assert rename.calls == []
        assert read.calls == [{"account_id": OWNER_ID}]

    async def test_should_take_the_write_path_on_an_explicit_null(self):
        read = RecordingUsecase(an_account())
        rename = RecordingUsecase(an_account(name=None))

        await _call(
            "patch", build_app(get_profile=read, rename_account=rename), json={"name": None}
        )

        assert rename.last_call == {"account_id": OWNER_ID, "name": None}
        assert read.calls == []

    async def test_should_pass_an_empty_string_through_to_the_write_path(self):
        rename = RecordingUsecase(an_account(name=None))
        app = build_app(get_profile=RecordingUsecase(an_account()), rename_account=rename)

        await _call("patch", app, json={"name": ""})

        assert rename.last_call == {"account_id": OWNER_ID, "name": ""}

    @pytest.mark.parametrize("value", [123, 1.5, [], {}, True])
    async def test_should_hand_a_non_string_to_the_domain_rather_than_refusing_it_first(
        self, value
    ):
        # A `str | None` annotation would make Pydantic answer 422 in a different
        # envelope that echoes the rejected input back.
        rename = RecordingUsecase(an_account())
        app = build_app(get_profile=RecordingUsecase(an_account()), rename_account=rename)

        await _call("patch", app, json={"name": value})

        assert rename.last_call == {"account_id": OWNER_ID, "name": value}

    async def test_should_answer_the_domain_refusal_in_the_canonical_envelope(self):
        rename = RecordingUsecase(
            ValidationException(error_code="INVALID_NAME", message="The name is not valid.")
        )

        app = build_app(get_profile=RecordingUsecase(an_account()), rename_account=rename)

        response = await _call("patch", app, json={"name": "x" * 61})

        assert response.status_code == 400
        assert response.json() == {
            "error_code": "INVALID_NAME",
            "message": "The name is not valid.",
        }

    async def test_should_answer_with_the_normalized_profile_not_an_echo_of_the_request(self):
        rename = RecordingUsecase(an_account(name="Renee"))

        app = build_app(get_profile=RecordingUsecase(an_account()), rename_account=rename)

        response = await _call("patch", app, json={"name": " Renee "})

        assert response.json()["name"] == "Renee"
        assert response.json()["email"] == EMAIL
