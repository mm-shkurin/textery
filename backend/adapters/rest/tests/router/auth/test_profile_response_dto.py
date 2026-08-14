"""`ProfileResponseDto`: the timezone guard, asserted where it can actually fire."""

from datetime import datetime

import pytest
from profile_router_fixtures import CREATED_AT, EMAIL, OWNER_ID

from auth.account import Account
from dto.auth.profile_response_dto import ProfileResponseDto


def _account(created_at: datetime, avatar_updated_at: datetime | None = None) -> Account:
    return Account.reconstitute(
        id=OWNER_ID,
        email=EMAIL,
        password_hash="",
        created_at=created_at,
        is_verified=True,
        avatar_updated_at=avatar_updated_at,
    )


class TestTheTimezoneGuard:
    def test_should_refuse_a_naive_created_at_rather_than_read_it_as_local_time(self):
        # `astimezone(UTC)` does not raise on a naive datetime -- it reads it as the
        # HOST's zone. That turns a visible violation into an invisible one: a
        # well-formed `Z` naming the wrong instant, right in a UTC container and
        # silently shifted on a developer machine.
        with pytest.raises(ValueError, match="created_at must be timezone-aware"):
            ProfileResponseDto.from_domain(_account(created_at=datetime(2026, 7, 1, 9, 30)))

    def test_should_refuse_a_naive_avatar_timestamp(self):
        with pytest.raises(ValueError, match="avatar_updated_at must be timezone-aware"):
            ProfileResponseDto.from_domain(
                _account(created_at=CREATED_AT, avatar_updated_at=datetime(2026, 8, 14, 12, 0))
            )

    def test_should_let_an_absent_avatar_timestamp_through_untouched(self):
        # None is the absent avatar, not a violation: only a present instant has a
        # zone to be wrong about.
        dto = ProfileResponseDto.from_domain(_account(created_at=CREATED_AT))

        assert dto.avatar_updated_at is None
