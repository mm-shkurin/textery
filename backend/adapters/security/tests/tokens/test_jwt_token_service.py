from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from shared.exceptions import InvalidTokenException
from tokens.jwt_token_service import MIN_SECRET_BYTES, JwtTokenService

# 32+ bytes: below that PyJWT warns the HMAC key is too short for SHA-256, and a
# suite that emits warnings trains everyone to ignore them.
_SECRET = "test-signing-secret-padded-to-32-bytes"
_OTHER_SECRET = "a-rotated-signing-secret-padded-to-32-bytes"
_ALGORITHM = "HS256"
_EMAIL = "user@example.ru"


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _service(clock=None) -> JwtTokenService:
    return JwtTokenService(secret=_SECRET, clock=clock)


def _real_now() -> datetime:
    return datetime.now(UTC)


class TestJwtTokenServiceConstruction:
    def test_should_refuse_an_empty_secret(self):
        # A default secret would ship a signing key that is public in the git
        # history, making every production token forgeable by anyone who read the
        # repo. The constructor is the only place that can prevent it.
        with pytest.raises(ValueError):
            JwtTokenService(secret="")

    def test_should_refuse_a_secret_shorter_than_the_hash_output(self):
        # 31 bytes: one short of RFC 7518 §3.2's floor for HS256. A key this size
        # is brute-forceable offline from a single captured token, and PyJWT only
        # warns. Rejecting at construction makes it a boot failure instead of a
        # silently weak deployment.
        with pytest.raises(ValueError, match="at least 32 bytes"):
            JwtTokenService(secret="a" * (MIN_SECRET_BYTES - 1))

    def test_should_accept_a_secret_at_exactly_the_minimum(self):
        # The boundary is inclusive -- exactly 32 bytes is compliant, and an
        # off-by-one here would reject a correctly generated key.
        assert JwtTokenService(secret="a" * MIN_SECRET_BYTES) is not None

    def test_should_measure_the_secret_in_bytes_not_characters(self):
        # 31 astral-plane characters are 124 UTF-8 bytes. len(str) would reject
        # this key; len(bytes) is what RFC 7518 actually specifies.
        assert JwtTokenService(secret="𝔞" * (MIN_SECRET_BYTES - 1)) is not None


class TestIssuePair:
    def test_should_issue_two_different_tokens(self):
        pair = _service().issue_pair(account_id=uuid4(), email=_EMAIL)

        assert pair.access_token != pair.refresh_token, (
            "expected the access and refresh tokens to differ -- one token used for "
            "both would give a 15-minute credential a 7-day lifetime"
        )

    def test_should_expire_the_access_token_after_fifteen_minutes(self):
        now = _real_now()

        pair = _service(clock=FixedClock(now)).issue_pair(account_id=uuid4(), email=_EMAIL)

        assert pair.access_token_expires_at == now + timedelta(minutes=15)

    def test_should_expire_the_refresh_token_after_seven_days(self):
        now = _real_now()

        pair = _service(clock=FixedClock(now)).issue_pair(account_id=uuid4(), email=_EMAIL)

        assert pair.refresh_token_expires_at == now + timedelta(days=7)

    def test_should_carry_the_account_id_and_email_in_the_access_token(self):
        account_id = uuid4()

        pair = _service().issue_pair(account_id=account_id, email=_EMAIL)

        claims = jwt.decode(pair.access_token, _SECRET, algorithms=[_ALGORITHM])
        assert (claims["sub"], claims["email"], claims["type"]) == (
            str(account_id),
            _EMAIL,
            "access",
        )

    def test_should_state_the_reported_expiry_in_the_token_itself(self):
        # The returned expires_at is what the client trusts; the exp claim is what
        # the server enforces. If they disagree, a client caches a token the
        # server already rejects (or worse, drops one that is still good).
        now = _real_now()

        pair = _service(clock=FixedClock(now)).issue_pair(account_id=uuid4(), email=_EMAIL)

        claims = jwt.decode(pair.refresh_token, _SECRET, algorithms=[_ALGORITHM])
        assert claims["exp"] == int(pair.refresh_token_expires_at.timestamp())


class TestReadRefreshSubject:
    def test_should_return_the_account_id_of_a_valid_refresh_token(self):
        account_id = uuid4()
        service = _service()
        pair = service.issue_pair(account_id=account_id, email=_EMAIL)

        assert service.read_refresh_subject(pair.refresh_token) == account_id

    def test_should_reject_an_access_token(self):
        # The access token is signed by the same key, so nothing but the type
        # claim distinguishes it. Without that check, /refresh would accept a
        # 15-minute credential and hand back a 7-day one.
        service = _service()
        pair = service.issue_pair(account_id=uuid4(), email=_EMAIL)

        with pytest.raises(InvalidTokenException):
            service.read_refresh_subject(pair.access_token)

    def test_should_reject_an_expired_refresh_token(self):
        issued_long_ago = FixedClock(_real_now() - timedelta(days=8))
        expired = _service(clock=issued_long_ago).issue_pair(account_id=uuid4(), email=_EMAIL)

        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject(expired.refresh_token)

    def test_should_reject_a_token_signed_with_another_key(self):
        # Scenario 9: after a signing-key rotation, tokens minted under the old
        # key must stop working rather than be honoured by the new deployment.
        foreign = JwtTokenService(secret=_OTHER_SECRET).issue_pair(account_id=uuid4(), email=_EMAIL)

        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject(foreign.refresh_token)

    def test_should_reject_a_tampered_token(self):
        service = _service()
        pair = service.issue_pair(account_id=uuid4(), email=_EMAIL)
        header, payload, signature = pair.refresh_token.split(".")
        forged_payload = jwt.utils.base64url_encode(
            b'{"sub":"' + str(uuid4()).encode() + b'","type":"refresh"}'
        ).decode()

        with pytest.raises(InvalidTokenException):
            service.read_refresh_subject(f"{header}.{forged_payload}.{signature}")

    def test_should_reject_a_token_that_is_not_a_jwt_at_all(self):
        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject("not-a-token")

    def test_should_reject_a_validly_signed_token_with_no_subject(self):
        # Scenario 6.4: a token whose claim shape no longer matches current code
        # is a clean rejection, never a KeyError escaping as a 500.
        shapeless = jwt.encode(
            {"type": "refresh", "exp": _real_now() + timedelta(days=1)},
            _SECRET,
            algorithm=_ALGORITHM,
        )

        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject(shapeless)

    def test_should_reject_a_validly_signed_token_whose_subject_is_not_a_uuid(self):
        malformed = jwt.encode(
            {"sub": "not-a-uuid", "type": "refresh", "exp": _real_now() + timedelta(days=1)},
            _SECRET,
            algorithm=_ALGORITHM,
        )

        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject(malformed)

    def test_should_reject_a_token_with_no_type_claim(self):
        typeless = jwt.encode(
            {"sub": str(uuid4()), "exp": _real_now() + timedelta(days=1)},
            _SECRET,
            algorithm=_ALGORITHM,
        )

        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject(typeless)

    def test_should_reject_an_unsigned_token_claiming_the_none_algorithm(self):
        # The classic JWT forgery: strip the signature, set alg to "none". PyJWT
        # refuses it only because algorithms= is passed explicitly at decode.
        unsigned = jwt.encode(
            {"sub": str(uuid4()), "type": "refresh", "exp": _real_now() + timedelta(days=1)},
            key="",
            algorithm="none",
        )

        with pytest.raises(InvalidTokenException):
            _service().read_refresh_subject(unsigned)
