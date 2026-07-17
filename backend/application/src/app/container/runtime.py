import os

from generation.generation_provider import GenerationProvider
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


def _create_provider() -> GenerationProvider:
    if os.environ.get(GENERATION_PROVIDER_ENV_VAR, "gigachat") == "fake":
        return FakeProvider()
    return GigaChatProvider()


# Built once at import, for the same reason `engine` and `token_service` are.
#
# It used to be constructed per background task, which put GigaChatProvider's
# missing-credentials ConfigurationException *inside* the task -- and it raises
# before GenerateDocument.execute, so the row never reached generation.fail() and
# stayed pending. The sweep then re-picked it every interval, forever: nothing
# retried its way out of a config error, and nothing recorded one either. A
# deployment with GENERATION_PROVIDER=gigachat and no credentials looked healthy
# and accumulated stuck rows.
#
# At import it is a named boot failure instead, matching what DATABASE_URL and
# JWT_SECRET already do. It also lets a provider hold per-instance state -- an
# OAuth token cached across calls, say -- which a per-task instance cannot.
provider: GenerationProvider = _create_provider()


def _create_token_service() -> JwtTokenService:
    # Built once at import, not per request: JwtTokenService refuses an empty
    # secret, so a misconfigured deployment fails at boot with a named error
    # instead of answering 500 on every /login while looking healthy. Same
    # module-level contract `engine` already follows for DATABASE_URL.
    return JwtTokenService(secret=os.environ.get(JWT_SECRET_ENV_VAR, ""))


token_service = _create_token_service()


def stale_after_minutes() -> int:
    return int(os.environ.get(STALE_AFTER_MINUTES_ENV_VAR, DEFAULT_STALE_AFTER_MINUTES))
