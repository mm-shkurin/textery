from typing import Protocol
from uuid import UUID


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
