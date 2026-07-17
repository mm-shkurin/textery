from uuid import uuid4

import pytest

from shared.exceptions import InvalidTokenException
from tokens.jwt_token_service import JwtTokenService

# At least 32 bytes: JwtTokenService enforces RFC 7518 §3.2 for HS256.
SECRET = "test-signing-secret-padded-to-32-bytes"


class TestReadAccessSubject:
    """Story 5 needs the owner id from an access token; nothing could read one.

    `read_refresh_subject` deliberately rejects access tokens, so /documents had no
    way to identify a caller. This is its access-side twin.
    """

    def test_should_return_the_account_id_from_a_valid_access_token(self):
        service = JwtTokenService(secret=SECRET)
        account_id = uuid4()
        pair = service.issue_pair(account_id=account_id, email="user@example.com")

        assert service.read_access_subject(pair.access_token) == account_id, (
            "the access token's sub claim must round-trip to the issuing account's id"
        )

    def test_should_reject_a_refresh_token_presented_as_an_access_token(self):
        # The load-bearing case. Both tokens are signed by the same key, so without a
        # type-claim guard a 7-day refresh token silently becomes a document
        # credential -- the same bug read_refresh_subject's own guard exists to
        # prevent, in the opposite direction.
        service = JwtTokenService(secret=SECRET)
        pair = service.issue_pair(account_id=uuid4(), email="user@example.com")

        with pytest.raises(InvalidTokenException):
            service.read_access_subject(pair.refresh_token)

    def test_should_reject_a_token_signed_with_a_different_key(self):
        issued_elsewhere = JwtTokenService(secret="another-signing-secret-padded-to-32-bytes").issue_pair(
            account_id=uuid4(), email="user@example.com"
        )

        with pytest.raises(InvalidTokenException):
            JwtTokenService(secret=SECRET).read_access_subject(issued_elsewhere.access_token)

    @pytest.mark.parametrize(
        "token",
        ["", "garbage", "a.b.c"],
        ids=["empty", "not-a-jwt", "three-segments-of-junk"],
    )
    def test_should_reject_a_malformed_token(self, token):
        with pytest.raises(InvalidTokenException):
            JwtTokenService(secret=SECRET).read_access_subject(token)
