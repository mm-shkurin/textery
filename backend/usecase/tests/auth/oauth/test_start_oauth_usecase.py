from datetime import UTC, datetime

import pytest

from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth.start_oauth import StartOAuth
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.oauth.fake_oauth_provider import FakeOAuthProvider
from fake.auth.oauth.fake_oauth_state_repository import FakeOAuthStateRepository
from shared.exceptions import ValidationException

_NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)


def _make(provider_name: str = "yandex"):
    provider = FakeOAuthProvider(name=provider_name)
    states = FakeOAuthStateRepository()
    uow = FakeUnitOfWork()
    usecase = StartOAuth(
        provider_registry=ProviderRegistry([provider]),
        state_repository=states,
        clock=FakeClock(_NOW),
        unit_of_work=uow,
    )
    return usecase, provider, states, uow


class TestStartOAuthSuccess:
    async def test_returns_the_provider_url_carrying_the_minted_state(self):
        usecase, provider, states, _ = _make()

        url = await usecase.execute("yandex")

        minted = next(iter(states._by_value.values()))
        assert provider.authorization_url_calls == [minted.value]
        assert f"state={minted.value}" in url

    async def test_persists_exactly_one_state_bound_to_the_provider(self):
        usecase, _, states, _ = _make()

        await usecase.execute("yandex")

        assert len(states._by_value) == 1
        assert next(iter(states._by_value.values())).provider == "yandex"

    async def test_commits_the_minted_state(self):
        usecase, _, _, uow = _make()

        await usecase.execute("yandex")

        assert uow.commit_call_count == 1


class TestStartOAuthUnknownProvider:
    async def test_rejects_a_provider_with_no_configured_credentials(self):
        # `vk` is not in the registry, so it is refused by name rather than aliased
        # to the configured provider's handshake.
        usecase, _, states, _ = _make(provider_name="yandex")

        with pytest.raises(ValidationException) as caught:
            await usecase.execute("vk")

        assert caught.value.error_code == "UNKNOWN_OAUTH_PROVIDER"
        assert states._by_value == {}
