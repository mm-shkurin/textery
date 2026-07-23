from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from auth.account import Account
from auth.oauth.complete_oauth_callback import CompleteOAuthCallback
from auth.oauth.oauth_error_codes import OAuthCallbackError
from auth.oauth.oauth_provider import ProviderIdentity
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth_state import OAuthState
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.oauth.fake_handoff_code_repository import FakeHandoffCodeRepository
from fake.auth.oauth.fake_oauth_identity_repository import FakeOAuthIdentityRepository
from fake.auth.oauth.fake_oauth_provider import FakeOAuthProvider, failing_provider
from fake.auth.oauth.fake_oauth_state_repository import FakeOAuthStateRepository

_NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)
_TTL = 300
_SUBJECT = "2027708195"
_EMAIL = "user@yandex.ru"


class _Fixture:
    def __init__(self, provider: FakeOAuthProvider) -> None:
        self.provider = provider
        self.states = FakeOAuthStateRepository()
        self.identities = FakeOAuthIdentityRepository()
        self.accounts = FakeAccountRepository()
        self.handoffs = FakeHandoffCodeRepository()
        self.uow = FakeUnitOfWork()
        self.usecase = CompleteOAuthCallback(
            provider_registry=ProviderRegistry([provider]),
            state_repository=self.states,
            identity_repository=self.identities,
            account_repository=self.accounts,
            handoff_code_repository=self.handoffs,
            handoff_ttl_seconds=_TTL,
            clock=FakeClock(_NOW),
            unit_of_work=self.uow,
        )

    async def mint_state(self, provider: str = "yandex") -> str:
        state = OAuthState.generate(provider, _NOW)
        await self.states.save(state)
        return state.value


def _fixture(identity_email: str = _EMAIL) -> _Fixture:
    provider = FakeOAuthProvider(
        identity=ProviderIdentity(subject=_SUBJECT, email=identity_email)
    )
    return _Fixture(provider)


class TestCallbackFirstSignIn:
    async def test_auto_creates_one_verified_account_and_returns_a_handoff_code(self):
        f = _fixture()
        state = await f.mint_state()

        code = await f.usecase.execute("yandex", "auth-code", state)

        assert len(f.accounts.saved_accounts) == 1
        assert f.accounts.saved_accounts[0].is_verified is True
        assert f.accounts.saved_accounts[0].email == _EMAIL
        assert code and code in f.handoffs._by_value
        assert f.uow.commit_call_count == 1

    async def test_binds_the_identity_to_the_new_account(self):
        f = _fixture()
        state = await f.mint_state()

        await f.usecase.execute("yandex", "auth-code", state)

        saved = f.identities.saved
        assert len(saved) == 1
        assert saved[0].provider == "yandex" and saved[0].subject == _SUBJECT
        assert saved[0].account_id == f.accounts.saved_accounts[0].id

    async def test_normalizes_the_provider_email_before_creating_the_account(self):
        # The Email VO case-folds; a provider that shouts the address must still land
        # on the canonical row so a later sign-in resolves to one account (I6).
        f = _fixture(identity_email="USER@Yandex.RU")
        state = await f.mint_state()

        await f.usecase.execute("yandex", "auth-code", state)

        assert f.accounts.saved_accounts[0].email == "user@yandex.ru"


class TestCallbackReturningUser:
    async def test_resolves_an_existing_identity_without_creating_a_second_account(self):
        f = _fixture()
        await f.usecase.execute("yandex", "auth-code", await f.mint_state())
        first_account_id = f.accounts.saved_accounts[0].id

        code = await f.usecase.execute("yandex", "auth-code", await f.mint_state())

        assert len(f.accounts.saved_accounts) == 1
        assert len(f.identities.saved) == 1
        assert f.handoffs._by_value[code].account_id == first_account_id


class TestCallbackStateValidation:
    async def test_refuses_a_forged_or_missing_state(self):
        f = _fixture()

        with pytest.raises(OAuthCallbackError):
            await f.usecase.execute("yandex", "auth-code", "never-minted")
        assert f.handoffs._by_value == {}

    async def test_refuses_a_replayed_state(self):
        f = _fixture()
        state = await f.mint_state()
        await f.usecase.execute("yandex", "auth-code", state)

        with pytest.raises(OAuthCallbackError):
            await f.usecase.execute("yandex", "auth-code", state)

    async def test_refuses_a_state_minted_for_another_provider(self):
        f = _fixture()
        state = await f.mint_state(provider="vk")

        with pytest.raises(OAuthCallbackError):
            await f.usecase.execute("yandex", "auth-code", state)

    async def test_refuses_an_expired_state(self):
        f = _fixture()
        expired = OAuthState(
            "stale", "yandex", _NOW - timedelta(hours=1), _NOW - timedelta(minutes=1)
        )
        await f.states.save(expired)

        with pytest.raises(OAuthCallbackError):
            await f.usecase.execute("yandex", "auth-code", "stale")


class TestCallbackProviderFailure:
    async def test_refuses_when_the_provider_exchange_fails(self):
        f = _Fixture(failing_provider())
        state = await f.mint_state()

        with pytest.raises(OAuthCallbackError):
            await f.usecase.execute("yandex", "auth-code", state)
        assert f.accounts.saved_accounts == []
        assert f.handoffs._by_value == {}


class TestCallbackPasswordAccountCollision:
    async def test_does_not_link_an_oauth_email_into_a_password_account(self):
        # Invariant I8: an email already owned by a password account is a hard stop,
        # never a silent link. The existing account must be untouched and no identity
        # bound to it.
        f = _fixture()
        existing = Account.create(uuid4(), _EMAIL, password_hash="hashed", created_at=_NOW)
        await f.accounts.save(existing)
        state = await f.mint_state()

        with pytest.raises(OAuthCallbackError):
            await f.usecase.execute("yandex", "auth-code", state)

        assert len(f.accounts.saved_accounts) == 1
        assert f.accounts.saved_accounts[0] is existing
        assert f.identities.saved == []
        assert f.handoffs._by_value == {}
