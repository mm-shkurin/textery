import os

from provider.fake_provider import FakeProvider
from provider.gigachat_provider import GigaChatProvider
from session import create_engine, create_session_factory
from tokens.jwt_token_service import JwtTokenService

GENERATION_PROVIDER_ENV_VAR = "GENERATION_PROVIDER"
STALE_AFTER_MINUTES_ENV_VAR = "GENERATION_STALE_AFTER_MINUTES"
DEFAULT_STALE_AFTER_MINUTES = 10
JWT_SECRET_ENV_VAR = "JWT_SECRET"

engine = create_engine()
session_factory = create_session_factory(engine)


def create_provider():
    if os.environ.get(GENERATION_PROVIDER_ENV_VAR, "gigachat") == "fake":
        return FakeProvider()
    return GigaChatProvider()


def _create_token_service() -> JwtTokenService:
    # Built once at import, not per request: JwtTokenService refuses an empty
    # secret, so a misconfigured deployment fails at boot with a named error
    # instead of answering 500 on every /login while looking healthy. Same
    # module-level contract `engine` already follows for DATABASE_URL.
    return JwtTokenService(secret=os.environ.get(JWT_SECRET_ENV_VAR, ""))


token_service = _create_token_service()


def stale_after_minutes() -> int:
    return int(os.environ.get(STALE_AFTER_MINUTES_ENV_VAR, DEFAULT_STALE_AFTER_MINUTES))
