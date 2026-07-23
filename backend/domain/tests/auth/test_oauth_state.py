from datetime import UTC, datetime, timedelta

from auth.oauth_state import STATE_TTL_MINUTES, OAuthState

_CREATED_AT = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)


class TestOAuthStateGenerate:
    def test_generates_a_nonempty_urlsafe_value(self):
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.value
        assert all(c.isalnum() or c in "-_" for c in state.value)

    def test_binds_the_state_to_the_minting_provider(self):
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.provider == "yandex"

    def test_expires_exactly_one_ttl_after_creation(self):
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.expires_at == _CREATED_AT + timedelta(minutes=STATE_TTL_MINUTES)

    def test_two_states_do_not_collide(self):
        first = OAuthState.generate("yandex", _CREATED_AT)
        second = OAuthState.generate("yandex", _CREATED_AT)

        assert first.value != second.value


class TestOAuthStateExpiry:
    def test_is_not_expired_before_the_boundary(self):
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.is_expired_at(state.expires_at - timedelta(seconds=1)) is False

    def test_is_expired_at_the_exact_boundary(self):
        # `>=`: the instant the TTL lapses is already expired, never redeemable.
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.is_expired_at(state.expires_at) is True


class TestOAuthStateProviderBinding:
    def test_belongs_to_its_own_provider(self):
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.belongs_to("yandex") is True

    def test_does_not_belong_to_another_provider(self):
        # A state minted for one provider must not validate a callback on another,
        # else the two handshakes are interchangeable.
        state = OAuthState.generate("yandex", _CREATED_AT)

        assert state.belongs_to("vk") is False
