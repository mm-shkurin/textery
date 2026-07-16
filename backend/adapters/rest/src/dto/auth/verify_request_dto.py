from pydantic import BaseModel, Field


class VerifyRequestDto(BaseModel):
    email: str
    code: str = Field(pattern=r"^[0-9]{6}$")
