from datetime import UTC, datetime, timedelta
from uuid import uuid4

from auth.handoff_code import MAX_HANDOFF_CODE_LENGTH, HandoffCode

_CREATED_AT = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)
_TTL_SECONDS = 300


def _generate() -> HandoffCode:
    return HandoffCode.generate(uuid4(), _CREATED_AT, _TTL_SECONDS)


class TestHandoffCodeGenerate:
    def test_generates_a_nonempty_urlsafe_value(self):
        code = _generate()

        assert code.value
        assert all(c.isalnum() or c in "-_" for c in code.value)

    def test_carries_the_account_it_was_minted_for(self):
        account_id = uuid4()
        code = HandoffCode.generate(account_id, _CREATED_AT, _TTL_SECONDS)

        assert code.account_id == account_id

    def test_expires_exactly_ttl_seconds_after_creation(self):
        code = _generate()

        assert code.expires_at == _CREATED_AT + timedelta(seconds=_TTL_SECONDS)

    def test_two_codes_do_not_collide(self):
        assert _generate().value != _generate().value

    def test_stays_within_the_max_lookup_length(self):
        assert len(_generate().value) <= MAX_HANDOFF_CODE_LENGTH


class TestHandoffCodeExpiry:
    def test_is_not_expired_one_second_before_the_boundary(self):
        code = _generate()

        assert code.is_expired_at(code.expires_at - timedelta(seconds=1)) is False

    def test_is_expired_at_the_exact_boundary(self):
        # `>=` not `>`: a code can never be redeemed at the instant it lapses.
        code = _generate()

        assert code.is_expired_at(code.expires_at) is True
