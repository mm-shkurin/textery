from typing import Protocol


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
