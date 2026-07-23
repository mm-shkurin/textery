import pytest

from auth.oauth.provider_registry import ProviderRegistry
from fake.auth.oauth.fake_oauth_provider import FakeOAuthProvider
from shared.exceptions import ValidationException


class TestProviderRegistry:
    def test_resolves_a_configured_provider_by_its_slug(self):
        yandex = FakeOAuthProvider(name="yandex")
        registry = ProviderRegistry([yandex])

        assert registry.get("yandex") is yandex

    def test_refuses_an_unconfigured_provider_by_name(self):
        registry = ProviderRegistry([FakeOAuthProvider(name="yandex")])

        with pytest.raises(ValidationException) as caught:
            registry.get("vk")

        assert caught.value.error_code == "UNKNOWN_OAUTH_PROVIDER"

    def test_keys_each_provider_by_its_own_name(self):
        yandex = FakeOAuthProvider(name="yandex")
        vk = FakeOAuthProvider(name="vk")
        registry = ProviderRegistry([yandex, vk])

        assert registry.get("yandex") is yandex
        assert registry.get("vk") is vk
