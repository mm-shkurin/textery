"""`POST /api/v1/auth/me/deletion`: the confirmation body, and what happens without one."""

import pytest
from httpx import ASGITransport, AsyncClient
from profile_router_fixtures import OWNER_ID, RecordingUsecase, build_app

from auth.deletion_confirmation import (
    DELETION_CONFIRMATION_INVALID_CODE,
    DELETION_CONFIRMATION_INVALID_MESSAGE,
)
from shared.exceptions import ValidationException

PATH = "/api/v1/auth/me/deletion"


async def _post(app, **kwargs):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(PATH, **kwargs)


class TestTheConfirmationReachesTheUsecase:
    async def test_should_answer_204_with_no_body_on_a_matching_confirmation(self):
        delete = RecordingUsecase()

        response = await _post(build_app(delete_account=delete), json={"password": "Str0ng!Pass"})

        assert response.status_code == 204
        assert response.content == b""

    async def test_should_forward_the_password_form(self):
        delete = RecordingUsecase()

        await _post(build_app(delete_account=delete), json={"password": "Str0ng!Pass"})

        assert delete.last_call == {
            "account_id": OWNER_ID,
            "password": "Str0ng!Pass",
            "confirm_email": None,
        }

    async def test_should_forward_the_address_form(self):
        delete = RecordingUsecase()

        await _post(build_app(delete_account=delete), json={"confirm_email": "ada@example.ru"})

        assert delete.last_call == {
            "account_id": OWNER_ID,
            "password": None,
            "confirm_email": "ada@example.ru",
        }

    async def test_should_forward_both_fields_rather_than_refusing_the_shape_itself(self):
        # Validating exclusivity here would answer in FastAPI's 422 envelope AND
        # tell the caller which field the server cares about for their account.
        delete = RecordingUsecase()

        await _post(
            build_app(delete_account=delete),
            json={"password": "Str0ng!Pass", "confirm_email": "ada@example.ru"},
        )

        assert delete.last_call["password"] == "Str0ng!Pass"
        assert delete.last_call["confirm_email"] == "ada@example.ru"

    @pytest.mark.parametrize("value", [123, [], {}, True])
    async def test_should_hand_a_non_string_confirmation_to_the_domain(self, value):
        # A `str | None` annotation would make FastAPI answer 422 in an envelope
        # that echoes the rejected input back -- here, a field carrying a password.
        delete = RecordingUsecase()

        await _post(build_app(delete_account=delete), json={"password": value})

        assert delete.last_call["password"] == value


class TestARequestWithNoBody:
    async def test_should_take_the_same_refusal_path_as_a_wrong_password(self):
        # A body dropped by a proxy must not become a 422 in a different shape.
        delete = RecordingUsecase()

        await _post(build_app(delete_account=delete))

        assert delete.last_call == {
            "account_id": OWNER_ID,
            "password": None,
            "confirm_email": None,
        }

    async def test_should_treat_an_empty_json_object_the_same_way(self):
        delete = RecordingUsecase()

        await _post(build_app(delete_account=delete), json={})

        assert delete.last_call["password"] is None


class TestTheRefusal:
    async def test_should_answer_400_in_the_canonical_envelope(self):
        # Deliberately not a 401: the session is valid and the caller is who they
        # say they are. A 401 would tell a client whose token is fine to renew it.
        delete = RecordingUsecase(
            ValidationException(
                error_code=DELETION_CONFIRMATION_INVALID_CODE,
                message=DELETION_CONFIRMATION_INVALID_MESSAGE,
            )
        )

        response = await _post(build_app(delete_account=delete), json={"password": "wrong"})

        assert response.status_code == 400
        assert response.json() == {
            "error_code": DELETION_CONFIRMATION_INVALID_CODE,
            "message": DELETION_CONFIRMATION_INVALID_MESSAGE,
        }

    async def test_should_not_echo_the_submitted_password_back(self):
        delete = RecordingUsecase(
            ValidationException(
                error_code=DELETION_CONFIRMATION_INVALID_CODE,
                message=DELETION_CONFIRMATION_INVALID_MESSAGE,
            )
        )

        response = await _post(build_app(delete_account=delete), json={"password": "Hunter2!x"})

        assert "Hunter2!x" not in response.text
