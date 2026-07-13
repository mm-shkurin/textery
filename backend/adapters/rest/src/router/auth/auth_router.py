from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from dto.auth.register_request_dto import RegisterRequestDto
from auth.register_user import RegisterUser
from shared.exceptions import ValidationException

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_register_user_usecase() -> RegisterUser:
    raise NotImplementedError("wired by the application composition root")


@router.post("/register", status_code=201, response_model=None)
async def register(
    request: RegisterRequestDto,
    usecase: RegisterUser = Depends(get_register_user_usecase),
) -> JSONResponse | None:
    try:
        await usecase.execute(
            email=request.email,
            password=request.password,
            confirm_password=request.confirm_password,
        )
    except ValidationException as exc:
        return JSONResponse(status_code=400, content={"error_code": exc.error_code, "message": exc.message})
    return None
