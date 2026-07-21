from fastapi import APIRouter, Depends

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

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_register_user_usecase() -> RegisterUser:
    raise NotImplementedError("wired by the application composition root")


def get_verify_account_usecase() -> VerifyAccount:
    raise NotImplementedError("wired by the application composition root")


def get_login_user_usecase() -> LoginUser:
    raise NotImplementedError("wired by the application composition root")


def get_refresh_access_token_usecase() -> RefreshAccessToken:
    raise NotImplementedError("wired by the application composition root")


def get_resend_code_usecase() -> ResendCode:
    raise NotImplementedError("wired by the application composition root")


@router.post("/register", status_code=201, response_model=RegisterResponseDto)
async def register(
    request: RegisterRequestDto,
    usecase: RegisterUser = Depends(get_register_user_usecase),
) -> RegisterResponseDto:
    result = await usecase.execute(
        email=request.email,
        password=request.password,
        confirm_password=request.confirm_password,
    )
    return RegisterResponseDto.from_domain(result)


@router.post("/verify", status_code=200, response_model=VerifyResponseDto)
async def verify(
    request: VerifyRequestDto,
    usecase: VerifyAccount = Depends(get_verify_account_usecase),
) -> VerifyResponseDto:
    await usecase.execute(email=request.email, code=request.code)
    return VerifyResponseDto(is_verified=True)


@router.post("/login", status_code=200, response_model=LoginResponseDto)
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


@router.post("/resend-code", status_code=200, response_model=ResendResponseDto)
async def resend_code(
    request: ResendRequestDto,
    usecase: ResendCode = Depends(get_resend_code_usecase),
) -> ResendResponseDto:
    result = await usecase.execute(email=request.email)
    return ResendResponseDto.from_domain(result)
