from datetime import datetime

from pydantic import BaseModel

from auth.token_pair import TokenPair


class LoginResponseDto(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime

    @classmethod
    def from_domain(cls, pair: TokenPair) -> "LoginResponseDto":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            access_token_expires_at=pair.access_token_expires_at,
            refresh_token_expires_at=pair.refresh_token_expires_at,
        )
