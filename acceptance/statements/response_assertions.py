from datetime import datetime
from typing import Protocol
from uuid import UUID

from statements.verification_code_assertions import (
    assert_code_expiry_within_window,
    assert_valid_verification_code,
)

SECRET_RESPONSE_FIELDS = ("password", "confirm_password", "password_hash")


class HasStatusAndBody(Protocol):
    status_code: int
    body: dict | None


def assert_validation_error(response: HasStatusAndBody, expected_error: dict) -> None:
    assert response.status_code == 400, (
        f"expected 400 Bad Request (validation error), got status_code={response.status_code}, "
        f"body={response.body}"
    )
    assert response.body == expected_error, (
        f"expected validation error body {expected_error}, got {response.body}"
    )


def assert_no_account_created(response: HasStatusAndBody) -> None:
    assert response.status_code not in (200, 201), (
        f"expected no account to be created (2xx would indicate creation), "
        f"got status_code={response.status_code}"
    )
    assert response.body is not None, (
        "expected an error body proving no account was created, got body=None"
    )
    assert "user_id" not in response.body, (
        f"expected no user_id in response, but got body={response.body}"
    )


def assert_duplicate_rejected(response: HasStatusAndBody, expected_error: dict) -> None:
    assert response.status_code == 409, (
        f"expected 409 Conflict (duplicate email), got status_code={response.status_code}, "
        f"body={response.body}"
    )
    assert response.body == expected_error, (
        f"expected duplicate error body {expected_error}, got {response.body}"
    )
    assert_no_account_created(response)


def assert_is_valid_uuid(value: object, field_name: str) -> None:
    try:
        UUID(str(value))
    except (ValueError, AttributeError, TypeError) as error:
        raise AssertionError(f"expected {field_name} to be a valid UUID, got {value!r}") from error


def assert_created_pending_account(response: HasStatusAndBody) -> dict:
    assert response.status_code == 201, (
        f"expected 201 Created, got status_code={response.status_code}, body={response.body}"
    )
    assert response.body is not None, (
        "expected a response body for the created account, got body=None"
    )
    is_verified = response.body.get("is_verified")
    assert is_verified is False, (
        f"expected newly created account is_verified=False, got is_verified={is_verified!r}"
    )
    leaked = [field for field in SECRET_RESPONSE_FIELDS if field in response.body]
    assert not leaked, (
        f"expected none of {SECRET_RESPONSE_FIELDS} in the response body, "
        f"found {leaked} (body={response.body})"
    )
    return response.body


def assert_server_owned_fields_ignored(response: HasStatusAndBody, attacker_supplied_id: str) -> None:
    body = assert_created_pending_account(response)
    account_id = body.get("user_id")
    assert account_id is not None, (
        f"expected a server-generated user_id, got user_id=None (body={body})"
    )
    assert_is_valid_uuid(account_id, field_name="user_id")
    assert account_id != attacker_supplied_id, (
        f"expected a server-generated user_id, not the attacker-supplied id "
        f"{attacker_supplied_id!r}, got user_id={account_id!r}"
    )


def assert_pending_account_created_with_verification_code(
    response: HasStatusAndBody, request_window: tuple[datetime, datetime]
) -> None:
    body = assert_created_pending_account(response)
    assert_valid_verification_code(body.get("verification_code"))
    sent_at, received_at = request_window
    assert_code_expiry_within_window(body.get("code_expires_at"), sent_at, received_at)


def assert_account_verified(response: HasStatusAndBody) -> None:
    assert response.status_code == 200, (
        f"expected 200 OK, got status_code={response.status_code}, body={response.body}"
    )
    assert response.body == {"is_verified": True}, (
        f"expected body {{'is_verified': True}}, got body={response.body}"
    )
