from pydantic import BaseModel


class RegisterResponseDto(BaseModel):
    user_id: str
    is_verified: bool
