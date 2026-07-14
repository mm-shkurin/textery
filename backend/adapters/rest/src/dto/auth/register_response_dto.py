from pydantic import BaseModel

from auth.registration_result import RegistrationResult


class RegisterResponseDto(BaseModel):
    user_id: str
    is_verified: bool
    email: str
    verification_code: str
    code_expires_at: str

    @classmethod
    def from_domain(cls, result: RegistrationResult) -> "RegisterResponseDto":
        return cls(
            user_id=str(result.account.id),
            is_verified=result.account.is_verified,
            email=result.account.email,
            verification_code=result.verification_code.code,
            code_expires_at=result.verification_code.expires_at.isoformat(),
        )
