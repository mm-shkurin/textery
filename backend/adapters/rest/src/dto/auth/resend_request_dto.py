from pydantic import BaseModel


class ResendRequestDto(BaseModel):
    email: str
