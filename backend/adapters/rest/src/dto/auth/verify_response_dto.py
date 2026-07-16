from pydantic import BaseModel


class VerifyResponseDto(BaseModel):
    is_verified: bool
