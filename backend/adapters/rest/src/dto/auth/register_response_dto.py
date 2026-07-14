from pydantic import BaseModel

from auth.account import Account


class RegisterResponseDto(BaseModel):
    user_id: str
    is_verified: bool

    @classmethod
    def from_domain(cls, account: Account) -> "RegisterResponseDto":
        return cls(user_id=str(account.id), is_verified=account.is_verified)
