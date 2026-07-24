import os

from oauth_providers.fake_oauth_provider import FakeOAuthProvider
from oauth_providers.yandex_oauth_provider import YandexOAuthProvider
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.handoff_code_storage import SqlAlchemyHandoffCodeRepository
from access.auth.oauth_identity_storage import SqlAlchemyOAuthIdentityRepository
from access.auth.oauth_rate_limit_storage import SqlAlchemyRateLimiter
from access.auth.oauth_state_storage import SqlAlchemyOAuthStateRepository
from auth.oauth.complete_oauth_callback import CompleteOAuthCallback
from auth.oauth.exchange_handoff_code import ExchangeHandoffCode
from auth.oauth.oauth_provider import OAuthConfigurationError
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth.rate_limiter import OAuthRateGuard
from auth.oauth.start_oauth import StartOAuth
from container.runtime import request_scoped, token_service
from session import SqlAlchemyUnitOfWork
from shared.clock import SystemClock

OAUTH_PROVIDER_ENV_VAR = "OAUTH_PROVIDER"
HANDOFF_TTL_ENV_VAR = "OAUTH_HANDOFF_CODE_TTL_SECONDS"
FRONTEND_CALLBACK_URL_ENV_VAR = "OAUTH_FRONTEND_CALLBACK_URL"
RATE_LIMIT_MAX_ENV_VAR = "OAUTH_RATE_LIMIT_MAX_REQUESTS"
RATE_LIMIT_WINDOW_ENV_VAR = "OAUTH_RATE_LIMIT_WINDOW_SECONDS"
DEFAULT_HANDOFF_TTL_SECONDS = 300
DEFAULT_FRONTEND_CALLBACK_URL = "http://localhost/auth/callback"
DEFAULT_FAKE_AUTHORIZE_URL = "https://fake-oauth.local/authorize"
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 40
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


def _require(var_name: str) -> str:
    # Fail-fast at import, exactly like DATABASE_URL and JWT_SECRET: Yandex is the
    # provider this image ships, so a blank credential is a boot failure that names
    # the variable, never a half-configured process that 500s on the first sign-in
    # (invariant I7). Validated unconditionally — selecting the fake provider swaps
    # only how the identity is fetched, it does not waive the deployment's config.
    value = os.environ.get(var_name, "")
    if not value:
        raise OAuthConfigurationError(
            f"{var_name} is not set. Yandex OAuth requires YANDEX_CLIENT_ID and "
            "YANDEX_CLIENT_SECRET (and YANDEX_REDIRECT_URI) at boot."
        )
    return value


_client_id = _require("YANDEX_CLIENT_ID")
_client_secret = _require("YANDEX_CLIENT_SECRET")
_redirect_uri = os.environ.get("YANDEX_REDIRECT_URI", DEFAULT_FRONTEND_CALLBACK_URL)
_handoff_ttl_seconds = int(os.environ.get(HANDOFF_TTL_ENV_VAR, DEFAULT_HANDOFF_TTL_SECONDS))
_frontend_callback_url = os.environ.get(
    FRONTEND_CALLBACK_URL_ENV_VAR, DEFAULT_FRONTEND_CALLBACK_URL
)
_rate_limit_max = int(os.environ.get(RATE_LIMIT_MAX_ENV_VAR, DEFAULT_RATE_LIMIT_MAX_REQUESTS))
_rate_limit_window = int(
    os.environ.get(RATE_LIMIT_WINDOW_ENV_VAR, DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
)


def _rate_guard(session: AsyncSession) -> OAuthRateGuard:
    # The limiter runs on the same request session but commits its increment itself,
    # so the hit counts even when the guarded operation rolls back (a throttled or
    # failed leg). The session is closed by the create_* factory's finally block.
    return OAuthRateGuard(SqlAlchemyRateLimiter(session, _rate_limit_max, _rate_limit_window))


def _create_provider():
    # The fake impersonates the real provider under its own slug (`yandex`), so routes
    # and CSRF-state binding behave identically; it just never leaves the host. `vk`
    # has no credentials, so it is simply not in the registry and answers a named
    # "unknown provider" error rather than being aliased to Yandex.
    if os.environ.get(OAUTH_PROVIDER_ENV_VAR, "yandex") == "fake":
        return FakeOAuthProvider(
            name="yandex",
            authorize_url=os.environ.get("OAUTH_FAKE_AUTHORIZE_URL", DEFAULT_FAKE_AUTHORIZE_URL),
            redirect_uri=_redirect_uri,
            client_id=_client_id,
        )
    return YandexOAuthProvider(_client_id, _client_secret, _redirect_uri)


provider_registry = ProviderRegistry([_create_provider()])


def create_frontend_callback_url() -> str:
    return _frontend_callback_url


@request_scoped
def create_start_oauth(session: AsyncSession) -> StartOAuth:
    return StartOAuth(
        provider_registry=provider_registry,
        state_repository=SqlAlchemyOAuthStateRepository(session),
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        rate_guard=_rate_guard(session),
    )


@request_scoped
def create_complete_oauth_callback(session: AsyncSession) -> CompleteOAuthCallback:
    return CompleteOAuthCallback(
        provider_registry=provider_registry,
        state_repository=SqlAlchemyOAuthStateRepository(session),
        identity_repository=SqlAlchemyOAuthIdentityRepository(session),
        account_repository=SqlAlchemyAccountRepository(session),
        handoff_code_repository=SqlAlchemyHandoffCodeRepository(session),
        handoff_ttl_seconds=_handoff_ttl_seconds,
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        rate_guard=_rate_guard(session),
    )


@request_scoped
def create_exchange_handoff_code(session: AsyncSession) -> ExchangeHandoffCode:
    return ExchangeHandoffCode(
        handoff_code_repository=SqlAlchemyHandoffCodeRepository(session),
        account_repository=SqlAlchemyAccountRepository(session),
        token_service=token_service,
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        rate_guard=_rate_guard(session),
    )
