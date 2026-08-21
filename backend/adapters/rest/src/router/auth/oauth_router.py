import logging
from http import HTTPStatus
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from analytics.client_context import (
    accept_language_of,
    campaign_parameters_of,
    client_ip_of,
    user_agent_of,
)
from auth.oauth.complete_oauth_callback import CompleteOAuthCallback
from auth.oauth.exchange_handoff_code import ExchangeHandoffCode
from auth.oauth.oauth_error_codes import OAUTH_CALLBACK_FAILED, OAuthCallbackError
from auth.oauth.start_oauth import StartOAuth
from dto.auth.login_response_dto import LoginResponseDto
from dto.auth.oauth_exchange_request_dto import OAuthExchangeRequestDto
from router import api_routes

logger = logging.getLogger(__name__)

router = APIRouter(prefix=api_routes.OAUTH, tags=["auth", "oauth"])

# 302, not FastAPI's default 307: the browser is finishing a navigation, and the
# provider/frontend legs of this handshake are plain GETs.
_REDIRECT_STATUS = HTTPStatus.FOUND


def get_start_oauth_usecase() -> StartOAuth:
    raise NotImplementedError("wired by the application composition root")


def get_complete_oauth_callback_usecase() -> CompleteOAuthCallback:
    raise NotImplementedError("wired by the application composition root")


def get_exchange_handoff_code_usecase() -> ExchangeHandoffCode:
    raise NotImplementedError("wired by the application composition root")


def get_frontend_callback_url() -> str:
    raise NotImplementedError("wired by the application composition root")


def client_source(request: Request) -> str:
    """The caller identity the rate-limit buckets key on.

    Behind the nginx proxy the real client IP is the rightmost X-Forwarded-For hop
    (nginx appends `$remote_addr`); earlier hops are client-supplied and spoofable,
    so the last entry is the one to trust. Falls back to the socket peer for a
    direct connection. This is a best-effort abuse bound, not an auth boundary — no
    security invariant rests on it.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@router.get("/{provider}/start")
async def start(
    provider: str,
    request: Request,
    source: str = Depends(client_source),
    usecase: StartOAuth = Depends(get_start_oauth_usecase),
) -> RedirectResponse:
    # The five `utm_*` are read off the query string rather than declared as
    # parameters, deliberately: a declared parameter with a type is a parameter
    # FastAPI can refuse, and this route answers 302/404/500 with no 400 at all.
    # Story 14 does not give it one — a broken marketing link must not end at a
    # broken sign-in. Anything unusable is dropped when it is parked.
    authorization_url = await usecase.execute(provider, source, campaign_parameters_of(request))
    return RedirectResponse(authorization_url, status_code=_REDIRECT_STATUS)


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    request: Request,
    code: str = "",
    state: str = "",
    source: str = Depends(client_source),
    usecase: CompleteOAuthCallback = Depends(get_complete_oauth_callback_usecase),
    frontend_callback_url: str = Depends(get_frontend_callback_url),
) -> RedirectResponse:
    # Every failure is one generic ?error= — the only thing that ever rides on success
    # is the opaque handoff code, never a token (invariant I4).
    # `provider` rides back on both legs so the frontend callback page can key its
    # copy off it. It is always the exact lowercase slug that matched the registry —
    # any other casing raises UNKNOWN_OAUTH_PROVIDER before reaching here, so the
    # frontend's exact-match guard never sees `Yandex`/`YANDEX`.
    try:
        handoff_code = await usecase.execute(
            provider,
            code,
            state,
            source,
            # `/callback` IS a browser request, so the caller's address, agent and
            # language are present here exactly as they are at `/register` — which
            # is what lets a provider-created account carry the same technical
            # context as a registered one, with no trick needed.
            client_ip=client_ip_of(request),
            user_agent=user_agent_of(request),
            accept_language=accept_language_of(request),
        )
        params = {"code": handoff_code, "provider": provider}
    except OAuthCallbackError as error:
        # The client only ever sees the generic ?error=; the operator-facing reason
        # (which leg failed) goes to the log. The message is safe by construction —
        # it names the failure kind, never the code, token or provider secret (I5).
        logger.warning("oauth callback refused for provider %s: %s", provider, error)
        params = {"error": OAUTH_CALLBACK_FAILED, "provider": provider}
    location = f"{frontend_callback_url}?{urlencode(params)}"
    return RedirectResponse(location, status_code=_REDIRECT_STATUS)


@router.post("/exchange", status_code=200, response_model=LoginResponseDto)
async def exchange(
    request: OAuthExchangeRequestDto,
    source: str = Depends(client_source),
    usecase: ExchangeHandoffCode = Depends(get_exchange_handoff_code_usecase),
) -> LoginResponseDto:
    pair = await usecase.execute(request.code, source)
    return LoginResponseDto.from_domain(pair)
