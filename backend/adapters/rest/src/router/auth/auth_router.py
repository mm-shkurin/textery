from fastapi import APIRouter, Depends

from dto.auth.register_request_dto import RegisterRequestDto
from dto.auth.register_response_dto import RegisterResponseDto
from auth.register_user import RegisterUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_register_user_usecase() -> RegisterUser:
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
