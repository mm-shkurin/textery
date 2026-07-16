from pydantic import BaseModel


class RefreshRequestDto(BaseModel):
    refresh_token: str
