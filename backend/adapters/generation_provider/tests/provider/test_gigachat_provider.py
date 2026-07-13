import pytest

from provider.gigachat_provider import CREDENTIALS_ENV_VAR, GigaChatProvider
from shared.exceptions import ConfigurationException


class TestMissingCredentials:
    """Constructing the provider without GIGACHAT_CREDENTIALS fails fast instead of sending 'Basic None'."""

    def test_should_raise_configuration_exception_when_credentials_unset(self, monkeypatch):
        monkeypatch.delenv(CREDENTIALS_ENV_VAR, raising=False)

        with pytest.raises(ConfigurationException):
            GigaChatProvider()

    def test_should_raise_configuration_exception_when_credentials_blank(self, monkeypatch):
        monkeypatch.setenv(CREDENTIALS_ENV_VAR, "")

        with pytest.raises(ConfigurationException):
            GigaChatProvider()


class TestPresentCredentials:
    """Constructing the provider with GIGACHAT_CREDENTIALS set succeeds."""

    def test_should_construct_when_credentials_set(self, monkeypatch):
        monkeypatch.setenv(CREDENTIALS_ENV_VAR, "dGVzdDp0ZXN0")

        provider = GigaChatProvider()

        assert provider is not None
