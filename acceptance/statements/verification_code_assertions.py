import re
from datetime import datetime, timedelta, timezone

VERIFICATION_CODE_TTL = timedelta(minutes=10)
# Clock-skew allowance only: the valid window is already bracketed by the
# request/response timestamps captured around the HTTP call, so this only
# needs to cover drift between the test host clock and the server clock.
CODE_EXPIRY_CLOCK_SKEW_TOLERANCE = timedelta(seconds=5)


def assert_valid_verification_code(verification_code: object) -> None:
    assert isinstance(verification_code, str), (
        f"expected verification_code to be a string, got "
        f"{type(verification_code).__name__} ({verification_code!r})"
    )
    assert re.fullmatch(r"[0-9]{6}", verification_code), (
        f"expected verification_code to match ^[0-9]{{6}}$ (6-digit zero-padded string), "
        f"got {verification_code!r}"
    )


def assert_code_expiry_within_window(
    code_expires_at_raw: object, sent_at: datetime, received_at: datetime
) -> None:
    assert code_expires_at_raw is not None, (
        f"expected code_expires_at in response body, got code_expires_at={code_expires_at_raw!r}"
    )
    try:
        code_expires_at = datetime.fromisoformat(str(code_expires_at_raw).replace("Z", "+00:00"))
    except ValueError as error:
        raise AssertionError(
            f"expected code_expires_at to be an ISO-8601 timestamp, got {code_expires_at_raw!r}"
        ) from error
    if code_expires_at.tzinfo is None:
        code_expires_at = code_expires_at.replace(tzinfo=timezone.utc)
    earliest_valid_expiry = sent_at + VERIFICATION_CODE_TTL - CODE_EXPIRY_CLOCK_SKEW_TOLERANCE
    latest_valid_expiry = received_at + VERIFICATION_CODE_TTL + CODE_EXPIRY_CLOCK_SKEW_TOLERANCE
    assert earliest_valid_expiry <= code_expires_at <= latest_valid_expiry, (
        f"expected code_expires_at within [{earliest_valid_expiry.isoformat()}, "
        f"{latest_valid_expiry.isoformat()}] (issuance time +/- request latency, "
        f"{VERIFICATION_CODE_TTL} TTL, {CODE_EXPIRY_CLOCK_SKEW_TOLERANCE} clock-skew "
        f"allowance), got {code_expires_at.isoformat()}"
    )
