"""`/api/v1/auth/me/avatar`: raw bytes in, proven bytes out.

The client's `Content-Type` is the thing this file is really about. It reaches
the route on every upload and must reach nothing else -- what the image IS gets
decided from its magic bytes, and that decision is what the GET later answers
with. A route that forwarded the header would let an uploader choose the type its
own bytes are served back under.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from profile_router_fixtures import (
    AVATAR_UPDATED_AT,
    OWNER_ID,
    RecordingUsecase,
    a_stored_avatar,
    an_account,
    build_app,
)

from auth.avatar import AVATAR_TOO_LARGE_CODE, MAX_AVATAR_BYTES
from auth.avatar_format import JPEG, PNG
from dto.auth.avatar_response import CACHE_CONTROL, FALLBACK_MEDIA_TYPE, NO_SNIFF
from shared.exceptions import NotFoundException, ValidationException
from statements.image_bytes import jpeg, png

PATH = "/api/v1/auth/me/avatar"


async def _call(method: str, app, **kwargs):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await getattr(client, method)(PATH, **kwargs)


class TestUploading:
    async def test_should_hand_the_body_to_the_usecase_byte_for_byte(self):
        upload = RecordingUsecase(an_account(avatar_updated_at=AVATAR_UPDATED_AT))
        data = png(64, 64)

        await _call("put", build_app(update_avatar=upload), content=data)

        assert upload.last_call == {"account_id": OWNER_ID, "data": data}

    @pytest.mark.parametrize(
        "declared_type", ["image/png", "image/svg+xml", "text/plain", "application/octet-stream"]
    )
    async def test_should_ignore_whatever_type_the_client_declared(self, declared_type: str):
        # JPEG bytes under four different declared types. The route forwards the
        # bytes and nothing else, so the type the domain reads out of them is the
        # same in all four cases.
        upload = RecordingUsecase(an_account(avatar_updated_at=AVATAR_UPDATED_AT))
        data = jpeg(64, 64)

        await _call(
            "put",
            build_app(update_avatar=upload),
            content=data,
            headers={"content-type": declared_type},
        )

        assert upload.last_call == {"account_id": OWNER_ID, "data": data}

    async def test_should_answer_with_the_whole_profile(self):
        upload = RecordingUsecase(an_account(name="Ada", avatar_updated_at=AVATAR_UPDATED_AT))

        response = await _call("put", build_app(update_avatar=upload), content=png())

        assert response.status_code == 200
        assert response.json()["avatar_updated_at"] is not None
        assert response.json()["name"] == "Ada"

    async def test_should_refuse_an_oversized_upload_on_its_declared_length(self):
        # Refused before the process buffers the body, and under the same code the
        # domain's own length check uses: to the client it is one refusal.
        upload = RecordingUsecase(an_account())

        response = await _call(
            "put",
            build_app(update_avatar=upload),
            content=b"\x00" * (MAX_AVATAR_BYTES + 1),
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == AVATAR_TOO_LARGE_CODE
        assert upload.calls == []

    async def test_should_still_read_a_body_whose_declared_length_is_within_the_cap(self):
        upload = RecordingUsecase(an_account(avatar_updated_at=AVATAR_UPDATED_AT))

        response = await _call("put", build_app(update_avatar=upload), content=png())

        assert response.status_code == 200

    async def test_should_answer_a_domain_refusal_in_the_canonical_envelope(self):
        upload = RecordingUsecase(
            ValidationException(
                error_code="AVATAR_UNSUPPORTED_TYPE", message="The image format is not supported."
            )
        )

        response = await _call("put", build_app(update_avatar=upload), content=b"<svg/>")

        assert response.status_code == 400
        assert response.json()["error_code"] == "AVATAR_UNSUPPORTED_TYPE"


class TestServing:
    async def test_should_serve_the_bytes_under_the_stored_type(self):
        data = jpeg(64, 64)
        serve = RecordingUsecase(a_stored_avatar(data, JPEG))

        response = await _call("get", build_app(get_avatar=serve))

        assert response.status_code == 200
        assert response.content == data
        assert response.headers["content-type"] == JPEG

    async def test_should_forbid_the_browser_from_sniffing_the_content(self):
        serve = RecordingUsecase(a_stored_avatar(png(), PNG))

        response = await _call("get", build_app(get_avatar=serve))

        assert response.headers["x-content-type-options"] == NO_SNIFF

    async def test_should_keep_the_image_out_of_shared_caches(self):
        serve = RecordingUsecase(a_stored_avatar(png(), PNG))

        response = await _call("get", build_app(get_avatar=serve))

        assert response.headers["cache-control"] == CACHE_CONTROL

    async def test_should_carry_an_etag_derived_from_the_update_instant(self):
        serve = RecordingUsecase(a_stored_avatar(png(), PNG))
        expected = int(AVATAR_UPDATED_AT.timestamp() * 1_000_000)

        response = await _call("get", build_app(get_avatar=serve))

        assert response.headers["etag"] == f'"{expected}"'

    async def test_should_omit_the_etag_rather_than_emit_a_constant_one(self):
        # A stable ETag over changing bytes is worse than none at all.
        serve = RecordingUsecase(a_stored_avatar(png(), PNG, updated_at=None))

        response = await _call("get", build_app(get_avatar=serve))

        assert "etag" not in response.headers

    async def test_should_serve_a_type_it_no_longer_recognises_as_an_opaque_download(self):
        # A row written by an older build, or a restored dump, must not get to
        # choose the Content-Type this origin answers with.
        serve = RecordingUsecase(a_stored_avatar(b"<svg/>", "image/svg+xml"))

        response = await _call("get", build_app(get_avatar=serve))

        assert response.headers["content-type"] == FALLBACK_MEDIA_TYPE

    async def test_should_answer_not_found_when_there_is_no_avatar(self):
        serve = RecordingUsecase(NotFoundException("no avatar"))

        response = await _call("get", build_app(get_avatar=serve))

        assert response.status_code == 404


class TestRemoving:
    async def test_should_answer_with_the_profile_reporting_no_avatar(self):
        remove = RecordingUsecase(an_account(name="Ada"))

        response = await _call("delete", build_app(delete_avatar=remove))

        assert response.status_code == 200
        assert response.json()["avatar_updated_at"] is None
        assert remove.last_call == {"account_id": OWNER_ID}

    async def test_should_succeed_a_second_time(self):
        remove = RecordingUsecase(an_account())
        app = build_app(delete_avatar=remove)

        first = await _call("delete", app)
        second = await _call("delete", app)

        assert (first.status_code, second.status_code) == (200, 200)
