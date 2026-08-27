from fastapi import APIRouter, Depends, Request

from analytics.client_context import observed_context
from analytics.record_registration_context import RecordRegistrationContext
from auth.login_user import LoginUser
from auth.refresh_access_token import RefreshAccessToken
from auth.register_user import RegisterUser
from auth.resend_code import ResendCode
from auth.verify_account import VerifyAccount
from dto.auth.login_request_dto import LoginRequestDto
from dto.auth.login_response_dto import LoginResponseDto
from dto.auth.refresh_request_dto import RefreshRequestDto
from dto.auth.register_request_dto import RegisterRequestDto
from dto.auth.register_response_dto import RegisterResponseDto
from dto.auth.resend_request_dto import ResendRequestDto
from dto.auth.resend_response_dto import ResendResponseDto
from dto.auth.verify_request_dto import VerifyRequestDto
from dto.auth.verify_response_dto import VerifyResponseDto
from router import api_routes
from router.auth.credential_rate_limit import (
    LOGIN_ROUTE,
    REGISTER_ROUTE,
    RESEND_CODE_ROUTE,
    rate_limited,
)

router = APIRouter(prefix=api_routes.AUTH, tags=["auth"])


def get_register_user_usecase() -> RegisterUser:
    raise NotImplementedError("wired by the application composition root")


def get_record_registration_context_usecase() -> RecordRegistrationContext:
    """The ONE dependency in this codebase that does not raise when unwired.

    Every other stub here raises `NotImplementedError`, which is right: a route
    served without its usecase would answer nonsense, and failing loudly at the
    first request is how that is caught. This one is the opposite case. If the
    composition root ever stops overriding it, a raise would turn EVERY
    REGISTRATION into a 500 -- the product's most sensitive route broken by a
    missing analytics binding, which is precisely the coupling this story's
    governing decision forbids. Unwired, the null ports store nothing and the
    registration is unaffected.
    """
    return RecordRegistrationContext()


def get_verify_account_usecase() -> VerifyAccount:
    raise NotImplementedError("wired by the application composition root")


def get_login_user_usecase() -> LoginUser:
    raise NotImplementedError("wired by the application composition root")


def get_refresh_access_token_usecase() -> RefreshAccessToken:
    raise NotImplementedError("wired by the application composition root")


def get_resend_code_usecase() -> ResendCode:
    raise NotImplementedError("wired by the application composition root")


@router.post(
    "/register",
    status_code=201,
    response_model=RegisterResponseDto,
    dependencies=[Depends(rate_limited(REGISTER_ROUTE))],
)
async def register(
    request: RegisterRequestDto,
    http_request: Request,
    usecase: RegisterUser = Depends(get_register_user_usecase),
    registration_context: RecordRegistrationContext = Depends(
        get_record_registration_context_usecase
    ),
) -> RegisterResponseDto:
    """Unchanged for the caller, whatever the attribution does.

    `RegisterUser` is not passed a single analytics value -- the account is
    created exactly as it was before Story 14, and the context is stored
    afterwards by a collaborator that cannot raise. That ordering is the whole
    guarantee: a visitor who arrives on a malformed marketing link, from a
    browser we cannot classify, behind a geolocation service that is down, still
    gets their 201 and their verification code.
    """
    result = await usecase.execute(
        email=request.email,
        password=request.password,
        confirm_password=request.confirm_password,
    )
    observed = observed_context(http_request)
    await registration_context.execute(
        account_id=result.account.id,
        campaign_parameters=request.campaign_parameters(),
        client_ip=observed.client_ip,
        user_agent=observed.user_agent,
        accept_language=observed.accept_language,
    )
    return RegisterResponseDto.from_domain(result)


@router.post("/verify", status_code=200, response_model=VerifyResponseDto)
async def verify(
    request: VerifyRequestDto,
    usecase: VerifyAccount = Depends(get_verify_account_usecase),
) -> VerifyResponseDto:
    await usecase.execute(email=request.email, code=request.code)
    return VerifyResponseDto(is_verified=True)


@router.post(
    "/login",
    status_code=200,
    response_model=LoginResponseDto,
    dependencies=[Depends(rate_limited(LOGIN_ROUTE))],
)
async def login(
    request: LoginRequestDto,
    usecase: LoginUser = Depends(get_login_user_usecase),
) -> LoginResponseDto:
    pair = await usecase.execute(email=request.email, password=request.password)
    return LoginResponseDto.from_domain(pair)


@router.post("/refresh", status_code=200, response_model=LoginResponseDto)
async def refresh(
    request: RefreshRequestDto,
    usecase: RefreshAccessToken = Depends(get_refresh_access_token_usecase),
) -> LoginResponseDto:
    pair = await usecase.execute(refresh_token=request.refresh_token)
    return LoginResponseDto.from_domain(pair)


@router.post(
    "/resend-code",
    status_code=200,
    response_model=ResendResponseDto,
    dependencies=[Depends(rate_limited(RESEND_CODE_ROUTE))],
)
async def resend_code(
    request: ResendRequestDto,
    usecase: ResendCode = Depends(get_resend_code_usecase),
) -> ResendResponseDto:
    result = await usecase.execute(email=request.email)
    return ResendResponseDto.from_domain(result)
